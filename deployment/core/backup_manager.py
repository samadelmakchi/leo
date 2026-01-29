#!/usr/bin/env python3
"""
Backup Manager
مدیریت backupهای volumes و databases
"""

import logging
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import json
import time

logger = logging.getLogger(__name__)


class BackupManager:
    """مدیریت backupها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Backup Manager
        
        Args:
            config: تنظیمات backup
        """
        self.config = config or {}
        
        # تنظیمات پیش‌فرض
        self.backup_dir = self.config.get('backup_dir', '/var/backups')
        self.retention_days = self.config.get('retention_days', 30)
        self.docker_socket = self.config.get('docker_socket', 'unix://var/run/docker.sock')
        
        # اطمینان از وجود دایرکتوری backup
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Backup Manager initialized. Backup dir: {self.backup_dir}")
    
    def create_backup_directory(self, customer_name: str) -> Path:
        """
        ایجاد دایرکتوری backup برای مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            مسیر دایرکتوری backup
        """
        customer_backup_dir = Path(self.backup_dir) / customer_name
        customer_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # ایجاد زیردایرکتوری‌ها
        (customer_backup_dir / 'volumes').mkdir(exist_ok=True)
        (customer_backup_dir / 'databases').mkdir(exist_ok=True)
        (customer_backup_dir / 'logs').mkdir(exist_ok=True)
        
        return customer_backup_dir
    
    def backup_volumes(self, customer_name: str, volumes_info: Dict) -> Dict:
        """
        Backup گرفتن از volumes
        
        Args:
            customer_name: نام مشتری
            volumes_info: اطلاعات volumes
            
        Returns:
            نتیجه backup
        """
        try:
            customer_backup_dir = self.create_backup_directory(customer_name)
            volumes_dir = customer_backup_dir / 'volumes'
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = volumes_dir / f"volumes_{timestamp}.tar.gz"
            
            logger.info(f"Starting volumes backup for {customer_name}")
            
            # جمع‌آوری لیست volumes برای backup
            volumes_to_backup = []
            
            # پردازش volumes_info
            if isinstance(volumes_info, dict):
                # اگر volumes_info یک دیکشنری است
                for volume_name, volume_path in volumes_info.items():
                    if Path(volume_path).exists():
                        volumes_to_backup.append(volume_path)
                        logger.debug(f"Added volume for backup: {volume_name} -> {volume_path}")
                    else:
                        logger.warning(f"Volume path does not exist: {volume_path}")
            
            elif isinstance(volumes_info, list):
                # اگر volumes_info یک لیست است
                for volume_path in volumes_info:
                    if Path(volume_path).exists():
                        volumes_to_backup.append(volume_path)
                        logger.debug(f"Added volume for backup: {volume_path}")
                    else:
                        logger.warning(f"Volume path does not exist: {volume_path}")
            
            elif isinstance(volumes_info, str):
                # اگر volumes_info یک رشته است (مسیر فایل)
                volumes_file = Path(volumes_info)
                if volumes_file.exists():
                    with open(volumes_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if Path(line).exists():
                                    volumes_to_backup.append(line)
                                else:
                                    logger.warning(f"Volume path from file does not exist: {line}")
            
            if not volumes_to_backup:
                return {
                    'success': False,
                    'error': 'No valid volumes found for backup',
                    'customer': customer_name
                }
            
            # ایجاد tar archive از volumes
            with tarfile.open(backup_file, 'w:gz') as tar:
                for volume_path in volumes_to_backup:
                    try:
                        tar.add(volume_path, arcname=Path(volume_path).name)
                        logger.debug(f"Added to backup: {volume_path}")
                    except Exception as e:
                        logger.warning(f"Failed to add {volume_path} to backup: {str(e)}")
            
            # محاسبه سایز backup
            backup_size = backup_file.stat().st_size
            
            result = {
                'success': True,
                'customer': customer_name,
                'backup_type': 'volumes',
                'backup_file': str(backup_file),
                'backup_size': backup_size,
                'backup_size_human': self._format_bytes(backup_size),
                'volumes_count': len(volumes_to_backup),
                'timestamp': timestamp,
                'message': f"Volumes backup completed successfully: {len(volumes_to_backup)} volumes"
            }
            
            logger.info(f"Volumes backup completed for {customer_name}: {result['backup_size_human']}")
            
            # اجرای retention policy
            self._apply_retention_policy(volumes_dir, 'volumes')
            
            return result
            
        except Exception as e:
            error_msg = f"Error backing up volumes for {customer_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name,
                'backup_type': 'volumes'
            }
    
    def backup_database(self, db_config: Dict, backup_dir: Path) -> Optional[Path]:
        """
        Backup گرفتن از یک دیتابیس
        
        Args:
            db_config: تنظیمات دیتابیس
            backup_dir: دایرکتوری backup
            
        Returns:
            مسیر فایل backup یا None
        """
        try:
            db_type = db_config.get('type', 'mysql').lower()
            db_name = db_config.get('database')
            db_user = db_config.get('username')
            db_password = db_config.get('password')
            db_host = db_config.get('host', 'localhost')
            db_port = db_config.get('port', '3306')
            container_name = db_config.get('container')
            
            if not all([db_name, db_user, db_password]):
                logger.error(f"Incomplete database config: {db_config}")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{db_name}_{timestamp}.sql"
            
            logger.info(f"Backing up database: {db_name}")
            
            if db_type == 'mysql' or db_type == 'mariadb':
                # Backup MySQL/MariaDB
                if container_name:
                    # استفاده از docker exec اگر container مشخص شده
                    cmd = [
                        'docker', 'exec', container_name,
                        'mysqldump',
                        f'--user={db_user}',
                        f'--password={db_password}',
                        '--single-transaction',
                        '--routines',
                        '--triggers',
                        '--events',
                        db_name
                    ]
                else:
                    # استفاده مستقیم از mysqldump
                    cmd = [
                        'mysqldump',
                        f'--host={db_host}',
                        f'--port={db_port}',
                        f'--user={db_user}',
                        f'--password={db_password}',
                        '--single-transaction',
                        '--routines',
                        '--triggers',
                        '--events',
                        db_name
                    ]
                
                with open(backup_file, 'w') as f:
                    process = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if process.returncode != 0:
                        logger.error(f"Database backup failed for {db_name}: {process.stderr}")
                        backup_file.unlink(missing_ok=True)
                        return None
            
            elif db_type == 'postgresql' or db_type == 'postgres':
                # Backup PostgreSQL
                # برای سادگی فعلا فقط MySQL را پشتیبانی می‌کنیم
                logger.warning(f"PostgreSQL backup not implemented yet for {db_name}")
                return None
            
            else:
                logger.warning(f"Unsupported database type: {db_type}")
                return None
            
            # فشرده سازی backup
            compressed_file = backup_file.with_suffix('.sql.gz')
            cmd = ['gzip', '-c', str(backup_file)]
            
            with open(compressed_file, 'w') as f:
                subprocess.run(cmd, stdout=f)
            
            # حذف فایل اصلی
            backup_file.unlink()
            
            logger.debug(f"Database backup created: {compressed_file}")
            return compressed_file
            
        except Exception as e:
            logger.error(f"Error backing up database {db_config.get('database', 'unknown')}: {str(e)}")
            return None
    
    def backup_databases(self, customer_name: str, databases_info: Dict) -> Dict:
        """
        Backup گرفتن از همه دیتابیس‌ها
        
        Args:
            customer_name: نام مشتری
            databases_info: اطلاعات دیتابیس‌ها
            
        Returns:
            نتیجه backup
        """
        try:
            customer_backup_dir = self.create_backup_directory(customer_name)
            databases_dir = customer_backup_dir / 'databases'
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            logger.info(f"Starting databases backup for {customer_name}")
            
            # پردازش databases_info
            databases_to_backup = []
            
            if isinstance(databases_info, dict):
                # اگر یک دیکشنری از دیتابیس‌ها است
                for db_name, db_config in databases_info.items():
                    if isinstance(db_config, dict):
                        databases_to_backup.append(db_config)
                    else:
                        logger.warning(f"Invalid database config for {db_name}")
            
            elif isinstance(databases_info, list):
                # اگر یک لیست از دیکشنری‌ها است
                for db_config in databases_info:
                    if isinstance(db_config, dict):
                        databases_to_backup.append(db_config)
                    else:
                        logger.warning(f"Invalid database config in list: {db_config}")
            
            elif isinstance(databases_info, str):
                # اگر یک رشته است (مسیر فایل)
                dbs_file = Path(databases_info)
                if dbs_file.exists():
                    with open(dbs_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # پارس کردن خط (فرمت: type,db,user,pass,container)
                                parts = line.split(',')
                                if len(parts) >= 5:
                                    db_config = {
                                        'type': parts[0].strip(),
                                        'database': parts[1].strip(),
                                        'username': parts[2].strip(),
                                        'password': parts[3].strip(),
                                        'container': parts[4].strip()
                                    }
                                    databases_to_backup.append(db_config)
            
            if not databases_to_backup:
                return {
                    'success': False,
                    'error': 'No valid databases found for backup',
                    'customer': customer_name
                }
            
            # Backup هر دیتابیس
            successful_backups = []
            failed_backups = []
            
            for db_config in databases_to_backup:
                backup_file = self.backup_database(db_config, databases_dir)
                
                if backup_file:
                    successful_backups.append({
                        'database': db_config.get('database'),
                        'backup_file': str(backup_file),
                        'size': backup_file.stat().st_size
                    })
                else:
                    failed_backups.append(db_config.get('database', 'unknown'))
            
            # ایجاد archive از همه backupها
            if successful_backups:
                archive_file = databases_dir / f"databases_{timestamp}.tar.gz"
                
                with tarfile.open(archive_file, 'w:gz') as tar:
                    for backup_info in successful_backups:
                        backup_path = Path(backup_info['backup_file'])
                        tar.add(backup_path, arcname=backup_path.name)
                        
                        # حذف فایل اصلی بعد از اضافه شدن به archive
                        backup_path.unlink()
                
                archive_size = archive_file.stat().st_size
            else:
                archive_file = None
                archive_size = 0
            
            result = {
                'success': len(failed_backups) == 0,
                'customer': customer_name,
                'backup_type': 'databases',
                'total_databases': len(databases_to_backup),
                'successful': len(successful_backups),
                'failed': len(failed_backups),
                'failed_databases': failed_backups,
                'archive_file': str(archive_file) if archive_file else None,
                'archive_size': archive_size,
                'archive_size_human': self._format_bytes(archive_size) if archive_size else '0B',
                'timestamp': timestamp,
                'message': f"Databases backup completed: {len(successful_backups)} successful, {len(failed_backups)} failed"
            }
            
            if result['success']:
                logger.info(f"Databases backup completed for {customer_name}: {result['archive_size_human']}")
            else:
                logger.warning(f"Databases backup partially failed for {customer_name}: {result['message']}")
            
            # اجرای retention policy
            self._apply_retention_policy(databases_dir, 'databases')
            
            return result
            
        except Exception as e:
            error_msg = f"Error backing up databases for {customer_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name,
                'backup_type': 'databases'
            }
    
    def restore_volumes(self, customer_name: str, backup_file: str, target_dir: str = None) -> Dict:
        """
        بازگردانی volumes از backup
        
        Args:
            customer_name: نام مشتری
            backup_file: مسیر فایل backup
            target_dir: دایرکتوری مقصد (اختیاری)
            
        Returns:
            نتیجه restore
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f"Backup file not found: {backup_file}",
                    'customer': customer_name
                }
            
            if target_dir:
                restore_dir = Path(target_dir)
            else:
                restore_dir = Path(self.backup_dir) / customer_name / 'restore' / 'volumes'
            
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Restoring volumes for {customer_name} from {backup_file}")
            
            # استخراج backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(path=restore_dir)
            
            # لیست فایل‌های استخراج شده
            extracted_files = list(restore_dir.rglob('*'))
            
            result = {
                'success': True,
                'customer': customer_name,
                'backup_file': backup_file,
                'restore_dir': str(restore_dir),
                'extracted_files': len(extracted_files),
                'message': f"Volumes restored successfully to {restore_dir}"
            }
            
            logger.info(f"Volumes restored for {customer_name}: {len(extracted_files)} files extracted")
            
            return result
            
        except Exception as e:
            error_msg = f"Error restoring volumes for {customer_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name,
                'backup_file': backup_file
            }
    
    def restore_database(self, customer_name: str, backup_file: str, db_config: Dict) -> Dict:
        """
        بازگردانی یک دیتابیس از backup
        
        Args:
            customer_name: نام مشتری
            backup_file: مسیر فایل backup
            db_config: تنظیمات دیتابیس
            
        Returns:
            نتیجه restore
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f"Backup file not found: {backup_file}",
                    'customer': customer_name,
                    'database': db_config.get('database', 'unknown')
                }
            
            db_type = db_config.get('type', 'mysql').lower()
            db_name = db_config.get('database')
            db_user = db_config.get('username')
            db_password = db_config.get('password')
            db_host = db_config.get('host', 'localhost')
            db_port = db_config.get('port', '3306')
            container_name = db_config.get('container')
            
            logger.info(f"Restoring database {db_name} for {customer_name}")
            
            if db_type == 'mysql' or db_type == 'mariadb':
                # ابتدا دیتابیس را ایجاد کن (اگر وجود ندارد)
                create_db_cmd = [
                    'mysql',
                    f'--host={db_host}',
                    f'--port={db_port}',
                    f'--user={db_user}',
                    f'--password={db_password}',
                    '-e', f"CREATE DATABASE IF NOT EXISTS {db_name};"
                ]
                
                if container_name:
                    create_db_cmd = ['docker', 'exec', container_name] + create_db_cmd[1:]
                
                subprocess.run(create_db_cmd, capture_output=True)
                
                # سپس restore کن
                if backup_path.suffix == '.gz':
                    # decompress و restore
                    decompress_cmd = ['gunzip', '-c', str(backup_path)]
                    restore_cmd = [
                        'mysql',
                        f'--host={db_host}',
                        f'--port={db_port}',
                        f'--user={db_user}',
                        f'--password={db_password}',
                        db_name
                    ]
                    
                    if container_name:
                        # برای docker، باید فایل را به container کپی کنیم
                        temp_file = f"/tmp/{backup_path.name.replace('.gz', '')}"
                        
                        # کپی فایل به container
                        copy_cmd = ['docker', 'cp', str(backup_path), f"{container_name}:{temp_file}.gz"]
                        subprocess.run(copy_cmd, capture_output=True)
                        
                        # decompress در container
                        decompress_in_container = ['docker', 'exec', container_name, 'gunzip', '-f', f"{temp_file}.gz"]
                        subprocess.run(decompress_in_container, capture_output=True)
                        
                        # restore در container
                        restore_in_container = [
                            'docker', 'exec', container_name,
                            'mysql',
                            f'--user={db_user}',
                            f'--password={db_password}',
                            db_name,
                            '-e', f"source {temp_file};"
                        ]
                        
                        process = subprocess.run(
                            restore_in_container,
                            capture_output=True,
                            text=True
                        )
                        
                        # حذف فایل موقت
                        cleanup_cmd = ['docker', 'exec', container_name, 'rm', '-f', temp_file]
                        subprocess.run(cleanup_cmd, capture_output=True)
                        
                    else:
                        # restore مستقیم
                        decompress = subprocess.Popen(decompress_cmd, stdout=subprocess.PIPE)
                        restore = subprocess.Popen(restore_cmd, stdin=decompress.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        decompress.stdout.close()
                        output, error = restore.communicate()
                        process = subprocess.CompletedProcess(restore_cmd, restore.returncode, output, error)
                
                else:
                    # فایل بدون فشرده‌سازی
                    restore_cmd = [
                        'mysql',
                        f'--host={db_host}',
                        f'--port={db_port}',
                        f'--user={db_user}',
                        f'--password={db_password}',
                        db_name,
                        '-e', f"source {backup_path};"
                    ]
                    
                    if container_name:
                        restore_cmd = ['docker', 'exec', container_name] + restore_cmd[1:]
                    
                    process = subprocess.run(
                        restore_cmd,
                        capture_output=True,
                        text=True
                    )
                
                if process.returncode == 0:
                    result = {
                        'success': True,
                        'customer': customer_name,
                        'database': db_name,
                        'backup_file': backup_file,
                        'message': f"Database {db_name} restored successfully"
                    }
                    logger.info(f"Database {db_name} restored for {customer_name}")
                else:
                    result = {
                        'success': False,
                        'error': f"Database restore failed: {process.stderr}",
                        'customer': customer_name,
                        'database': db_name,
                        'backup_file': backup_file
                    }
                    logger.error(f"Failed to restore database {db_name}: {process.stderr}")
            
            else:
                result = {
                    'success': False,
                    'error': f"Unsupported database type: {db_type}",
                    'customer': customer_name,
                    'database': db_name
                }
            
            return result
            
        except Exception as e:
            error_msg = f"Error restoring database {db_config.get('database', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name,
                'database': db_config.get('database', 'unknown')
            }
    
    def list_backups(self, customer_name: str, backup_type: str = None) -> Dict:
        """
        لیست backupهای موجود
        
        Args:
            customer_name: نام مشتری
            backup_type: نوع backup (volumes, databases, یا None برای همه)
            
        Returns:
            لیست backupها
        """
        try:
            customer_backup_dir = Path(self.backup_dir) / customer_name
            
            if not customer_backup_dir.exists():
                return {
                    'success': True,
                    'customer': customer_name,
                    'backups': [],
                    'message': 'No backups found'
                }
            
            backups = []
            
            if backup_type is None or backup_type == 'volumes':
                volumes_dir = customer_backup_dir / 'volumes'
                if volumes_dir.exists():
                    for backup_file in volumes_dir.glob('*.tar.gz'):
                        backups.append({
                            'type': 'volumes',
                            'file': backup_file.name,
                            'path': str(backup_file),
                            'size': backup_file.stat().st_size,
                            'size_human': self._format_bytes(backup_file.stat().st_size),
                            'modified': backup_file.stat().st_mtime,
                            'modified_human': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            if backup_type is None or backup_type == 'databases':
                databases_dir = customer_backup_dir / 'databases'
                if databases_dir.exists():
                    for backup_file in databases_dir.glob('*.tar.gz'):
                        backups.append({
                            'type': 'databases',
                            'file': backup_file.name,
                            'path': str(backup_file),
                            'size': backup_file.stat().st_size,
                            'size_human': self._format_bytes(backup_file.stat().st_size),
                            'modified': backup_file.stat().st_mtime,
                            'modified_human': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            # مرتب کردن بر اساس تاریخ (جدیدترین اول)
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'success': True,
                'customer': customer_name,
                'total_backups': len(backups),
                'backups': backups
            }
            
        except Exception as e:
            error_msg = f"Error listing backups for {customer_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name
            }
    
    def delete_backup(self, customer_name: str, backup_file: str) -> Dict:
        """
        حذف یک backup
        
        Args:
            customer_name: نام مشتری
            backup_file: نام فایل backup (یا مسیر کامل)
            
        Returns:
            نتیجه حذف
        """
        try:
            backup_path = Path(backup_file)
            
            # اگر فقط نام فایل داده شده، مسیر کامل را بساز
            if not backup_path.is_absolute():
                # تشخیص نوع backup از نام فایل
                if backup_file.startswith('volumes_'):
                    backup_path = Path(self.backup_dir) / customer_name / 'volumes' / backup_file
                elif backup_file.startswith('databases_'):
                    backup_path = Path(self.backup_dir) / customer_name / 'databases' / backup_file
                else:
                    # جستجو در همه دایرکتوری‌ها
                    found = False
                    for backup_type in ['volumes', 'databases']:
                        candidate = Path(self.backup_dir) / customer_name / backup_type / backup_file
                        if candidate.exists():
                            backup_path = candidate
                            found = True
                            break
                    
                    if not found:
                        return {
                            'success': False,
                            'error': f"Backup file not found: {backup_file}",
                            'customer': customer_name
                        }
            
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f"Backup file not found: {backup_path}",
                    'customer': customer_name
                }
            
            # حذف فایل
            backup_size = backup_path.stat().st_size
            backup_path.unlink()
            
            logger.info(f"Deleted backup: {backup_path} ({self._format_bytes(backup_size)})")
            
            return {
                'success': True,
                'customer': customer_name,
                'deleted_file': str(backup_path),
                'deleted_size': backup_size,
                'deleted_size_human': self._format_bytes(backup_size),
                'message': 'Backup deleted successfully'
            }
            
        except Exception as e:
            error_msg = f"Error deleting backup {backup_file}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'customer': customer_name,
                'backup_file': backup_file
            }
    
    def cleanup_old_backups(self, customer_name: str = None) -> Dict:
        """
        حذف backupهای قدیمی بر اساس retention policy
        
        Args:
            customer_name: نام مشتری (اگر None باشد برای همه مشتری‌ها)
            
        Returns:
            نتیجه cleanup
        """
        try:
            deleted_files = []
            total_freed = 0
            
            if customer_name:
                customers = [customer_name]
            else:
                # همه مشتری‌ها
                backup_dir = Path(self.backup_dir)
                customers = [d.name for d in backup_dir.iterdir() if d.is_dir()]
            
            for customer in customers:
                customer_dir = Path(self.backup_dir) / customer
                
                if not customer_dir.exists():
                    continue
                
                # cleanup برای volumes
                volumes_dir = customer_dir / 'volumes'
                if volumes_dir.exists():
                    deleted = self._cleanup_directory(volumes_dir)
                    deleted_files.extend(deleted)
                    total_freed += sum(f['size'] for f in deleted)
                
                # cleanup برای databases
                databases_dir = customer_dir / 'databases'
                if databases_dir.exists():
                    deleted = self._cleanup_directory(databases_dir)
                    deleted_files.extend(deleted)
                    total_freed += sum(f['size'] for f in deleted)
            
            result = {
                'success': True,
                'deleted_files': len(deleted_files),
                'total_freed': total_freed,
                'total_freed_human': self._format_bytes(total_freed),
                'deleted_files_list': deleted_files,
                'message': f"Cleaned up {len(deleted_files)} old backup files, freed {self._format_bytes(total_freed)}"
            }
            
            if deleted_files:
                logger.info(f"Cleanup completed: {result['message']}")
            else:
                logger.debug("No old backups to clean up")
            
            return result
            
        except Exception as e:
            error_msg = f"Error cleaning up old backups: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _cleanup_directory(self, directory: Path) -> List[Dict]:
        """
        حذف فایل‌های قدیمی از یک دایرکتوری
        
        Args:
            directory: دایرکتوری مورد نظر
            
        Returns:
            لیست فایل‌های حذف شده
        """
        deleted = []
        now = time.time()
        cutoff = now - (self.retention_days * 24 * 3600)  # cutoff زمان
        
        for backup_file in directory.glob('*.tar.gz'):
            file_mtime = backup_file.stat().st_mtime
            
            if file_mtime < cutoff:
                file_size = backup_file.stat().st_size
                backup_file.unlink()
                
                deleted.append({
                    'file': backup_file.name,
                    'path': str(backup_file),
                    'size': file_size,
                    'age_days': int((now - file_mtime) / (24 * 3600))
                })
                
                logger.debug(f"Deleted old backup: {backup_file.name} ({self._format_bytes(file_size)}, {int((now - file_mtime) / (24 * 3600))} days old)")
        
        return deleted
    
    def _apply_retention_policy(self, directory: Path, backup_type: str):
        """
        اعمال retention policy روی یک دایرکتوری
        
        Args:
            directory: دایرکتوری backup
            backup_type: نوع backup
        """
        try:
            deleted = self._cleanup_directory(directory)
            
            if deleted:
                logger.info(f"Retention policy applied to {backup_type}: deleted {len(deleted)} old backups")
        except Exception as e:
            logger.warning(f"Error applying retention policy to {directory}: {str(e)}")
    
    def _format_bytes(self, size_bytes: int) -> str:
        """
        فرمت کردن سایز به واحدهای خوانا
        
        Args:
            size_bytes: سایز به بایت
            
        Returns:
            رشته فرمت شده
        """
        if size_bytes == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024.0
            unit_index += 1
        
        return f"{size_bytes:.2f} {units[unit_index]}"
    
    def get_backup_stats(self, customer_name: str = None) -> Dict:
        """
        دریافت آمار backupها
        
        Args:
            customer_name: نام مشتری (اگر None باشد برای همه)
            
        Returns:
            آمار backupها
        """
        try:
            stats = {
                'total_customers': 0,
                'total_backups': 0,
                'total_size': 0,
                'customers': []
            }
            
            if customer_name:
                customers = [customer_name]
            else:
                backup_dir = Path(self.backup_dir)
                customers = [d.name for d in backup_dir.iterdir() if d.is_dir()]
            
            stats['total_customers'] = len(customers)
            
            for customer in customers:
                customer_dir = Path(self.backup_dir) / customer
                
                if not customer_dir.exists():
                    continue
                
                customer_stats = {
                    'name': customer,
                    'volumes_backups': 0,
                    'databases_backups': 0,
                    'total_backups': 0,
                    'total_size': 0
                }
                
                # volumes
                volumes_dir = customer_dir / 'volumes'
                if volumes_dir.exists():
                    for backup_file in volumes_dir.glob('*.tar.gz'):
                        customer_stats['volumes_backups'] += 1
                        customer_stats['total_backups'] += 1
                        customer_stats['total_size'] += backup_file.stat().st_size
                
                # databases
                databases_dir = customer_dir / 'databases'
                if databases_dir.exists():
                    for backup_file in databases_dir.glob('*.tar.gz'):
                        customer_stats['databases_backups'] += 1
                        customer_stats['total_backups'] += 1
                        customer_stats['total_size'] += backup_file.stat().st_size
                
                customer_stats['total_size_human'] = self._format_bytes(customer_stats['total_size'])
                stats['customers'].append(customer_stats)
                stats['total_backups'] += customer_stats['total_backups']
                stats['total_size'] += customer_stats['total_size']
            
            stats['total_size_human'] = self._format_bytes(stats['total_size'])
            
            return {
                'success': True,
                'stats': stats,
                'retention_days': self.retention_days,
                'backup_dir': self.backup_dir
            }
            
        except Exception as e:
            error_msg = f"Error getting backup stats: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


