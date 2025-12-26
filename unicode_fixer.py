# -*- coding: utf-8 -*-
"""
【工具脚本】Unicode 隐形字符与全角符号修复器 (V1.1)
功能：
1. 扫描当前目录下所有代码和数据文件 (.py, .json, .jsonl, .dsl, .md)。
2. 自动检测并修复“全角符号”、“零宽空格”、“非断行空格”等隐形杀手。
3. 会自动为修改过的文件创建备份，统一存放在 _backups 目录下，保持原有目录结构。
"""
import os
import shutil

# =============================================================================
# 配置项
# =============================================================================
BACKUP_DIR_NAME = "_backups"  # 统一备份目录名称

# =============================================================================
# 替换规则表 (Bad -> Good)
# =============================================================================
REPLACEMENT_MAP = {
    # 1. 隐形字符 / 空白符
    '\u200b': '',    # Zero Width Space (零宽空格) - 绝对的杀手
    '\ufeff': '',    # BOM (Byte Order Mark) - 有时会影响开头解析
    '\u3000': ' ',   # Ideographic Space (全角空格) -> 标准空格
    '\xa0': ' ',     # Non-breaking Space (NBSP) -> 标准空格
    
    # 2. 标点符号 (全角 -> 半角)
    # 注意：这里只替换会导致代码语法错误的符号。
    # 仅仅用于注释的中文标点通常保留，但为了防止 DSL 解析错误，建议统一。
    '：': ':',       # Full-width Colon
    '；': ';',       # Full-width Semicolon
    '，': ',',       # Full-width Comma
    '（': '(',       # Full-width Parenthesis Left
    '）': ')',       # Full-width Parenthesis Right
    '“': '"',        # Left Double Quote
    '”': '"',        # Right Double Quote
    '‘': "'",        # Left Single Quote
    '’': "'",        # Right Single Quote
    '【': '[',       # 这是一个激进的选择，视情况而定，但在 DSL 中 [ ] 常用于列表
    '】': ']', 
}

# 需要扫描的文件后缀
TARGET_EXTENSIONS = {'.py', '.json', '.jsonl', '.dsl', '.md', '.txt'}

def fix_file(filepath, root_dir):
    """读取文件，执行替换，如果发生变化则保存，并将备份存入统一目录"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except UnicodeDecodeError:
        print(f"⚠️ 跳过二进制或非 UTF-8 文件: {filepath}")
        return

    new_content = original_content
    changes_made = []

    for bad_char, good_char in REPLACEMENT_MAP.items():
        if bad_char in new_content:
            count = new_content.count(bad_char)
            new_content = new_content.replace(bad_char, good_char)
            
            # 记录日志
            char_display = bad_char
            if bad_char == '\u200b': char_display = "[零宽空格]"
            elif bad_char == '\u3000': char_display = "[全角空格]"
            elif bad_char == '\xa0': char_display = "[NBSP空格]"
            
            changes_made.append(f"  - 替换了 {count} 个 '{char_display}' -> '{good_char}'")

    if changes_made:
        # 1. 计算统一备份路径 (保持原有目录结构)
        # 例如: D:\Project\src\app.py -> D:\Project\_backups\src\app.py.bak
        rel_path = os.path.relpath(filepath, root_dir)
        backup_path = os.path.join(root_dir, BACKUP_DIR_NAME, rel_path + ".bak")
        
        # 确保备份目录存在
        backup_dir = os.path.dirname(backup_path)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        shutil.copy2(filepath, backup_path)
        
        # 2. 写入新内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 已修复: {rel_path}")
        for change in changes_made:
            print(change)
        print(f"  (已备份至 {BACKUP_DIR_NAME}{os.sep}{rel_path}.bak)")
    else:
        # print(f"✨ 无需修复: {os.path.basename(filepath)}")
        pass

def main():
    print("="*60)
    print("🧹 Unicode & 全角符号修复工具 V1.1")
    print("="*60)
    
    current_dir = os.getcwd()
    print(f"正在扫描目录: {current_dir}")
    print(f"备份目录: {os.path.join(current_dir, BACKUP_DIR_NAME)}\n")
    
    count = 0
    for root, dirs, files in os.walk(current_dir):
        # 排除 .git, __pycache__, .idea, 以及备份目录本身
        if '.git' in dirs: dirs.remove('.git')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        if '.streamlit' in dirs: dirs.remove('.streamlit')
        if BACKUP_DIR_NAME in dirs: dirs.remove(BACKUP_DIR_NAME)
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in TARGET_EXTENSIONS:
                # 排除脚本自己和备份文件(.bak)
                if file == "unicode_fixer.py" or file.endswith(".bak"):
                    continue
                    
                filepath = os.path.join(root, file)
                fix_file(filepath, current_dir)
                count += 1
                
    print("\n" + "="*60)
    print("🎉 扫描完成！")

if __name__ == "__main__":
    main()