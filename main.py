"""
Use this script to filter and process Chinese data from the GeoNames dataset when updates exist,
now leveraging aria2 for file downloads.
"""

import os
import subprocess
import logging
import platform
from typing import List, Optional

import requests
import polars
import opencc

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

CHINESE_LANGUAGE_CODE: List[str] = [
    'zh-Hans', 'zh-CN', 'cnm', 'zh', 'zho', 'chi', 'zh-Hant', 'zh-TW', 'ja'
]

def read_etag(etag_path: str) -> Optional[str]:
    """Read an ETag from a local file if it exists.

    Args:
        etag_path (str): Path to the file storing the ETag.

    Returns:
        Optional[str]: The ETag value or None if not found.
    """
    if not os.path.exists(etag_path):
        return None
    with open(etag_path, 'rb') as file_handle:
        return file_handle.read().decode()

def write_etag(etag_path: str, new_etag: str) -> None:
    """Write a new ETag value to a file.

    Args:
        etag_path (str): Path to the file storing the ETag.
        new_etag (str): The ETag to record.
    """
    with open(etag_path, 'wb') as file_handle:
        file_handle.write(new_etag.encode())

def is_chinese(text: str) -> bool:
    """Check if text contains only Chinese characters.

    This function identifies strings strictly in Chinese script.

    Args:
        text (str): Text to check.

    Returns:
        bool: True if all characters are Chinese, otherwise False.
    """
    return all(
        ('\U00004E00' <= char <= '\U00009FFF')
        or ('\U00003400' <= char <= '\U00004DBF')
        or ('\U00020000' <= char <= '\U0002A6DF')
        or ('\U0002A700' <= char <= '\U0002B73A')
        or ('\U0002B740' <= char <= '\U0002B81D')
        or ('\U0002B820' <= char <= '\U0002CEA1')
        or ('\U0002CEB0' <= char <= '\U0002EBE0')
        or ('\U00030000' <= char <= '\U0003134A')
        or ('\U00031350' <= char <= '\U000323AF')
        or ('\U0002EBF0' <= char <= '\U0002EE5D')
        or ('\U00002F00' <= char <= '\U00002FD5')
        or ('\U00002E80' <= char <= '\U00002EF3')
        or ('\U0000F900' <= char <= '\U0000FAD9')
        or ('\U0002F800' <= char <= '\U0002FA1D')
        for char in text
    )

def calculate_language_precedence(language: Optional[str]) -> int:
    """Assign a numeric precedence to a language code for sorting.

    Args:
        language (Optional[str]): Language code or None.

    Returns:
        int: A smaller value indicates a higher precedence.
    """
    if language and language in CHINESE_LANGUAGE_CODE:
        return CHINESE_LANGUAGE_CODE.index(language)
    if not language:
        return len(CHINESE_LANGUAGE_CODE) + 1
    if language.startswith('zh-'):
        return len(CHINESE_LANGUAGE_CODE) + 2
    return len(CHINESE_LANGUAGE_CODE) + 3

def unzip_file(archive_file: str, extracted_file: str, output_dir: str) -> None:
    """Extract a file from a .zip archive, depending on the platform.

    Args:
        archive_file (str): Path to the archive file.
        extracted_file (str): Filename inside the archive to extract.
        output_dir (str): Directory where the extracted file will be placed.

    Raises:
        subprocess.CalledProcessError: If extraction fails.
    """
    file_lower = archive_file.lower()
    sys_type = platform.system()
    if file_lower.endswith('.zip'):
        if sys_type == 'Windows':
            cmd = ['7z', 'e', archive_file, extracted_file, f'-o{output_dir}']
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        else:
            cmd = ['unzip', '-o', archive_file, extracted_file, '-d', output_dir]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
    else:
        logging.warning("Unrecognized archive format: %s", archive_file)
        return
    os.remove(archive_file)
    logging.info("Extraction completed: %s", extracted_file)

def aria2_download(url: str, output_path: str, num_connections: int = 4) -> None:
    """Download a file using aria2 with multiple connections.

    Args:
        url (str): The remote file URL.
        output_path (str): Where the downloaded file will be saved.
        num_connections (int): Number of parallel connections used by aria2.
    """
    download_dir = os.path.dirname(output_path)
    output_file = os.path.basename(output_path)
    os.makedirs(download_dir, exist_ok=True)

    cmd = [
        'aria2c',
        f'--split={num_connections}',
        f'--max-connection-per-server={num_connections}',
        '--allow-overwrite=true',
        f'--dir={download_dir}',
        f'--out={output_file}',
        url
    ]

    try:
        subprocess.run(cmd, check=True)
        logging.info("Download completed using aria2: %s", output_path)
    except subprocess.CalledProcessError as exc:
        logging.error("aria2 download failed: %s", exc)
        raise