# تابع helper برای استفاده آسان
def create_backup_manager(config: Dict = None) -> BackupManager:
    """
    تابع helper برای ایجاد Backup Manager
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از BackupManager
    """
    return BackupManager(config)


if __name__ == "__main__":
    # تست Backup Manager
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ایجاد Backup Manager
    manager = BackupManager({
        'backup_dir': '/tmp/test-backups',
        'retention_days': 7
    })
    
    # تست backup volumes
    print("Testing volumes backup...")
    volumes_info = {
        'volume1': '/tmp/test-volume-1',
        'volume2': '/tmp/test-volume-2'
    }
    
    # ایجاد دایرکتوری‌های تست
    for path in volumes_info.values():
        Path(path).mkdir(parents=True, exist_ok=True)
        (Path(path) / 'test.txt').write_text('Test content')
    
    result = manager.backup_volumes('test-customer', volumes_info)
    print(json.dumps(result, indent=2))
    
    # تست list backups
    print("\nListing backups...")
    list_result = manager.list_backups('test-customer')
    print(json.dumps(list_result, indent=2))
    
    # تست get stats
    print("\nBackup stats...")
    stats_result = manager.get_backup_stats()
    print(json.dumps(stats_result, indent=2))
    
    # تمیز کردن
    import shutil
    shutil.rmtree('/tmp/test-backups', ignore_errors=True)
    for path in volumes_info.values():
        shutil.rmtree(path, ignore_errors=True)