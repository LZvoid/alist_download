# AList 批量下载器一个功能强大的 AList 文件批量下载和上传工具，支持断点续传、递归下载、进度跟踪等功能。## 功能特性### 🚀 核心功能- **批量下载**：支持目录和单文件下载- **批量上传**：支持目录和单文件上传- **断点续传**：下载中断后可继续下载- **递归操作**：支持递归下载/上传子目录- **进度跟踪**：实时显示下载/上传进度- **智能去重**：自动跳过已下载的文件### 📋 高级功能- **文件过滤**：支持按文件名模式过滤- **深度控制**：可限制递归下载的最大深度- **状态监控**：查看下载状态和完成度- **目录管理**：自动创建远程目录结构- **错误处理**：完善的错误处理和重试机制## 安装要求### 系统依赖- Python 3.6+- wget（用于文件下载）### Python 依赖```bashpip install requests```### 安装 wget**Windows:**```bash# 使用 Chocolateychoco install wget# 或下载 wget.exe 放到 PATH 目录```**Linux/macOS:**```bash# Ubuntu/Debiansudo apt-get install wget# CentOS/RHELsudo yum install wget# macOSbrew install wget```## 快速开始### 1. 初始化配置```bash# 创建示例配置文件python alist_download.py init# 复制并编辑配置文件cp config.json.example config.json```### 2. 配置文件设置编辑 `config.json` 文件：```json{  "server_url": "https://your-alist-server.com",  "auth_token": "Bearer your_auth_token_here",  "download": {    "remote_path": "/path/to/remote/directory",    "local_dir": "./downloads",    "file_pattern": null,    "recursive": true,    "max_depth": null  },  "upload": {    "local_dir": "./uploads",    "remote_path": "/path/to/remote/upload/directory"  }}```### 3. 获取认证令牌1. 登录你的 AList 管理界面2. 打开浏览器开发者工具 (F12)3. 在 Network 标签页中找到任意 API 请求4. 复制 Authorization 请求头的值### 4. 开始使用```bash# 开始下载python alist_download.py# 上传文件python alist_download.py upload# 查看下载状态python alist_download.py status```## 命令行用法```bash# 基础命令python alist_download.py init                # 创建示例配置文件python alist_download.py                     # 开始/继续下载python alist_download.py upload              # 开始上传文件python alist_download.py status              # 查看下载状态python alist_download.py clear               # 清除下载记录python alist_download.py help                # 显示帮助信息# 高级命令python alist_download.py check [path]        # 检查远程目录状态python alist_download.py mkdir [path]        # 创建远程目录```## 配置说明### 基础配置- `server_url`: AList 服务器地址- `auth_token`: 认证令牌（Bearer token）### 下载配置 (download)- `remote_path`: 远程文件或目录路径- `local_dir`: 本地下载目录- `file_pattern`: 文件名过滤器（如 ".mp4" 只下载 mp4 文件）- `recursive`: 是否递归下载子目录- `max_depth`: 最大递归深度（null 表示无限制）### 上传配置 (upload)- `local_dir`: 本地上传目录- `remote_path`: 远程目标目录## 使用示例### 下载单个文件```json{  "download": {    "remote_path": "/videos/movie.mp4",    "local_dir": "./downloads"  }}```### 递归下载目录```json{  "download": {    "remote_path": "/documents",    "local_dir": "./downloads",    "recursive": true,    "max_depth": 3  }}```### 过滤特定文件类型```json{  "download": {    "remote_path": "/photos",    "local_dir": "./downloads",    "file_pattern": ".jpg",    "recursive": true  }}```### 批量上传文件```json{  "upload": {    "local_dir": "./my_files",    "remote_path": "/backup/my_files"  }}```## 功能详解### 断点续传程序会自动记录下载进度，中断后重新运行会从断点继续：- 下载记录保存在 `.download_success.json` 文件中- 支持文件级别的断点续传- 使用 `wget -c` 参数支持字节级断点续传### 进度跟踪实时显示详细的下载/上传进度：- 当前文件进度- 总体完成度- 文件大小统计- 成功/失败统计### 错误处理完善的错误处理机制：- 网络错误自动重试（最多5次）- 文件完整性检查- 详细的错误日志输出- 优雅的中断处理### 目录管理智能的目录管理功能：- 自动创建本地目录结构- 递归创建远程目录- 目录冲突检测和处理## 文件结构```alist_download/├── alist_download.py          # 主程序├── config.json.example        # 配置文件示例├── config.json               # 实际配置文件（需要创建）├── .gitignore                # Git 忽略文件├── README.md                 # 使用说明├── downloads/                # 默认下载目录├── uploads/                  # 默认上传目录└── .download_success.json    # 下载记录文件（自动生成）```## 注意事项### 安全性- 配置文件包含敏感信息，请勿提交到版本控制系统- 建议定期更新认证令牌- 使用 HTTPS 连接确保传输安全### 性能优化- 大文件下载建议使用有限的递归深度- 网络不稳定时可适当减少并发数- 定期清理下载记录文件### 故障排除- 检查网络连接和服务器状态
- 验证认证令牌是否有效
- 确认远程路径是否存在和有权限访问
- 查看详细错误日志进行诊断

## 更新日志

### v2.0.0
- ✨ 新增配置文件支持
- 🔒 移除硬编码的敏感信息
- 📝 完善命令行界面
- 🐛 修复多项已知问题

### v1.0.0
- 🎉 初始版本发布
- 📥 支持批量下载
- 📤 支持批量上传
- 🔄 支持断点续传

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 在 GitHub 上提交 Issue
3. 提供详细的错误信息和配置（隐藏敏感信息）
