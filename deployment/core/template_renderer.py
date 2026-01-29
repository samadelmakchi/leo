#!/usr/bin/env python3
"""
Template Renderer
رندر کردن templateهای Jinja2
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import jinja2
import hashlib

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """رندر کردن templateها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Template Renderer
        
        Args:
            config: تنظیمات template
        """
        self.config = config or {}
        
        # تنظیمات Jinja2
        self.template_dirs = self.config.get('template_dirs', [])
        self.autoescape = self.config.get('autoescape', True)
        self.trim_blocks = self.config.get('trim_blocks', True)
        self.lstrip_blocks = self.config.get('lstrip_blocks', True)
        self.keep_trailing_newline = self.config.get('keep_trailing_newline', False)
        
        # ایجاد environment
        self.env = self._create_jinja2_environment()
        
        # فیلترها و globalهای سفارشی
        self._register_custom_filters()
        self._register_custom_globals()
        
        logger.info("Template Renderer initialized")
    
    def _create_jinja2_environment(self) -> jinja2.Environment:
        """
        ایجاد Jinja2 environment
        
        Returns:
            Jinja2 environment
        """
        # اضافه کردن دایرکتوری جاری به template dirs
        template_dirs = self.template_dirs.copy()
        template_dirs.append(str(Path.cwd()))
        
        # ایجاد loader
        loader = jinja2.FileSystemLoader(template_dirs)
        
        # ایجاد environment
        env = jinja2.Environment(
            loader=loader,
            autoescape=self.autoescape,
            trim_blocks=self.trim_blocks,
            lstrip_blocks=self.lstrip_blocks,
            keep_trailing_newline=self.keep_trailing_newline
        )
        
        return env
    
    def _register_custom_filters(self):
        """ثبت فیلترهای سفارشی"""
        # فیلتر format_bytes
        def format_bytes(value: int) -> str:
            """فرمت کردن سایز به واحدهای خوانا"""
            if value == 0:
                return "0B"
            
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            unit_index = 0
            
            while value >= 1024 and unit_index < len(units) - 1:
                value /= 1024.0
                unit_index += 1
            
            return f"{value:.2f} {units[unit_index]}"
        
        self.env.filters['format_bytes'] = format_bytes
        
        # فیلتر to_yaml
        def to_yaml(value: Any, indent: int = 2) -> str:
            """تبدیل به YAML"""
            import yaml
            return yaml.dump(value, indent=indent, default_flow_style=False)
        
        self.env.filters['to_yaml'] = to_yaml
        
        # فیلتر to_json
        def to_json(value: Any, indent: int = 2) -> str:
            """تبدیل به JSON"""
            import json
            return json.dumps(value, indent=indent, default=str)
        
        self.env.filters['to_json'] = to_json
        
        # فیلتر basename
        def basename(path: str) -> str:
            """دریافت نام فایل از مسیر"""
            return Path(path).name
        
        self.env.filters['basename'] = basename
        
        # فیلتر dirname
        def dirname(path: str) -> str:
            """دریافت نام دایرکتوری از مسیر"""
            return str(Path(path).parent)
        
        self.env.filters['dirname'] = dirname
        
        # فیلتر join_path
        def join_path(base: str, *parts) -> str:
            """اتصال مسیرها"""
            return str(Path(base).joinpath(*parts))
        
        self.env.filters['join_path'] = join_path
        
        logger.debug("Custom filters registered")
    
    def _register_custom_globals(self):
        """ثبت globalهای سفارشی"""
        # تابع now
        def now(format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
            """زمان فعلی"""
            return datetime.now().strftime(format_str)
        
        self.env.globals['now'] = now
        
        # تابع uuid
        def generate_uuid() -> str:
            """تولید UUID"""
            import uuid
            return str(uuid.uuid4())
        
        self.env.globals['uuid'] = generate_uuid
        
        # تابع env_var
        def get_env_var(name: str, default: str = '') -> str:
            """دریافت متغیر محیطی"""
            return os.getenv(name, default)
        
        self.env.globals['env_var'] = get_env_var
        
        logger.debug("Custom globals registered")
    
    def render_template(self, template_path: str, output_path: str, 
                       context: Dict[str, Any], mode: int = None,
                       backup: bool = False, force: bool = True) -> Dict:
        """
        رندر کردن template و ذخیره در فایل
        
        Args:
            template_path: مسیر template
            output_path: مسیر فایل خروجی
            context: context برای template
            mode: mode فایل خروجی
            backup: backup گرفتن از فایل موجود
            force: overwrite اگر فایل وجود دارد
            
        Returns:
            نتیجه رندر
        """
        try:
            output_file = Path(output_path)
            
            # بررسی existence فایل خروجی
            if output_file.exists() and not force:
                return {
                    'success': False,
                    'error': f"Output file already exists: {output_path}",
                    'template': template_path,
                    'output': output_path
                }
            
            # رندر template
            rendered_content = self.render_template_string(template_path, context)
            
            if not rendered_content['success']:
                return rendered_content
            
            content = rendered_content['content']
            
            # Backup گرفتن اگر لازم باشد
            backup_path = None
            if backup and output_file.exists():
                backup_path = output_file.with_suffix(output_file.suffix + '.bak')
                shutil.copy2(str(output_file), str(backup_path))
                logger.debug(f"Backup created: {backup_path}")
            
            # ایجاد دایرکتوری والد اگر وجود ندارد
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # نوشتن محتوا
            output_file.write_text(content, encoding='utf-8')
            
            # تنظیم permissions
            if mode is not None:
                os.chmod(str(output_file), mode)
            
            # محاسبه checksum
            md5_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            result = {
                'success': True,
                'template': template_path,
                'output': output_path,
                'backup': str(backup_path) if backup_path else None,
                'content_size': len(content),
                'md5': md5_hash,
                'mode': oct(mode) if mode is not None else None,
                'changed': True,
                'message': f"Template rendered successfully: {template_path} -> {output_path}"
            }
            
            logger.info(f"Template rendered: {template_path} -> {output_path} ({len(content)} bytes)")
            return result
            
        except Exception as e:
            error_msg = f"Error rendering template {template_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'template': template_path,
                'output': output_path
            }
    
    def render_template_string(self, template_path: str, 
                             context: Dict[str, Any]) -> Dict:
        """
        رندر کردن template و بازگشت به عنوان رشته
        
        Args:
            template_path: مسیر template
            context: context برای template
            
        Returns:
            محتوای رندر شده
        """
        try:
            # بارگذاری template
            template = self.env.get_template(template_path)
            
            # رندر template با context
            rendered = template.render(**context)
            
            return {
                'success': True,
                'template': template_path,
                'content': rendered,
                'size': len(rendered),
                'message': 'Template rendered successfully'
            }
            
        except jinja2.TemplateNotFound as e:
            error_msg = f"Template not found: {template_path}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'template': template_path
            }
        except jinja2.TemplateSyntaxError as e:
            error_msg = f"Template syntax error in {template_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'template': template_path,
                'line': e.lineno,
                'message': e.message
            }
        except Exception as e:
            error_msg = f"Error rendering template {template_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'template': template_path
            }
    
    def render_string_template(self, template_string: str, 
                             context: Dict[str, Any]) -> Dict:
        """
        رندر کردن template از رشته
        
        Args:
            template_string: template به صورت رشته
            context: context برای template
            
        Returns:
            محتوای رندر شده
        """
        try:
            # ایجاد template از رشته
            template = self.env.from_string(template_string)
            
            # رندر template
            rendered = template.render(**context)
            
            return {
                'success': True,
                'content': rendered,
                'size': len(rendered),
                'message': 'String template rendered successfully'
            }
            
        except jinja2.TemplateSyntaxError as e:
            error_msg = f"Template syntax error in string template: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'line': e.lineno,
                'message': e.message
            }
        except Exception as e:
            error_msg = f"Error rendering string template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def validate_template(self, template_path: str) -> Dict:
        """
        اعتبارسنجی template
        
        Args:
            template_path: مسیر template
            
        Returns:
            نتیجه اعتبارسنجی
        """
        try:
            # بارگذاری template (این اعتبارسنجی syntax را انجام می‌دهد)
            template = self.env.get_template(template_path)
            
            # بررسی متغیرهای استفاده شده
            variables = list(template.undeclared_variables)
            
            return {
                'success': True,
                'template': template_path,
                'valid': True,
                'variables': variables,
                'variables_count': len(variables),
                'message': f"Template is valid, uses {len(variables)} variables"
            }
            
        except jinja2.TemplateSyntaxError as e:
            error_msg = f"Template syntax error in {template_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'template': template_path,
                'valid': False,
                'error': error_msg,
                'line': e.lineno,
                'message': e.message
            }
        except jinja2.TemplateNotFound as e:
            error_msg = f"Template not found: {template_path}"
            logger.error(error_msg)
            return {
                'success': False,
                'template': template_path,
                'valid': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Error validating template {template_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'template': template_path,
                'valid': False,
                'error': error_msg
            }
    
    def get_template_variables(self, template_path: str) -> Dict:
        """
        دریافت لیست متغیرهای مورد نیاز template
        
        Args:
            template_path: مسیر template
            
        Returns:
            لیست متغیرها
        """
        try:
            template = self.env.get_template(template_path)
            variables = list(template.undeclared_variables)
            
            return {
                'success': True,
                'template': template_path,
                'variables': variables,
                'variables_count': len(variables),
                'message': f"Template requires {len(variables)} variables"
            }
            
        except Exception as e:
            error_msg = f"Error getting template variables for {template_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'template': template_path,
                'error': error_msg
            }
    
    def compare_templates(self, template1_path: str, template2_path: str, 
                         context: Dict[str, Any] = None) -> Dict:
        """
        مقایسه دو template
        
        Args:
            template1_path: مسیر template اول
            template2_path: مسیر template دوم
            context: context برای رندر (اختیاری)
            
        Returns:
            نتیجه مقایسه
        """
        try:
            # رندر template اول
            result1 = self.render_template_string(template1_path, context or {})
            if not result1['success']:
                return result1
            
            # رندر template دوم
            result2 = self.render_template_string(template2_path, context or {})
            if not result2['success']:
                return result2
            
            content1 = result1['content']
            content2 = result2['content']
            
            # مقایسه
            are_equal = content1 == content2
            
            # اگر متفاوت هستند، diff را محاسبه کن
            diff = None
            if not are_equal:
                import difflib
                diff = list(difflib.unified_diff(
                    content1.splitlines(keepends=True),
                    content2.splitlines(keepends=True),
                    fromfile=template1_path,
                    tofile=template2_path,
                    lineterm='\n'
                ))
            
            result = {
                'success': True,
                'template1': template1_path,
                'template2': template2_path,
                'are_equal': are_equal,
                'size1': len(content1),
                'size2': len(content2),
                'size_diff': len(content1) - len(content2),
                'diff': diff,
                'message': 'Templates are identical' if are_equal else 'Templates are different'
            }
            
            logger.debug(f"Template comparison: {template1_path} vs {template2_path} - {'Equal' if are_equal else 'Different'}")
            return result
            
        except Exception as e:
            error_msg = f"Error comparing templates {template1_path} and {template2_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'template1': template1_path,
                'template2': template2_path
            }
    
    def batch_render_templates(self, templates: List[Dict], 
                              context: Dict[str, Any]) -> Dict:
        """
        رندر کردن دسته‌ای templateها
        
        Args:
            templates: لیست templateها
            context: context مشترک برای همه templateها
            
        Returns:
            نتایج رندر
        """
        try:
            results = []
            successful = 0
            failed = 0
            
            logger.info(f"Batch rendering {len(templates)} templates")
            
            for template_config in templates:
                template_path = template_config.get('template')
                output_path = template_config.get('output')
                template_context = template_config.get('context', {})
                
                # ترکیب contextها
                combined_context = {**context, **template_context}
                
                if output_path:
                    # رندر و ذخیره در فایل
                    result = self.render_template(
                        template_path=template_path,
                        output_path=output_path,
                        context=combined_context,
                        mode=template_config.get('mode'),
                        backup=template_config.get('backup', False),
                        force=template_config.get('force', True)
                    )
                else:
                    # فقط رندر به رشته
                    result = self.render_template_string(
                        template_path=template_path,
                        context=combined_context
                    )
                
                results.append({
                    'template': template_path,
                    'output': output_path,
                    'result': result
                })
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
            
            summary = {
                'success': failed == 0,
                'total_templates': len(templates),
                'successful': successful,
                'failed': failed,
                'results': results,
                'message': f"Batch render completed: {successful} successful, {failed} failed"
            }
            
            logger.info(f"Batch render completed: {summary['message']}")
            return summary
            
        except Exception as e:
            error_msg = f"Error in batch template rendering: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'total_templates': len(templates) if 'templates' in locals() else 0
            }
    
    def add_template_directory(self, directory: str) -> bool:
        """
        اضافه کردن دایرکتوری template
        
        Args:
            directory: مسیر دایرکتوری
            
        Returns:
            True اگر موفق باشد
        """
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                logger.warning(f"Template directory does not exist: {directory}")
                return False
            
            if not dir_path.is_dir():
                logger.warning(f"Template path is not a directory: {directory}")
                return False
            
            # اضافه کردن به loader
            if str(dir_path) not in self.template_dirs:
                self.template_dirs.append(str(dir_path))
                self.env.loader.searchpath.append(str(dir_path))
                logger.info(f"Template directory added: {directory}")
                return True
            else:
                logger.debug(f"Template directory already exists: {directory}")
                return False
            
        except Exception as e:
            logger.error(f"Error adding template directory {directory}: {str(e)}")
            return False
    
    def list_templates(self, directory: str = None, pattern: str = None) -> Dict:
        """
        لیست templateهای موجود
        
        Args:
            directory: دایرکتوری خاص (اگر None باشد همه)
            pattern: الگوی جستجو
            
        Returns:
            لیست templateها
        """
        try:
            templates = []
            
            if directory:
                # جستجو در دایرکتوری خاص
                dir_path = Path(directory)
                if pattern:
                    search_pattern = f"**/{pattern}"
                else:
                    search_pattern = "**/*"
                
                for template_file in dir_path.glob(search_pattern):
                    if template_file.is_file():
                        templates.append(str(template_file.relative_to(dir_path)))
            else:
                # جستجو در همه دایرکتوری‌های template
                for template_dir in self.template_dirs:
                    dir_path = Path(template_dir)
                    if dir_path.exists():
                        if pattern:
                            search_pattern = f"**/{pattern}"
                        else:
                            search_pattern = "**/*"
                        
                        for template_file in dir_path.glob(search_pattern):
                            if template_file.is_file():
                                # مسیر نسبی
                                rel_path = template_file.relative_to(dir_path)
                                templates.append(str(rel_path))
            
            # حذف duplicateها (اگر template در چند دایرکتوری وجود دارد)
            templates = list(set(templates))
            templates.sort()
            
            return {
                'success': True,
                'templates': templates,
                'total_templates': len(templates),
                'template_dirs': self.template_dirs,
                'pattern': pattern,
                'message': f"Found {len(templates)} templates"
            }
            
        except Exception as e:
            error_msg = f"Error listing templates: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'templates': []
            }


def create_template_renderer(config: Dict = None) -> TemplateRenderer:
    """
    تابع helper برای ایجاد Template Renderer
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از TemplateRenderer
    """
    return TemplateRenderer(config)