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
        """批量下载文件（支持递归）或下载单个文件"""
        print(f"🔍 分析远程路径: {remote_path}")
        
        # 首先检查是否为单个文件
        if self._is_single_file(remote_path):
            print("📄 检测到单个文件，执行文件下载...")
            return self._download_single_file(remote_path, local_dir)
        
        print("📁 检测到目录，执行目录下载...")
        
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
        # 检查是否为单个文件
        if self._is_single_file(remote_path):
            filename = remote_path.rstrip('/').split('/')[-1]
            is_downloaded = self.is_file_downloaded(remote_path)
            
            print(f"📊 文件下载状态:")
            print(f"   文件名: {filename}")
            print(f"   状态: {'✅ 已下载' if is_downloaded else '❌ 未下载'}")
            print(f"   路径: {remote_path}")
            
            return (1 if is_downloaded else 0), 1
        
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

    def upload_file(self, local_file_path, remote_path):
        """上传单个文件到远程目录"""
        if not os.path.exists(local_file_path):
            print(f"❌ 本地文件不存在: {local_file_path}")
            return False
        
        filename = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)
        
        print(f"📤 准备上传: {filename} ({file_size / (1024**2):.2f} MB)")
        
        # 首先获取上传策略
        upload_info = self._get_upload_info(remote_path, filename, file_size)
        if not upload_info:
            return False
        
        # 执行文件上传
        return self._do_upload(local_file_path, upload_info, remote_path)
    
    def _get_upload_info(self, remote_path, filename, file_size):
        """获取上传信息和策略"""
        try:
            # 直接返回上传策略信息
            return self._upload_directly(remote_path, filename, file_size)
        except Exception as e:
            print(f"❌ 获取上传信息失败: {e}")
            return None
    
    def _upload_directly(self, remote_path, filename, file_size):
        """直接上传文件的策略信息"""
        return {
            'method': 'put',
            'url': f"{self.server_url}/api/fs/put",
            'path': remote_path,
            'filename': filename,
            'size': file_size
        }
    
    def _do_upload(self, local_file_path, upload_info, remote_path):
        """执行文件上传"""
        filename = os.path.basename(local_file_path)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 使用PUT方法上传文件
                api_url = f"{self.server_url}/api/fs/put"
                
                # 构建完整的远程文件路径
                full_remote_path = f"{remote_path}/{filename}"
                
                headers = self.session.headers.copy()
                headers.update({
                    'File-Path': quote(full_remote_path),
                    'Content-Type': 'application/octet-stream'
                })
                
                # 读取文件内容
                with open(local_file_path, 'rb') as f:
                    file_content = f.read()
                
                if attempt == 0:  # 只在第一次尝试时显示URL
                    print(f"🔗 上传到: {full_remote_path}")
                elif attempt > 0:
                    print(f"🔄 重试第 {attempt} 次...")
                
                # 发送PUT请求上传文件
                response = self.session.put(
                    api_url,
                    data=file_content,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get('code') == 200:
                    print(f"✅ 上传成功: {filename}")
                    return True
                else:
                    error_msg = result.get('message', '未知错误')
                    
                    # 如果是目录相关错误，尝试重新创建目录
                    if 'failed to make dir' in error_msg and attempt < max_retries - 1:
                        print(f"⚠ 目录创建失败，尝试重新创建: {error_msg}")
                        self._ensure_remote_directory(remote_path)
                        continue
                    else:
                        print(f"❌ 上传失败: {error_msg}")
                        return False
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠ 上传异常，准备重试: {e}")
                    continue
                else:
                    print(f"❌ 上传错误: {filename} - {e}")
                    return False
        
        return False
    
    def batch_upload(self, local_dir, remote_path, file_pattern=None, recursive=True):
        """批量上传文件"""
        if not os.path.exists(local_dir):
            print(f"❌ 本地目录不存在: {local_dir}")
            return
        
        print(f"📂 扫描本地目录: {local_dir}")
        
        # 收集要上传的文件
        files_to_upload = []
        directories_needed = set()
        
        if recursive:
            # 递归收集所有文件
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    if file_pattern is None or file_pattern in file:
                        local_file_path = os.path.join(root, file)
                        # 计算相对路径
                        rel_path = os.path.relpath(local_file_path, local_dir)
                        files_to_upload.append((local_file_path, rel_path))
                        
                        # 记录需要的目录
                        rel_dir = os.path.dirname(rel_path)
                        if rel_dir and rel_dir != '.':
                            target_dir = f"{remote_path}/{rel_dir}".replace('\\', '/')
                            directories_needed.add(target_dir)
                            
                            # 添加所有父目录
                            parts = target_dir.split('/')
                            for i in range(1, len(parts)):
                                parent_dir = '/'.join(parts[:i+1])
                                if parent_dir:
                                    directories_needed.add(parent_dir)
        else:
            # 只收集当前目录的文件
            for item in os.listdir(local_dir):
                item_path = os.path.join(local_dir, item)
                if os.path.isfile(item_path):
                    if file_pattern is None or file_pattern in item:
                        files_to_upload.append((item_path, item))
        
        if not files_to_upload:
            print("❌ 没有找到符合条件的文件")
            return
        
        print(f"📋 找到 {len(files_to_upload)} 个文件需要上传")
        total_size = sum(os.path.getsize(f[0]) for f in files_to_upload)
        print(f"📊 总大小: {total_size / (1024**3):.2f} GB")
        
        # 确保基础远程目录存在
        print(f"📁 确保远程基础目录存在: {remote_path}")
        if not self._ensure_remote_directory(remote_path):
            print(f"❌ 无法创建远程基础目录: {remote_path}")
            return
        
        # 预先创建所有需要的目录
        if directories_needed:
            print(f"📁 预先创建 {len(directories_needed)} 个目录...")
            sorted_dirs = sorted(directories_needed, key=len)  # 按路径长度排序，先创建父目录
            
            for dir_path in sorted_dirs:
                print(f"📁 确保目录存在: {dir_path}")
                if not self._ensure_remote_directory(dir_path):
                    print(f"⚠ 目录创建失败，继续尝试: {dir_path}")
        
        # 开始上传
        success_count = 0
        for i, (local_file_path, rel_path) in enumerate(files_to_upload, 1):
            print(f"\n[{i}/{len(files_to_upload)}] ", end="")
            
            # 计算目标远程路径
            target_remote_path = remote_path
            rel_dir = os.path.dirname(rel_path)
            if rel_dir and rel_dir != '.':
                target_remote_path = f"{remote_path}/{rel_dir}".replace('\\', '/')
            
            if self.upload_file(local_file_path, target_remote_path):
                success_count += 1
            
            # 显示进度
            print(f"📈 上传进度: {success_count}/{i} 成功")
        
        print(f"\n🎯 上传完成: {success_count}/{len(files_to_upload)} 个文件成功")
    
    def _ensure_remote_directory(self, remote_path):
        """确保远程目录存在，如果不存在则递归创建"""
        # 规范化路径
        remote_path = remote_path.rstrip('/')
        if not remote_path or remote_path == '/':
            return True
        
        # 检查目录是否已存在
        if self._check_directory_exists(remote_path):
            return True
        
        # 递归确保父目录存在
        parent_path = '/'.join(remote_path.split('/')[:-1])
        if parent_path and parent_path != '/':
            if not self._ensure_remote_directory(parent_path):
                return False
        
        # 创建当前目录
        return self._create_directory(remote_path)
    
    def _check_directory_exists(self, remote_path):
        """检查远程目录是否存在"""
        parent_path = '/'.join(remote_path.rstrip('/').split('/')[:-1])
        if not parent_path:
            parent_path = '/'
        
        dir_name = remote_path.rstrip('/').split('/')[-1]
        
        try:
            file_list = self.get_file_list(parent_path)
            for item in file_list:
                if item['is_dir'] and item['name'] == dir_name:
                    return True
            return False
        except Exception as e:
            # 如果获取文件列表失败，假设目录不存在
            return False
    
    def _create_directory(self, remote_path):
        """创建单个远程目录"""
        try:
            api_url = f"{self.server_url}/api/fs/mkdir"
            data = {
                'path': remote_path
            }
            
            response = self.session.post(api_url, json=data)
            result = response.json()
            
            if result.get('code') == 200:
                print(f"📁 创建远程目录: {remote_path}")
                return True
            else:
                error_msg = result.get('message', '未知错误')
                print(f"⚠ 创建目录失败: {remote_path} - {error_msg}")
                
                # 如果是同名冲突，检查是否是文件而非目录
                if '同名冲突' in error_msg or 'file is doloading' in error_msg:
                    print(f"⚠ 可能存在同名文件，无法创建目录: {remote_path}")
                    # 尝试列出父目录内容查看冲突情况
                    parent_path = '/'.join(remote_path.split('/')[:-1])
                    if parent_path:
                        self._debug_directory_contents(parent_path)
                
                # 对于某些特定错误，我们可以尝试忽略并继续
                if 'file is doloading' in error_msg:
                    print(f"⚠ 忽略下载冲突错误，尝试继续: {remote_path}")
                    # 等待一下再检查目录是否实际创建成功
                    import time
                    time.sleep(1)
                    if self._check_directory_exists(remote_path):
                        print(f"✅ 目录实际已存在: {remote_path}")
                        return True
                
                return False
                
        except Exception as e:
            print(f"⚠ 创建目录异常: {remote_path} - {e}")
            return False
    
    def _debug_directory_contents(self, parent_path):
        """调试：显示目录内容以诊断冲突"""
        try:
            file_list = self.get_file_list(parent_path)
            print(f"🔍 调试 - 目录内容 {parent_path}:")
            for item in file_list:
                item_type = "📁" if item['is_dir'] else "📄"
                print(f"   {item_type} {item['name']}")
        except Exception as e:
            print(f"🔍 调试 - 无法获取目录内容: {e}")
    
    def create_directory_force(self, remote_path):
        """强制创建目录的辅助命令"""
        print(f"🔨 强制创建目录: {remote_path}")
        
        # 首先检查目录是否已经存在
        if self._check_directory_exists(remote_path):
            print(f"✅ 目录已存在: {remote_path}")
            return True
        
        # 尝试创建目录
        result = self._create_directory(remote_path)
        if result:
            return True
        
        # 如果失败，尝试分步创建
        parts = remote_path.strip('/').split('/')
        current_path = ''
        
        for part in parts:
            current_path = f"{current_path}/{part}"
            if not self._check_directory_exists(current_path):
                print(f"📁 分步创建: {current_path}")
                if not self._create_directory(current_path):
                    print(f"❌ 分步创建失败: {current_path}")
                    return False
        
        return True

    def _is_single_file(self, remote_path):
        """检查远程路径是否为单个文件"""
        try:
            # 获取父目录路径和文件名
            parent_path = '/'.join(remote_path.rstrip('/').split('/')[:-1])
            filename = remote_path.rstrip('/').split('/')[-1]
            
            if not parent_path:
                parent_path = '/'
            
            # 获取父目录的文件列表
            file_list = self.get_file_list(parent_path)
            
            # 检查是否存在指定的文件
            for item in file_list:
                if item['name'] == filename and not item['is_dir']:
                    return True
            
            return False
        except Exception as e:
            print(f"⚠ 检查文件类型失败: {e}")
            return False
    
    def _download_single_file(self, remote_file_path, local_dir):
        """下载单个文件"""
        try:
            # 获取父目录路径和文件名
            parent_path = '/'.join(remote_file_path.rstrip('/').split('/')[:-1])
            filename = remote_file_path.rstrip('/').split('/')[-1]
            
            if not parent_path:
                parent_path = '/'
            
            # 获取文件信息
            file_list = self.get_file_list(parent_path)
            file_info = None
            
            for item in file_list:
                if item['name'] == filename and not item['is_dir']:
                    file_info = item
                    break
            
            if not file_info:
                print(f"❌ 文件不存在: {remote_file_path}")
                return False
            
            print(f"📄 找到文件: {filename}")
            print(f"📊 文件大小: {file_info['size'] / (1024**3):.2f} GB")
            
            # 创建下载目录并设置记录文件
            os.makedirs(local_dir, exist_ok=True)
            self.set_success_log(local_dir)
            
            # 检查是否已下载
            if self.is_file_downloaded(remote_file_path):
                print(f"⏭ 文件已下载: {remote_file_path}")
                return True
            
            # 下载文件
            print(f"📥 开始下载文件...")
            success = self.download_file(parent_path, filename, local_dir)
            
            if success:
                print(f"✅ 文件下载成功: {filename}")
            else:
                print(f"❌ 文件下载失败: {filename}")
            
            return success
            
        except Exception as e:
            print(f"❌ 下载单个文件出错: {e}")
            return False

def load_config():
    """加载配置文件"""
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 配置文件读取失败: {e}")
            sys.exit(1)
    else:
        print(f"⚠ 配置文件 {config_file} 不存在，请参考 config.json.example 创建")
        print("💡 或运行 'python alist_download.py init' 创建示例配置文件")
        sys.exit(1)

def create_example_config():
    """创建示例配置文件"""
    example_config = {
        "server_url": "https://your-alist-server.com",
        "auth_token": "Bearer your_auth_token_here",
        "download": {
            "remote_path": "/path/to/remote/directory",
            "local_dir": "./downloads",
            "file_pattern": None,
            "recursive": True,
            "max_depth": None
        },
        "upload": {
            "local_dir": "./uploads",
            "remote_path": "/path/to/remote/upload/directory"
        }
    }
    
    config_file = "config.json"
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(example_config, f, ensure_ascii=False, indent=2)
        print(f"✅ 示例配置文件已创建: {config_file}")
        print("📝 请复制为 config.json 并修改其中的配置信息")
        return True
    except Exception as e:
        print(f"❌ 创建示例配置文件失败: {e}")
        return False

def main():
    # 处理 init 命令
    if len(sys.argv) > 1 and sys.argv[1].lower() == "init":
        print("🔧 创建示例配置文件...")
        create_example_config()
        return
    
    # 从配置文件加载信息
    config = load_config()
    
    SERVER_URL = config.get("server_url", "")
    AUTH_TOKEN = config.get("auth_token", "")
    
    # 下载配置
    download_config = config.get("download", {})
    REMOTE_PATH = download_config.get("remote_path", "")
    LOCAL_DIR = download_config.get("local_dir", "./downloads")
    FILE_PATTERN = download_config.get("file_pattern", None)
    RECURSIVE = download_config.get("recursive", True)
    MAX_DEPTH = download_config.get("max_depth", None)
    
    # 上传配置
    upload_config = config.get("upload", {})
    UPLOAD_LOCAL_DIR = upload_config.get("local_dir", "./uploads")
    UPLOAD_REMOTE_PATH = upload_config.get("remote_path", "")
    
    # 验证必要配置
    if not SERVER_URL or not AUTH_TOKEN:
        print("❌ 配置信息不完整：缺少服务器地址或认证令牌")
        print("📝 请检查 config.json 文件中的 server_url 和 auth_token 配置")
        sys.exit(1)
    
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
            
        elif action == "upload":
            print("📤 开始上传文件...")
            print(f"📁 本地目录: {UPLOAD_LOCAL_DIR}")
            print(f"🎯 目标路径: {UPLOAD_REMOTE_PATH}")
            print(f"🔄 递归模式: {'开启' if RECURSIVE else '关闭'}")
            if FILE_PATTERN:
                print(f"🔍 文件过滤: {FILE_PATTERN}")
            print("")
            
            try:
                downloader.batch_upload(UPLOAD_LOCAL_DIR, UPLOAD_REMOTE_PATH, FILE_PATTERN, RECURSIVE)
            except KeyboardInterrupt:
                print("\n⏹ 上传被用户中断")
            except Exception as e:
                print(f"❌ 上传过程中出错: {e}")
                import traceback
                traceback.print_exc()
            return
            
        elif action == "check":
            print("🔍 检查远程目录状态...")
            if len(sys.argv) > 2:
                check_path = sys.argv[2]
            else:
                check_path = UPLOAD_REMOTE_PATH
            
            print(f"📁 检查路径: {check_path}")
            downloader._debug_directory_contents(check_path)
            
            # 检查父目录
            parent_path = '/'.join(check_path.rstrip('/').split('/')[:-1])
            if parent_path and parent_path != check_path:
                print(f"📁 检查父目录: {parent_path}")
                downloader._debug_directory_contents(parent_path)
            return
            
        elif action == "mkdir":
            print("🔨 创建远程目录...")
            if len(sys.argv) > 2:
                mkdir_path = sys.argv[2]
            else:
                mkdir_path = UPLOAD_REMOTE_PATH
            
            print(f"📁 创建路径: {mkdir_path}")
            if downloader.create_directory_force(mkdir_path):
                print(f"✅ 目录创建成功: {mkdir_path}")
            else:
                print(f"❌ 目录创建失败: {mkdir_path}")
            return
            
        elif action == "help":
            print("📖 使用说明:")
            print("  python alist_download.py init     # 创建示例配置文件")
            print("  python alist_download.py          # 开始/继续下载")
            print("  python alist_download.py upload   # 开始上传文件")
            print("  python alist_download.py status   # 查看下载状态")
            print("  python alist_download.py clear    # 清除下载记录")
            print("  python alist_download.py check [path]  # 检查远程目录状态")
            print("  python alist_download.py mkdir [path]  # 创建远程目录")
            print("  python alist_download.py help     # 显示帮助")
            print("")
            print("📋 配置文件: config.json")
            print("  首次使用请运行 'python alist_download.py init' 创建配置文件")
            print("")
            try:
                print("📋 当前下载配置:")
                print(f"  服务器地址: {SERVER_URL}")
                print(f"  远程路径: {REMOTE_PATH if REMOTE_PATH else '未配置'}")
                print(f"  本地目录: {LOCAL_DIR}")
                print(f"  文件过滤: {FILE_PATTERN if FILE_PATTERN else '无'}")
                print(f"  递归下载: {'是' if RECURSIVE else '否'}")
                print(f"  最大深度: {MAX_DEPTH if MAX_DEPTH else '无限制'}")
                print("")
                print("📋 当前上传配置:")
                print(f"  本地目录: {UPLOAD_LOCAL_DIR}")
                print(f"  目标路径: {UPLOAD_REMOTE_PATH if UPLOAD_REMOTE_PATH else '未配置'}")
                print(f"  文件过滤: {FILE_PATTERN if FILE_PATTERN else '无'}")
                print(f"  递归上传: {'是' if RECURSIVE else '否'}")
            except:
                print("⚠ 无法显示配置信息，请检查配置文件")
            return
    
    # 开始批量下载
    try:
        # 验证下载配置
        if not REMOTE_PATH:
            print("❌ 下载配置不完整：缺少远程路径")
            print("� 请检查 config.json 文件中的 download.remote_path 配置")
            sys.exit(1)
            
        print("�🚀 启动批量下载器...")
        print(f"🔗 服务器地址: {SERVER_URL}")
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
