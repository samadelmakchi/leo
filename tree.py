import os
from pathlib import Path

def print_tree(start_path=".", prefix="", show_hidden=False, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = ['venv', '__pycache__', '.git']
    
    path = Path(start_path)
    
    # فهرست محتویات
    contents = list(path.iterdir())
    
    # فیلتر کردن محتوا
    filtered_contents = []
    for item in contents:
        # نادیده گرفتن فایل‌های مخفی
        if not show_hidden and item.name.startswith('.'):
            continue
        # نادیده گرفتن پوشه‌های مشخص شده
        if item.is_dir() and item.name in ignore_dirs:
            continue
        filtered_contents.append(item)
    
    # مرتب‌سازی
    filtered_contents.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    
    for i, item in enumerate(filtered_contents):
        is_last = i == len(filtered_contents) - 1
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            print(f"{prefix}{connector}📁 {item.name}/")
            extension = "    " if is_last else "│   "
            print_tree(item, prefix + extension, show_hidden, ignore_dirs)
        else:
            # بدون نمایش حجم
            print(f"{prefix}{connector}📄 {item.name}")

# استفاده
print_tree(".", show_hidden=False, ignore_dirs=['venv'])