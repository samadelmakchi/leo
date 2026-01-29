#!/usr/bin/env python3
"""
File Manager
مدیریت فایل‌ها و دایرکتوری‌ها
"""

import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import hashlib
import json
import yaml

logger = logging.getLogger(__name__)


class FileManager:
    """مدیریت فایل‌ها و دایرکتوری‌ها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه File Manager
        
        Args:
            config: تنظیمات
        """
        self.config = config or {}
        self.default_mode = self.config.get('default_mode', 0o644)
        self.default_dir_mode = self.config.get('default_dir_mode', 0o755)
        
        logger.info("File Manager initialized")
    
    # ==================== Directory Operations ====================
    
    def create_directory(self, path: str, mode: int = None, 
                        force: bool = False, recurse: bool = True) -> Dict:
        """
        ایجاد دایرکتوری
        
        Args:
            path: مسیر دایرکتوری
            mode: mode دایرکتوری
            force: overwrite اگر وجود دارد
            recurse: ایجاد دایرکتوری‌های والد اگر وجود ندارند
            
        Returns:
            نتیجه عملیات
        """
        try:
            dir_path = Path(path)
            mode = mode or self.default_dir_mode
            
            if dir_path.exists():
                if dir_path.is_dir():
                    # دایرکتوری وجود دارد
                    if force:
                        # تغییر permissions اگر force=True
                        os.chmod(str(dir_path), mode)
                        logger.debug(f"Directory permissions updated: {path}")
                        return {
                            'success': True,
                            'created': False,
                            'changed': True,
                            'path': str(dir_path),
                            'mode': oct(mode),
                            'message': 'Directory permissions updated'
                        }
                    else:
                        logger.debug(f"Directory already exists: {path}")
                        return {
                            'success': True,
                            'created': False,
                            'changed': False,
                            'path': str(dir_path),
                            'message': 'Directory already exists'
                        }
                else:
                    # یک فایل با همین نام وجود دارد
                    if force:
                        # حذف فایل و ایجاد دایرکتوری
                        dir_path.unlink()
                        if recurse:
                            dir_path.mkdir(mode=mode, parents=True, exist_ok=True)
                        else:
                            dir_path.mkdir(mode=mode)
                        logger.info(f"File replaced with directory: {path}")
                        return {
                            'success': True,
                            'created': True,
                            'changed': True,
                            'path': str(dir_path),
                            'mode': oct(mode),
                            'message': 'File replaced with directory'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"A file already exists at {path}",
                            'path': str(dir_path)
                        }
            else:
                # ایجاد دایرکتوری جدید
                if recurse:
                    dir_path.mkdir(mode=mode, parents=True, exist_ok=True)
                else:
                    # بررسی وجود دایرکتوری والد
                    if not dir_path.parent.exists():
                        return {
                            'success': False,
                            'error': f"Parent directory does not exist: {dir_path.parent}",
                            'path': str(dir_path)
                        }
                    dir_path.mkdir(mode=mode)
                
                logger.info(f"Directory created: {path}")
                return {
                    'success': True,
                    'created': True,
                    'changed': True,
                    'path': str(dir_path),
                    'mode': oct(mode),
                    'message': 'Directory created successfully'
                }
                
        except Exception as e:
            error_msg = f"Error creating directory {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def remove_directory(self, path: str, force: bool = False, recursive: bool = True) -> Dict:
        """
        حذف دایرکتوری
        
        Args:
            path: مسیر دایرکتوری
            force: حذف اجباری حتی اگر read-only باشد
            recursive: حذف بازگشتی
            
        Returns:
            نتیجه عملیات
        """
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                logger.debug(f"Directory does not exist: {path}")
                return {
                    'success': True,
                    'removed': False,
                    'changed': False,
                    'path': str(dir_path),
                    'message': 'Directory does not exist'
                }
            
            if not dir_path.is_dir():
                return {
                    'success': False,
                    'error': f"Path is not a directory: {path}",
                    'path': str(dir_path)
                }
            
            if force:
                # تابع helper برای حذف فایل‌های read-only
                def remove_readonly(func, path, excinfo):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                if recursive:
                    shutil.rmtree(str(dir_path), onerror=remove_readonly)
                else:
                    try:
                        dir_path.rmdir()
                    except OSError as e:
                        if "Directory not empty" in str(e):
                            return {
                                'success': False,
                                'error': f"Directory not empty: {path}",
                                'path': str(dir_path)
                            }
                        raise
            else:
                if recursive:
                    shutil.rmtree(str(dir_path))
                else:
                    dir_path.rmdir()
            
            logger.info(f"Directory removed: {path}")
            return {
                'success': True,
                'removed': True,
                'changed': True,
                'path': str(dir_path),
                'message': 'Directory removed successfully'
            }
            
        except Exception as e:
            error_msg = f"Error removing directory {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def list_directory(self, path: str, recursive: bool = False, 
                      pattern: str = None) -> Dict:
        """
        لیست محتوای دایرکتوری
        
        Args:
            path: مسیر دایرکتوری
            recursive: لیست بازگشتی
            pattern: الگوی جستجو (glob pattern)
            
        Returns:
            لیست فایل‌ها و دایرکتوری‌ها
        """
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return {
                    'success': False,
                    'error': f"Directory does not exist: {path}",
                    'path': str(dir_path)
                }
            
            if not dir_path.is_dir():
                return {
                    'success': False,
                    'error': f"Path is not a directory: {path}",
                    'path': str(dir_path)
                }
            
            items = []
            
            if pattern:
                if recursive:
                    search_path = dir_path.rglob(pattern)
                else:
                    search_path = dir_path.glob(pattern)
            else:
                if recursive:
                    search_path = dir_path.rglob('*')
                else:
                    search_path = dir_path.iterdir()
            
            for item in search_path:
                try:
                    stat_info = item.stat()
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': stat_info.st_size if item.is_file() else 0,
                        'mode': oct(stat_info.st_mode),
                        'modified': stat_info.st_mtime,
                        'accessed': stat_info.st_atime,
                        'created': stat_info.st_ctime
                    })
                except (OSError, PermissionError):
                    # اگر دسترسی نداشتیم، skip کن
                    continue
            
            result = {
                'success': True,
                'path': str(dir_path),
                'items': items,
                'total_items': len(items),
                'recursive': recursive,
                'pattern': pattern
            }
            
            logger.debug(f"Listed directory {path}: {len(items)} items")
            return result
            
        except Exception as e:
            error_msg = f"Error listing directory {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    # ==================== File Operations ====================
    
    def write_file(self, path: str, content: Union[str, bytes], 
                  mode: int = None, force: bool = True, 
                  backup: bool = False, encoding: str = 'utf-8') -> Dict:
        """
        نوشتن محتوا در فایل
        
        Args:
            path: مسیر فایل
            content: محتوا
            mode: mode فایل
            force: overwrite اگر وجود دارد
            backup: backup گرفتن از فایل موجود
            encoding: encoding برای فایل متنی
            
        Returns:
            نتیجه عملیات
        """
        try:
            file_path = Path(path)
            mode = mode or self.default_mode
            
            # بررسی existence
            file_exists = file_path.exists()
            
            if file_exists and not force:
                return {
                    'success': False,
                    'error': f"File already exists: {path}",
                    'path': str(file_path)
                }
            
            # Backup گرفتن اگر لازم باشد
            backup_path = None
            if backup and file_exists:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                shutil.copy2(str(file_path), str(backup_path))
                logger.debug(f"Backup created: {backup_path}")
            
            # ایجاد دایرکتوری والد اگر وجود ندارد
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # نوشتن محتوا
            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content, encoding=encoding)
            
            # تنظیم permissions
            os.chmod(str(file_path), mode)
            
            result = {
                'success': True,
                'created': not file_exists,
                'changed': True,
                'path': str(file_path),
                'mode': oct(mode),
                'backup': str(backup_path) if backup_path else None,
                'message': 'File created' if not file_exists else 'File updated'
            }
            
            logger.debug(f"File written: {path} ({len(content) if isinstance(content, str) else len(content)} bytes)")
            return result
            
        except Exception as e:
            error_msg = f"Error writing file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def read_file(self, path: str, encoding: str = 'utf-8') -> Dict:
        """
        خواندن فایل
        
        Args:
            path: مسیر فایل
            encoding: encoding برای فایل متنی
            
        Returns:
            محتوای فایل
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f"File does not exist: {path}",
                    'path': str(file_path)
                }
            
            if not file_path.is_file():
                return {
                    'success': False,
                    'error': f"Path is not a file: {path}",
                    'path': str(file_path)
                }
            
            # خواندن فایل
            content = file_path.read_text(encoding=encoding)
            stat_info = file_path.stat()
            
            result = {
                'success': True,
                'path': str(file_path),
                'content': content,
                'size': len(content),
                'mode': oct(stat_info.st_mode),
                'modified': stat_info.st_mtime,
                'encoding': encoding
            }
            
            logger.debug(f"File read: {path} ({len(content)} bytes)")
            return result
            
        except UnicodeDecodeError:
            # اگر فایل متنی نبود، باینری بخوان
            try:
                file_path = Path(path)
                content = file_path.read_bytes()
                stat_info = file_path.stat()
                
                result = {
                    'success': True,
                    'path': str(file_path),
                    'content': content,
                    'size': len(content),
                    'mode': oct(stat_info.st_mode),
                    'modified': stat_info.st_mtime,
                    'encoding': 'binary'
                }
                
                logger.debug(f"Binary file read: {path} ({len(content)} bytes)")
                return result
                
            except Exception as e:
                error_msg = f"Error reading binary file {path}: {str(e)}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'path': path
                }
                
        except Exception as e:
            error_msg = f"Error reading file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def copy_file(self, src: str, dest: str, force: bool = True, 
                 preserve: bool = True, backup: bool = False) -> Dict:
        """
        کپی فایل
        
        Args:
            src: مسیر مبدأ
            dest: مسیر مقصد
            force: overwrite اگر وجود دارد
            preserve: حفظ metadata
            backup: backup گرفتن از فایل مقصد
            
        Returns:
            نتیجه عملیات
        """
        try:
            src_path = Path(src)
            dest_path = Path(dest)
            
            if not src_path.exists():
                return {
                    'success': False,
                    'error': f"Source file does not exist: {src}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            if not src_path.is_file():
                return {
                    'success': False,
                    'error': f"Source is not a file: {src}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            # بررسی existence فایل مقصد
            dest_exists = dest_path.exists()
            
            if dest_exists and not force:
                return {
                    'success': False,
                    'error': f"Destination file already exists: {dest}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            # Backup گرفتن اگر لازم باشد
            backup_path = None
            if backup and dest_exists:
                backup_path = dest_path.with_suffix(dest_path.suffix + '.bak')
                shutil.copy2(str(dest_path), str(backup_path))
                logger.debug(f"Backup created: {backup_path}")
            
            # ایجاد دایرکتوری والد اگر وجود ندارد
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # کپی فایل
            if preserve:
                shutil.copy2(str(src_path), str(dest_path))
            else:
                shutil.copy(str(src_path), str(dest_path))
            
            result = {
                'success': True,
                'copied': True,
                'changed': True,
                'src': str(src_path),
                'dest': str(dest_path),
                'size': src_path.stat().st_size,
                'backup': str(backup_path) if backup_path else None,
                'preserve': preserve,
                'message': 'File copied successfully'
            }
            
            logger.info(f"File copied: {src} -> {dest}")
            return result
            
        except Exception as e:
            error_msg = f"Error copying file {src} to {dest}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'src': src,
                'dest': dest
            }
    
    def move_file(self, src: str, dest: str, force: bool = True, 
                 backup: bool = False) -> Dict:
        """
        انتقال فایل
        
        Args:
            src: مسیر مبدأ
            dest: مسیر مقصد
            force: overwrite اگر وجود دارد
            backup: backup گرفتن از فایل مقصد
            
        Returns:
            نتیجه عملیات
        """
        try:
            src_path = Path(src)
            dest_path = Path(dest)
            
            if not src_path.exists():
                return {
                    'success': False,
                    'error': f"Source file does not exist: {src}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            if not src_path.is_file():
                return {
                    'success': False,
                    'error': f"Source is not a file: {src}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            # بررسی existence فایل مقصد
            dest_exists = dest_path.exists()
            
            if dest_exists and not force:
                return {
                    'success': False,
                    'error': f"Destination file already exists: {dest}",
                    'src': str(src_path),
                    'dest': str(dest_path)
                }
            
            # Backup گرفتن اگر لازم باشد
            backup_path = None
            if backup and dest_exists:
                backup_path = dest_path.with_suffix(dest_path.suffix + '.bak')
                shutil.copy2(str(dest_path), str(backup_path))
                logger.debug(f"Backup created: {backup_path}")
            
            # ایجاد دایرکتوری والد اگر وجود ندارد
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # انتقال فایل
            shutil.move(str(src_path), str(dest_path))
            
            result = {
                'success': True,
                'moved': True,
                'changed': True,
                'src': str(src_path),
                'dest': str(dest_path),
                'size': dest_path.stat().st_size,
                'backup': str(backup_path) if backup_path else None,
                'message': 'File moved successfully'
            }
            
            logger.info(f"File moved: {src} -> {dest}")
            return result
            
        except Exception as e:
            error_msg = f"Error moving file {src} to {dest}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'src': src,
                'dest': dest
            }
    
    def delete_file(self, path: str, force: bool = True) -> Dict:
        """
        حذف فایل
        
        Args:
            path: مسیر فایل
            force: حذف اجباری حتی اگر read-only باشد
            
        Returns:
            نتیجه عملیات
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                logger.debug(f"File does not exist: {path}")
                return {
                    'success': True,
                    'deleted': False,
                    'changed': False,
                    'path': str(file_path),
                    'message': 'File does not exist'
                }
            
            if not file_path.is_file():
                return {
                    'success': False,
                    'error': f"Path is not a file: {path}",
                    'path': str(file_path)
                }
            
            if force:
                # حذف فایل read-only
                os.chmod(str(file_path), stat.S_IWRITE)
            
            file_size = file_path.stat().st_size
            file_path.unlink()
            
            result = {
                'success': True,
                'deleted': True,
                'changed': True,
                'path': str(file_path),
                'size': file_size,
                'message': 'File deleted successfully'
            }
            
            logger.info(f"File deleted: {path} ({file_size} bytes)")
            return result
            
        except Exception as e:
            error_msg = f"Error deleting file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    # ==================== File Properties ====================
    
    def get_file_info(self, path: str) -> Dict:
        """
        دریافت اطلاعات فایل
        
        Args:
            path: مسیر فایل
            
        Returns:
            اطلاعات فایل
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f"File does not exist: {path}",
                    'path': str(file_path)
                }
            
            stat_info = file_path.stat()
            
            info = {
                'success': True,
                'path': str(file_path),
                'name': file_path.name,
                'parent': str(file_path.parent),
                'type': 'directory' if file_path.is_dir() else 'file',
                'size': stat_info.st_size,
                'mode': oct(stat_info.st_mode),
                'uid': stat_info.st_uid,
                'gid': stat_info.st_gid,
                'modified': stat_info.st_mtime,
                'accessed': stat_info.st_atime,
                'created': stat_info.st_ctime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir(),
                'is_symlink': file_path.is_symlink(),
                'exists': True
            }
            
            # اضافه کردن checksum برای فایل‌ها
            if file_path.is_file():
                info['md5'] = self._calculate_checksum(str(file_path), 'md5')
                info['sha256'] = self._calculate_checksum(str(file_path), 'sha256')
            
            return info
            
        except Exception as e:
            error_msg = f"Error getting file info for {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def _calculate_checksum(self, path: str, algorithm: str = 'md5') -> str:
        """
        محاسبه checksum فایل
        
        Args:
            path: مسیر فایل
            algorithm: الگوریتم hash
            
        Returns:
            checksum
        """
        try:
            hash_func = hashlib.new(algorithm)
            
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception:
            return None
    
    def change_permissions(self, path: str, mode: int, recursive: bool = False) -> Dict:
        """
        تغییر permissions فایل یا دایرکتوری
        
        Args:
            path: مسیر
            mode: mode جدید
            recursive: تغییر بازگشتی
            
        Returns:
            نتیجه عملیات
        """
        try:
            item_path = Path(path)
            
            if not item_path.exists():
                return {
                    'success': False,
                    'error': f"Path does not exist: {path}",
                    'path': str(item_path)
                }
            
            old_mode = oct(item_path.stat().st_mode)
            
            if recursive and item_path.is_dir():
                for root, dirs, files in os.walk(str(item_path)):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), mode)
                    for f in files:
                        os.chmod(os.path.join(root, f), mode)
            
            os.chmod(str(item_path), mode)
            
            result = {
                'success': True,
                'changed': True,
                'path': str(item_path),
                'old_mode': old_mode,
                'new_mode': oct(mode),
                'recursive': recursive,
                'message': 'Permissions changed successfully'
            }
            
            logger.info(f"Permissions changed: {path} {old_mode} -> {oct(mode)}")
            return result
            
        except Exception as e:
            error_msg = f"Error changing permissions for {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def change_ownership(self, path: str, uid: int = None, gid: int = None, 
                        recursive: bool = False) -> Dict:
        """
        تغییر ownership فایل یا دایرکتوری
        
        Args:
            path: مسیر
            uid: user ID جدید
            gid: group ID جدید
            recursive: تغییر بازگشتی
            
        Returns:
            نتیجه عملیات
        """
        try:
            item_path = Path(path)
            
            if not item_path.exists():
                return {
                    'success': False,
                    'error': f"Path does not exist: {path}",
                    'path': str(item_path)
                }
            
            stat_info = item_path.stat()
            old_uid = stat_info.st_uid
            old_gid = stat_info.st_gid
            
            # اگر uid یا gid مشخص نشده، از مقدار قبلی استفاده کن
            uid = uid if uid is not None else old_uid
            gid = gid if gid is not None else old_gid
            
            if recursive and item_path.is_dir():
                for root, dirs, files in os.walk(str(item_path)):
                    for d in dirs:
                        os.chown(os.path.join(root, d), uid, gid)
                    for f in files:
                        os.chown(os.path.join(root, f), uid, gid)
            
            os.chown(str(item_path), uid, gid)
            
            result = {
                'success': True,
                'changed': uid != old_uid or gid != old_gid,
                'path': str(item_path),
                'old_uid': old_uid,
                'old_gid': old_gid,
                'new_uid': uid,
                'new_gid': gid,
                'recursive': recursive,
                'message': 'Ownership changed successfully'
            }
            
            logger.info(f"Ownership changed: {path} UID:{old_uid}->{uid} GID:{old_gid}->{gid}")
            return result
            
        except Exception as e:
            error_msg = f"Error changing ownership for {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    # ==================== JSON/YAML Operations ====================
    
    def read_json(self, path: str, encoding: str = 'utf-8') -> Dict:
        """
        خواندن فایل JSON
        
        Args:
            path: مسیر فایل
            encoding: encoding
            
        Returns:
            داده‌های JSON
        """
        try:
            file_result = self.read_file(path, encoding)
            
            if not file_result['success']:
                return file_result
            
            content = file_result['content']
            data = json.loads(content)
            
            return {
                'success': True,
                'path': path,
                'data': data,
                'size': len(content)
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
        except Exception as e:
            error_msg = f"Error reading JSON file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def write_json(self, path: str, data: Any, indent: int = 2, 
                  encoding: str = 'utf-8', **kwargs) -> Dict:
        """
        نوشتن فایل JSON
        
        Args:
            path: مسیر فایل
            data: داده‌ها
            indent: indentation
            encoding: encoding
            **kwargs: آرگومان‌های اضافی برای json.dumps
            
        Returns:
            نتیجه عملیات
        """
        try:
            content = json.dumps(data, indent=indent, **kwargs)
            return self.write_file(path, content, encoding=encoding)
            
        except Exception as e:
            error_msg = f"Error writing JSON file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def read_yaml(self, path: str, encoding: str = 'utf-8') -> Dict:
        """
        خواندن فایل YAML
        
        Args:
            path: مسیر فایل
            encoding: encoding
            
        Returns:
            داده‌های YAML
        """
        try:
            file_result = self.read_file(path, encoding)
            
            if not file_result['success']:
                return file_result
            
            content = file_result['content']
            data = yaml.safe_load(content)
            
            return {
                'success': True,
                'path': path,
                'data': data,
                'size': len(content)
            }
            
        except yaml.YAMLError as e:
            error_msg = f"Error parsing YAML file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
        except Exception as e:
            error_msg = f"Error reading YAML file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    def write_yaml(self, path: str, data: Any, encoding: str = 'utf-8', 
                  default_flow_style: bool = False, **kwargs) -> Dict:
        """
        نوشتن فایل YAML
        
        Args:
            path: مسیر فایل
            data: داده‌ها
            encoding: encoding
            default_flow_style: flow style
            **kwargs: آرگومان‌های اضافی برای yaml.dump
            
        Returns:
            نتیجه عملیات
        """
        try:
            content = yaml.dump(data, default_flow_style=default_flow_style, **kwargs)
            return self.write_file(path, content, encoding=encoding)
            
        except Exception as e:
            error_msg = f"Error writing YAML file {path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'path': path
            }
    
    # ==================== Temporary Files ====================
    
    def create_temp_file(self, content: Union[str, bytes] = None, 
                        suffix: str = None, prefix: str = None, 
                        dir: str = None, delete: bool = True) -> Dict:
        """
        ایجاد فایل موقت
        
        Args:
            content: محتوا (اختیاری)
            suffix: پسوند
            prefix: پیشوند
            dir: دایرکتوری
            delete: حذف خودکار
            
        Returns:
            اطلاعات فایل موقت
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode='w+' if isinstance(content, str) else 'w+b',
                suffix=suffix,
                prefix=prefix,
                dir=dir,
                delete=delete
            ) as tmp_file:
                tmp_path = tmp_file.name
                
                if content is not None:
                    if isinstance(content, str):
                        tmp_file.write(content)
                    else:
                        tmp_file.write(content)
                    tmp_file.flush()
                
                result = {
                    'success': True,
                    'path': tmp_path,
                    'name': Path(tmp_path).name,
                    'content': content,
                    'delete_on_close': delete
                }
                
                logger.debug(f"Temporary file created: {tmp_path}")
                return result
                
        except Exception as e:
            error_msg = f"Error creating temporary file: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def create_temp_directory(self, suffix: str = None, prefix: str = None, 
                             dir: str = None) -> Dict:
        """
        ایجاد دایرکتوری موقت
        
        Args:
            suffix: پسوند
            prefix: پیشوند
            dir: دایرکتوری والد
            
        Returns:
            اطلاعات دایرکتوری موقت
        """
        try:
            tmp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
            
            result = {
                'success': True,
                'path': tmp_dir,
                'name': Path(tmp_dir).name
            }
            
            logger.debug(f"Temporary directory created: {tmp_dir}")
            return result
            
        except Exception as e:
            error_msg = f"Error creating temporary directory: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def create_file_manager(config: Dict = None) -> FileManager:
    """
    تابع helper برای ایجاد File Manager
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از FileManager
    """
    return FileManager(config)