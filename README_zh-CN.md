<div align="center">

# GeoNamesCN

[**English**](README.md) | **简体中文**  

![GeoNamesCN](https://socialify.git.ci/CZAsTc/GeoNamesCN/image?description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pulls=1&stargazers=1&theme=Auto)

![GitHub Repo Size](https://img.shields.io/github/repo-size/CZAsTc/GeoNamesCN?style=for-the-badge)
[![GitHub Release (with filter)](https://img.shields.io/github/v/release/CZAsTc/GeoNamesCN?style=for-the-badge)](https://github.com/CZAsTc/GeoNamesCN/releases/latest)
[![GitHub All Releases](https://img.shields.io/github/downloads/CZAsTc/GeoNamesCN/total?style=for-the-badge&color=violet)](https://github.com/CZAsTc/GeoNamesCN/releases)
[![GitHub License](https://img.shields.io/github/license/CZAsTc/GeoNamesCN?style=for-the-badge)](https://github.com/CZAsTc/GeoNamesCN/blob/main/LICENSE)

</div>

## GeoNamesCN

GeoNamesCN 是一个用于下载、处理和筛选中文地名数据的项目。它集成了来自 GeoNames 的数据，使用 aria2 进行高效下载，并利用 OpenCC 进行文本转换。

## 特性
- 并行下载大数据集  
- 繁体中文与简体中文之间的转换  
- 简单的数据筛选和转换  

## 依赖
- Python 3.9 或更高版本（推荐使用较高版本以获得更好的性能）  
- aria2（用于并行下载）  
- 7-Zip（仅限 Windows，用于解压缩）  
- OpenCC（用于文本转换）  
- polars（用于数据处理）  
- requests（用于 HTTP 交互）  

## 使用方法
### 1. 从 Releases 下载
对于大多数用户，获取最新处理数据的最简单方法是直接从 [最新版本](https://github.com/CZAsTc/GeoNamesCN/releases/latest) 下载已准备好的文件。将 `alternateNamesV2.parquet` 放到 `output/` 文件夹（或任何目录）中，即可立即使用。

### 2. 本地安装
如果您希望在本地运行此过程，请参考下方的 [安装](#安装方法) 部分。安装依赖项后，进入项目文件夹并运行：

```bash
cd GeoNamesCN
python main.py
```

该脚本将处理数据，将输出存储在 `output` 或 `upload` 文件夹中，并生成 `alternateNamesV2.parquet`。

### 3. 使用 GitHub Actions
开发者还可以配置 `.github/workflows/main.yml` 中的 GitHub Actions 工作流。它将：
1. 比较 ETag 值，检查数据是否为最新。  
2. 使用 `main.py` 下载和处理 GeoNames 数据。  
3. 将生成的 Parquet 文件上传到 `download` 分支和 Releases。

### Parquet 格式和示例
本项目生成的 Parquet 文件通常包含：
- `geoname_id`：每个位置的唯一标识符  
- `zh_name`：处理后的中文名称  

使用 polars 读取文件的示例：

```python
import polars as pl

df = pl.read_parquet("output/alternateNamesV2.parquet")
print(df.head())
```

## 安装方法
### Windows
1. 从官方网站安装 Python 3.9 或更高版本。  
2. 必须安装 [aria2](https://aria2.github.io/) 和 [7-Zip](https://www.7-zip.org/) 以支持核心功能。  
3. 克隆该仓库：  
   ```bash
   git clone https://github.com/CZAsTc/GeoNamesCN.git
   ```
4. 安装依赖：  
   ```bash
   pip install -r requirements.txt
   ```

### Linux / macOS
1. 确保已安装 Python 3.9 或更高版本。  
2. 使用包管理器安装 [aria2](https://aria2.github.io/)（例如，在 Ubuntu 上使用 `sudo apt install aria2`）。  
3. 克隆该仓库：  
   ```bash
   git clone https://github.com/CZAsTc/GeoNamesCN.git
   ```
4. 安装依赖：  
   ```bash
   pip install -r requirements.txt
   ```

## 工作原理
1. 通过 aria2 下载 GeoNames 数据，加速数据传输。  
2. 使用 ETag 检查，只在数据集更新时才重新下载。  
3. 使用 OpenCC 进行文本转换（例如，将繁体字转换为简体字）。  
4. 将处理后的数据输出为 Parquet 格式。  

## 许可证
- 代码以 MIT 许可证发布。请参阅 [LICENSE](LICENSE) 文件。  
- [GeoNames Gazetteer 数据](https://download.geonames.org/export/dump/readme.txt) 采用 [Creative Commons Attribution 4.0 许可证](https://creativecommons.org/licenses/by/4.0/) 发布。  

## 致谢
- 感谢 [GeoNames](http://www.geonames.org/) 提供数据  
- 感谢所有贡献者和开源社区的支持！  