def export_to_parquet(input_file: str, output_file: str, local_converter: opencc.OpenCC) -> None:
    """Convert 'alternateNamesV2.txt' to a Parquet file, focusing on Chinese data.

    This function filters relevant columns, keeps only desired language codes,
    and uses OpenCC to convert Traditional Chinese to Simplified.

    Args:
        input_file (str): Path to 'alternateNamesV2.txt'.
        output_file (str): Destination for the Parquet file.
        local_converter (opencc.OpenCC): Converter for Traditional->Simplified.
    """
    df = polars.read_csv(
        input_file,
        has_header=False,
        separator='\t',
        columns=[1, 2, 3, 4, 5, 6, 7]
    )
    df.columns = [
        'geoname_id',
        'iso_language',
        'alternate_name',
        'is_preferred_name',
        'is_short_name',
        'is_colloquial',
        'is_historic'
    ]

    # Filter out colloquial/historic
    df = df.filter(
        (polars.col('is_colloquial').is_null())
        & (polars.col('is_historic').is_null())
    ).drop(['is_colloquial', 'is_historic'])

    # Keep only certain language codes or null
    df = df.filter(
        (polars.col('iso_language').is_in(CHINESE_LANGUAGE_CODE))
        | (polars.col('iso_language').str.contains(r'^zh-'))
        | (polars.col('iso_language').is_null())
    )

    # Validate if 'ja' or null codes actually hold Chinese text
    df = df.with_columns(
        polars.when(
            (polars.col('iso_language') == 'ja')
            | (polars.col('iso_language').is_null())
        )
        .then(
            polars.col('alternate_name').map_elements(
                is_chinese,
                return_dtype=polars.Boolean,
                skip_nulls=False
            )
        )
        .otherwise(True)
        .alias('is_chinese')
    ).filter(polars.col('is_chinese'))

    # Assign numeric language precedence
    df = df.with_columns(
        polars.col('iso_language').map_elements(
            calculate_language_precedence,
            return_dtype=polars.Int64,
            skip_nulls=False
        ).alias('language_precedence')
    )

    # Sort and deduplicate (keep first record per geoname_id)
    df = df.sort(
        ['geoname_id', 'language_precedence', 'is_preferred_name', 'is_short_name'],
        descending=[False, False, True, False]
    ).unique(subset=['geoname_id'], keep='first')

    # Convert Traditional->Simplified
    df = df.with_columns(
        polars.col('alternate_name').map_elements(
            local_converter.convert,
            return_dtype=polars.Utf8,
            skip_nulls=True
        ).alias('alternate_name')
    )

    # Drop unneeded columns
    df = df.drop([
        'iso_language',
        'is_preferred_name',
        'is_short_name',
        'is_chinese',
        'language_precedence'
    ])
    df = df.rename({'alternate_name': 'zh_name'})
    df.write_parquet(output_file)
    logging.info("Data written to Parquet file: %s", output_file)

def geonames_download(
    geonames_path: str,
    etag_path: str,
    local_converter: opencc.OpenCC,
    num_chunks: int = 4
) -> None:
    """Download and process 'alternateNamesV2.zip' from GeoNames if updates are detected.

    Uses ETag to determine whether new data exists. If so, attempts to fetch
    the file using aria2, then extracts and converts it to Parquet format.

    Args:
        geonames_path (str): Destination path for the final Parquet file.
        etag_path (str): Path to store/read the ETag.
        local_converter (opencc.OpenCC): Converter for Traditional Chinese text.
        num_chunks (int): Number of parallel connections for aria2.
    """
    url = "https://download.geonames.org/export/dump/alternateNamesV2.zip"
    current_etag = read_etag(etag_path)
    headers = {'If-None-Match': current_etag} if current_etag else {}

    # Check if a new version is available
    try:
        response = requests.head(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logging.error("GeoNames HEAD request error: %s", exc)
        return

    geonames_dir = os.path.dirname(geonames_path)
    zipfile_path = os.path.join(geonames_dir, 'alternateNamesV2.zip')

    # Skip download if not changed and file already exists
    if response.status_code in (304, 302) and os.path.exists(geonames_path):
        logging.info("GeoNames file already exists. Download skipped.")
        return

    # Handle standard/partial responses
    if response.status_code in (200, 206, 302, 304):
        new_etag = response.headers.get('ETag')
        if new_etag:
            write_etag(etag_path, new_etag)

        # Download with aria2
        aria2_download(url, zipfile_path, num_connections=num_chunks)

        # Unzip, convert, clean up
        unzip_file(zipfile_path, 'alternateNamesV2.txt', geonames_dir)
        export_to_parquet(
            os.path.join(geonames_dir, 'alternateNamesV2.txt'),
            os.path.join(geonames_dir, 'alternateNamesV2.parquet'),
            local_converter
        )
        try:
            os.remove(os.path.join(geonames_dir, 'alternateNamesV2.txt'))
        except OSError:
            pass
        logging.info("GeoNames download and processing completed.")

def main(local_converter: opencc.OpenCC) -> None:
    """Coordinate the download and processing of GeoNames data end-to-end.

    Checks local Parquet/ETag files, downloads new data if available,
    and converts it to Parquet format for future use.

    Args:
        local_converter (opencc.OpenCC): Converter for Traditional->Simplified Chinese.
    """
    logging.info("Starting GeoNames download and processing...")

    os.makedirs('./output', exist_ok=True)

    logging.info(
        "Found alternateNamesV2.parquet: %s",
        os.path.exists('./output/alternateNamesV2.parquet')
    )
    logging.info(
        "Found alternateNamesV2-ETag.txt: %s",
        os.path.exists('./output/alternateNamesV2-ETag.txt')
    )
    geonames_download(
        './output/alternateNamesV2.parquet',
        './output/alternateNamesV2-ETag.txt',
        local_converter
    )
    logging.info("Finished GeoNames download and processing.")

if __name__ == '__main__':
    converter = opencc.OpenCC('t2s.json')
    main(converter)
