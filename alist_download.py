#!/usr/bin/env python3
"""
AList 批量下载器
使用wget批量下载AList服务器上的文件
"""

import requests
import subprocess
import os
import sys
import json
from urllib.parse import quote

class AListDownloader:
    def __init__(self, server_url, auth_token):
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Authorization': auth_token,
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.success_log_file = None
        self.downloaded_files = set()
    
    def set_success_log(self, local_dir):
        """设置成功下载记录文件"""
        self.success_log_file = os.path.join(local_dir, '.download_success.json')
        self.load_downloaded_files()
    
    def load_downloaded_files(self):
        """加载已下载文件列表"""
        if self.success_log_file and os.path.exists(self.success_log_file):
            try:
                with open(self.success_log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.downloaded_files = set(data.get('downloaded_files', []))
                    print(f"加载已下载文件记录: {len(self.downloaded_files)} 个文件")
            except Exception as e:
                print(f"读取下载记录失败: {e}")
                self.downloaded_files = set()
        else:
            self.downloaded_files = set()
    
    def save_downloaded_file(self, filename):
        """保存成功下载的文件记录"""
        if self.success_log_file:
            self.downloaded_files.add(filename)
            try:
                with open(self.success_log_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'downloaded_files': list(self.downloaded_files),
                        'last_update': os.path.getctime(self.success_log_file) if os.path.exists(self.success_log_file) else None
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存下载记录失败: {e}")
    
    def is_file_downloaded(self, filename):
        """检查文件是否已下载"""
        return filename in self.downloaded_files
    
    def get_file_list(self, remote_path):
        """获取远程目录的文件列表"""
        api_url = f"{self.server_url}/api/fs/list"
        data = {
            'path': remote_path,
            'password': '',
            'page': 1,
            'per_page': 0,
            'refresh': False,
        }
        
        try:
            response = self.session.post(api_url, json=data)
            response.raise_for_status()
            
            result = response.json()
            if result['code'] == 200:
                return result['data']['content']
            else:
                print(f"API错误: {result['message']}")
                return []
        except Exception as e:
            print(f"获取文件列表失败: {e}")
            return []
    
    def download_file(self, remote_path, filename, local_dir):
        """使用wget下载单个文件"""
        # 构建完整的文件路径用于记录
        full_file_path = os.path.join(remote_path, filename).replace('\\', '/')
        
        # 检查是否已下载
        if self.is_file_downloaded(full_file_path):
            print(f"⏭ 跳过已下载: {full_file_path}")
            return True
            
        # 构建下载URL
        encoded_path = quote(f"{remote_path}/{filename}")
        download_url = f"{self.server_url}/d{encoded_path}"
        
        # 本地文件路径
        local_path = os.path.join(local_dir, filename)
        
        # 确保本地目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 检查本地文件是否存在且完整
        if os.path.exists(local_path):
            print(f"📁 本地文件已存在，尝试验证: {filename}")
        
        # wget命令
        cmd = [
            'wget',
            '-c',  # 断点续传
            '-t', '5',  # 重试5次
            '-T', '60',  # 超时60秒
            '--progress=bar:force:noscroll',  # 进度条
            '--no-check-certificate',  # 忽略SSL证书问题
            '-O', local_path,
            download_url
        ]
        
        try:
            print(f"📥 下载: {full_file_path}")
            print(f"🔗 URL: {download_url}")
            
            result = subprocess.run(cmd, check=True)
            print(f"✅ 成功: {full_file_path}")
            
            # 记录成功下载（使用完整路径）
            self.save_downloaded_file(full_file_path)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 失败: {full_file_path} (退出码: {e.returncode})")
            # 删除可能的不完整文件
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
            return False
        except Exception as e:
            print(f"❌ 错误: {full_file_path} - {e}")
            return False
    
    def batch_download(self, remote_path, local_dir, file_pattern=None, recursive=True, max_depth=None):
        """批量下载文件（支持递归）"""
        print(f"🔍 分析远程目录: {remote_path}")
        
        if recursive:
            # 递归模式：统计所有文件
            print("📊 统计目录结构...")
            stats = self.get_directory_stats(remote_path, file_pattern, max_depth=max_depth)
            
            if stats['files'] == 0:
                print("❌ 未找到符合条件的文件")
                return
            
            print(f"📋 目录统计:")
            print(f"   文件总数: {stats['files']} 个")
            print(f"   目录总数: {stats['dirs']} 个")
            print(f"   总大小: {stats['size'] / (1024**3):.2f} GB")
            
            # 创建下载目录并设置记录文件
            os.makedirs(local_dir, exist_ok=True)
            self.set_success_log(local_dir)
            
            print(f"🚀 开始递归下载...")
            self.recursive_download(remote_path, local_dir, file_pattern, max_depth=max_depth)
            
        else:
            # 非递归模式：只下载当前目录
            file_list = self.get_file_list(remote_path)
            
            if not file_list:
                print("❌ 未找到文件")
                return
            
            # 过滤文件
            files = [f for f in file_list if not f['is_dir']]
            
            if file_pattern:
                files = [f for f in files if file_pattern in f['name']]
            
            if not files:
                print("❌ 没有符合条件的文件")
                return
            
            print(f"📋 找到 {len(files)} 个文件")
            total_size = sum(f['size'] for f in files)
            print(f"📊 总大小: {total_size / (1024**3):.2f} GB")
            
            # 创建下载目录并设置记录文件
            os.makedirs(local_dir, exist_ok=True)
            self.set_success_log(local_dir)
            
            # 过滤已下载的文件
            remaining_files = []
            for f in files:
                full_file_path = os.path.join(remote_path, f['name']).replace('\\', '/')
                if not self.is_file_downloaded(full_file_path):
                    remaining_files.append(f)
            
            already_downloaded = len(files) - len(remaining_files)
            
            if already_downloaded > 0:
                print(f"⏭ 已下载 {already_downloaded} 个文件，跳过")
            
            if not remaining_files:
                print("🎉 所有文件已下载完成！")
                return
                
            print(f"📥 需要下载 {len(remaining_files)} 个文件")
            remaining_size = sum(f['size'] for f in remaining_files)
            print(f"📊 剩余大小: {remaining_size / (1024**3):.2f} GB")
            
            # 开始下载
            success_count = 0
            for i, file_info in enumerate(remaining_files, 1):
                print(f"\n[{i}/{len(remaining_files)}] ", end="")
                
                if self.download_file(remote_path, file_info['name'], local_dir):
                    success_count += 1
                
                # 显示进度统计
                print(f"📈 进度: {success_count}/{i} 成功")
            
            print(f"\n🎯 下载完成: {success_count}/{len(remaining_files)} 个文件成功")
            total_success = already_downloaded + success_count
            print(f"📊 总体进度: {total_success}/{len(files)} 个文件完成")
    
    def clear_download_log(self):
        """清除下载记录"""
        if self.success_log_file and os.path.exists(self.success_log_file):
            try:
                os.remove(self.success_log_file)
                self.downloaded_files = set()
                print("✅ 下载记录已清除")
            except Exception as e:
                print(f"❌ 清除下载记录失败: {e}")
    
    def show_download_status(self, remote_path, file_pattern=None, recursive=True):
        """显示下载状态"""
        if recursive:
            print("📊 统计目录结构...")
            stats = self.get_directory_stats(remote_path, file_pattern)
            
            if stats['files'] == 0:
                print("❌ 未找到符合条件的文件")
                return
            
            # 递归统计已下载文件数
            downloaded_count = self._count_downloaded_files_recursive(remote_path, file_pattern)
            total_count = stats['files']
            
            print(f"📊 下载状态 (递归):")
            print(f"   总文件数: {total_count}")
            print(f"   总目录数: {stats['dirs']}")
            print(f"   已下载: {downloaded_count}")
            print(f"   未下载: {total_count - downloaded_count}")
            print(f"   完成度: {downloaded_count/total_count*100:.1f}%")
            print(f"   总大小: {stats['size'] / (1024**3):.2f} GB")
            
            return downloaded_count, total_count
        else:
            file_list = self.get_file_list(remote_path)
            if not file_list:
                print("❌ 未找到文件")
                return
                
            files = [f for f in file_list if not f['is_dir']]
            if file_pattern:
                files = [f for f in files if file_pattern in f['name']]
                
            if not files:
                print("❌ 没有符合条件的文件")
                return
            
            downloaded_count = 0
            for f in files:
                full_file_path = os.path.join(remote_path, f['name']).replace('\\', '/')
                if self.is_file_downloaded(full_file_path):
                    downloaded_count += 1
            
            total_count = len(files)
            
            print(f"📊 下载状态 (当前目录):")
            print(f"   总文件数: {total_count}")
            print(f"   已下载: {downloaded_count}")
            print(f"   未下载: {total_count - downloaded_count}")
            print(f"   完成度: {downloaded_count/total_count*100:.1f}%")
            
            return downloaded_count, total_count
    
    def _count_downloaded_files_recursive(self, remote_path, file_pattern=None):
        """递归统计已下载文件数"""
        file_list = self.get_file_list(remote_path)
        if not file_list:
            return 0
        
        count = 0
        
        # 统计当前目录的已下载文件
        files = [f for f in file_list if not f['is_dir']]
        if file_pattern:
            files = [f for f in files if file_pattern in f['name']]
        
        for f in files:
            full_file_path = os.path.join(remote_path, f['name']).replace('\\', '/')
            if self.is_file_downloaded(full_file_path):
                count += 1
        
        # 递归统计子目录
        directories = [f for f in file_list if f['is_dir']]
        for directory in directories:
            sub_remote_path = f"{remote_path}/{directory['name']}"
            count += self._count_downloaded_files_recursive(sub_remote_path, file_pattern)
        
        return count
    
    def recursive_download(self, remote_path, local_dir, file_pattern=None, current_depth=0, max_depth=None):
        """递归下载目录及其所有子目录"""
        if max_depth is not None and current_depth > max_depth:
            print(f"⏹ 已达到最大递归深度 {max_depth}")
            return
        
        indent = "  " * current_depth
        print(f"{indent}🔍 扫描目录: {remote_path}")
        
        # 获取当前目录的文件列表
        file_list = self.get_file_list(remote_path)
        if not file_list:
            print(f"{indent}⚠ 目录为空或无法访问: {remote_path}")
            return
        
        # 分离文件和目录
        files = [f for f in file_list if not f['is_dir']]
        directories = [f for f in file_list if f['is_dir']]
        
        # 过滤文件
        if file_pattern:
            files = [f for f in files if file_pattern in f['name']]
        
        # 下载当前目录的文件
        if files:
            print(f"{indent}📁 当前目录有 {len(files)} 个文件")
            
            # 确保本地目录存在
            os.makedirs(local_dir, exist_ok=True)
            
            success_count = 0
            for i, file_info in enumerate(files, 1):
                print(f"{indent}[{i}/{len(files)}] ", end="")
                
                if self.download_file(remote_path, file_info['name'], local_dir):
                    success_count += 1
            
            print(f"{indent}📈 当前目录完成: {success_count}/{len(files)} 个文件")
        
        # 递归处理子目录
        if directories:
            print(f"{indent}📂 发现 {len(directories)} 个子目录")
            
            for directory in directories:
                # 构建子目录路径
                sub_remote_path = f"{remote_path}/{directory['name']}"
                sub_local_dir = os.path.join(local_dir, directory['name'])
                
                print(f"{indent}📂 进入子目录: {directory['name']}")
                
                # 递归下载子目录
                self.recursive_download(
                    sub_remote_path, 
                    sub_local_dir, 
                    file_pattern, 
                    current_depth + 1,
                    max_depth
                )
    
    def get_directory_stats(self, remote_path, file_pattern=None, current_depth=0, max_depth=None):
        """递归统计目录信息"""
        if max_depth is not None and current_depth > max_depth:
            return {'files': 0, 'size': 0, 'dirs': 0}
        
        file_list = self.get_file_list(remote_path)
        if not file_list:
            return {'files': 0, 'size': 0, 'dirs': 0}
        
        # 分离文件和目录
        files = [f for f in file_list if not f['is_dir']]
        directories = [f for f in file_list if f['is_dir']]
        
        # 过滤文件
        if file_pattern:
            files = [f for f in files if file_pattern in f['name']]
        
        stats = {
            'files': len(files),
            'size': sum(f['size'] for f in files),
            'dirs': len(directories)
        }
        
        # 递归统计子目录
        for directory in directories:
            sub_remote_path = f"{remote_path}/{directory['name']}"
            sub_stats = self.get_directory_stats(
                sub_remote_path, 
                file_pattern, 
                current_depth + 1,
                max_depth
            )
            stats['files'] += sub_stats['files']
            stats['size'] += sub_stats['size']
            stats['dirs'] += sub_stats['dirs']
        
        return stats

def main():
    # 配置信息
    SERVER_URL = "YOUR SERVER URL"  # 替换为你的AList服务器地址
    AUTH_TOKEN = "YOUR AUTH TOKEN"
    
    # 下载配置
    REMOTE_PATH = "YOUR ROMOTE PATH"  # 远程路径
    LOCAL_DIR = "YOUR LOCAL PATH"  # 本地目录
    FILE_PATTERN = None  # 文件名过滤器，如 ".tif" 只下载tif文件
    RECURSIVE = True  # 是否递归下载子目录
    MAX_DEPTH = None  # 最大递归深度，None表示无限制
    
    # 创建下载器
    downloader = AListDownloader(SERVER_URL, AUTH_TOKEN)
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "status":
            print("📊 检查下载状态...")
            downloader.set_success_log(LOCAL_DIR)
            downloader.show_download_status(REMOTE_PATH, FILE_PATTERN, RECURSIVE)
            return
            
        elif action == "clear":
            print("🗑 清除下载记录...")
            downloader.set_success_log(LOCAL_DIR)
            confirm = input("确认清除所有下载记录？(y/N): ")
            if confirm.lower() == 'y':
                downloader.clear_download_log()
            return
            
        elif action == "help":
            print("📖 使用说明:")
            print("  python alist_download.py          # 开始/继续下载")
            print("  python alist_download.py status   # 查看下载状态")
            print("  python alist_download.py clear    # 清除下载记录")
            print("  python alist_download.py help     # 显示帮助")
            print("")
            print("📋 配置说明:")
            print(f"  远程路径: {REMOTE_PATH}")
            print(f"  本地目录: {LOCAL_DIR}")
            print(f"  文件过滤: {FILE_PATTERN if FILE_PATTERN else '无'}")
            print(f"  递归下载: {'是' if RECURSIVE else '否'}")
            print(f"  最大深度: {MAX_DEPTH if MAX_DEPTH else '无限制'}")
            return
    
    # 开始批量下载
    try:
        print("🚀 启动批量下载器...")
        print(f"📁 远程路径: {REMOTE_PATH}")
        print(f"💾 本地目录: {LOCAL_DIR}")
        print(f"🔄 递归模式: {'开启' if RECURSIVE else '关闭'}")
        if MAX_DEPTH:
            print(f"📏 最大深度: {MAX_DEPTH}")
        if FILE_PATTERN:
            print(f"🔍 文件过滤: {FILE_PATTERN}")
        print("")
        
        downloader.batch_download(REMOTE_PATH, LOCAL_DIR, FILE_PATTERN, RECURSIVE, MAX_DEPTH)
    except KeyboardInterrupt:
        print("\n⏹ 下载被用户中断")
        print("💡 下次运行时将从中断处继续下载")
    except Exception as e:
        print(f"❌ 下载过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
