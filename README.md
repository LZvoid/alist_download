# AList 批量下载器

一个基于Python的AList服务器批量下载工具，支持递归下载目录结构、断点续传和下载进度记录。

## ✨ 功能特性

- 🔄 **递归下载**: 支持下载整个目录树，保持完整的目录结构
- 📥 **断点续传**: 使用wget实现可靠的断点续传功能
- 📊 **进度记录**: 自动记录下载进度，支持中断后继续下载
- 🔍 **文件过滤**: 支持按文件名模式过滤下载的文件
- 📈 **状态统计**: 提供详细的下载状态和进度统计
- 🛡️ **错误处理**: 完善的错误处理和重试机制
- 🎯 **多种模式**: 支持递归和非递归两种下载模式

## 📋 系统要求

- Python 3.6+
- wget (Linux/macOS系统通常已预装)
- requests库

### 安装依赖

```bash
pip install requests
```

对于Ubuntu/Debian系统，确保安装了wget：
```bash
sudo apt-get install wget
```

## 🚀 快速开始

### 1. 配置下载参数

编辑脚本中的配置部分：

```python
# 配置信息
SERVER_URL = "http://your-alist-server:port"  # AList服务器地址
AUTH_TOKEN = "your_auth_token_here"            # 认证令牌

# 下载配置
REMOTE_PATH = "/your/remote/path"              # 远程路径
LOCAL_DIR = "/your/local/download/directory"   # 本地下载目录
FILE_PATTERN = None                            # 文件过滤器 (可选)
RECURSIVE = True                               # 是否递归下载
MAX_DEPTH = None                               # 最大递归深度 (可选)
```

### 2. 获取认证令牌

1. 登录AList Web界面
2. 打开浏览器开发者工具 (F12)
3. 在Network标签页中找到任意API请求
4. 复制请求头中的`Authorization`字段值

### 3. 运行下载器

```bash
# 开始下载
python alist_download.py

# 查看下载状态
python alist_download.py status

# 清除下载记录
python alist_download.py clear

# 查看帮助信息
python alist_download.py help
```

## 📖 详细使用说明

### 命令行参数

| 命令 | 说明 |
|------|------|
| `python alist_download.py` | 开始/继续下载 |
| `python alist_download.py status` | 查看下载状态 |
| `python alist_download.py clear` | 清除下载记录 |
| `python alist_download.py help` | 显示帮助信息 |

### 配置选项详解

#### 基础配置
- `SERVER_URL`: AList服务器地址，格式为 `http://ip:port`
- `AUTH_TOKEN`: 从AList Web界面获取的认证令牌
- `REMOTE_PATH`: 要下载的远程目录路径
- `LOCAL_DIR`: 本地下载目录路径

#### 高级配置
- `FILE_PATTERN`: 文件名过滤器
  - `None`: 下载所有文件
  - `".jpg"`: 只下载包含".jpg"的文件
  - `"2024"`: 只下载文件名包含"2024"的文件

- `RECURSIVE`: 递归下载模式
  - `True`: 递归下载所有子目录
  - `False`: 只下载当前目录的文件

- `MAX_DEPTH`: 最大递归深度
  - `None`: 无限制深度
  - `3`: 最多递归3层目录

### 使用示例

#### 示例1: 下载整个目录
```python
REMOTE_PATH = "/dataset/images"
LOCAL_DIR = "/home/user/downloads/images"
RECURSIVE = True
FILE_PATTERN = None
```

#### 示例2: 只下载图片文件
```python
REMOTE_PATH = "/photos"
LOCAL_DIR = "/home/user/photos"
RECURSIVE = True
FILE_PATTERN = ".jpg"
```

#### 示例3: 限制递归深度
```python
REMOTE_PATH = "/documents"
LOCAL_DIR = "/home/user/docs"
RECURSIVE = True
MAX_DEPTH = 2
```

## 🔧 功能详解

### 递归下载
- 自动遍历所有子目录
- 在本地重建完整的目录结构
- 支持设置最大递归深度避免过深的目录

### 断点续传
- 使用wget的`-c`参数实现断点续传
- 自动处理网络中断和临时错误
- 支持重试机制（默认重试5次）

### 下载记录
- 在下载目录生成`.download_success.json`记录文件
- 记录所有成功下载的文件路径
- 支持中断后继续下载，自动跳过已下载文件

### 进度显示
```
📊 目录统计:
   文件总数: 1250 个
   目录总数: 45 个
   总大小: 15.67 GB

🚀 开始递归下载...
  🔍 扫描目录: /dataset/images
  📁 当前目录有 25 个文件
  [1/25] 📥 下载: /dataset/images/photo001.jpg
  ✅ 成功: /dataset/images/photo001.jpg
  📈 当前目录完成: 25/25 个文件
```

## 📁 文件结构

```
alist_download.py          # 主程序文件
README.md                  # 说明文档
.download_success.json     # 下载记录文件 (自动生成)
```

## ⚠️ 注意事项

1. **认证令牌有效期**: AList的认证令牌有时效性，过期后需要重新获取
2. **网络稳定性**: 大文件下载建议在稳定的网络环境下进行
3. **磁盘空间**: 确保本地有足够的磁盘空间存储下载文件
4. **权限问题**: 确保对下载目录有写入权限
5. **服务器负载**: 避免同时启动多个下载任务，以免给服务器造成过大负载

## 🐛 故障排除

### 常见问题

#### 1. 认证失败
**问题**: 提示"API错误"或认证相关错误
**解决**: 重新获取认证令牌并更新配置

#### 2. wget命令未找到
**问题**: 提示"wget: command not found"
**解决**: 安装wget工具
```bash
# Ubuntu/Debian
sudo apt-get install wget

# CentOS/RHEL
sudo yum install wget

# macOS
brew install wget
```

#### 3. 下载中断
**问题**: 下载过程中出现网络中断
**解决**: 重新运行脚本，会自动从中断处继续

#### 4. 权限错误
**问题**: 无法创建目录或写入文件
**解决**: 检查下载目录的写入权限

### 调试模式

如果遇到问题，可以在脚本中添加调试信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 许可证

本项目基于MIT许可证开源。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进此工具！

## 📧 支持

如果遇到问题或有功能建议，请通过以下方式联系：

- 提交GitHub Issue
- 查看文档和FAQ

---

**⚠️ 免责声明**: 请确保您有权下载相关文件，并遵守相关的版权和使用条款。
