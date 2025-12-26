import os
import unicodedata

def clean_line(text):
    """
    深度清洗每一行数据,确保兼容性:
    1. NFKC 标准化:将全角字符、歧义符号、某些同形异义词转换为标准半角/规范形式。
    2. 剔除所有不可见控制字符(保留换行符和缩进)。
    3. 处理 VS Code 容易报错的 Unicode 歧义字符。
    """
    if not text:
        return ""
    
    # 第一步:执行 NFKC 标准化 (Compatibility Decomposition, followed by Canonical Composition)
    # 这能解决很多"看起来像 A 其实是 B"的 Unicode 歧义问题
    text = unicodedata.normalize('NFKC', text)
    
    # 第二步:过滤不可见字符
    # 只保留可打印字符、换行符(\n)和制表符(\t)
    # isprintable() 会自动识别并排除 \u200b (零宽空格) 等不可见字符
    text = "".join(ch for ch in text if ch.isprintable() or ch in '\n\r\t')
    
    # 第三步:处理特定的潜在歧义引号或符号(如果 NFKC 没处理掉的话)
    # 在 JSON 中,标准的双引号是 " (\u0022),如果混入了奇怪的引号,这里可以手动纠正
    # 但通常 NFKC 已经处理了大部分情况
    
    return text.strip() + "\n"

def merge_jsonl_files(file1_path, file2_path, output_path):
    """
    合并并深度清洗两个 JSONL 文件
    """
    if not os.path.exists(file1_path) or not os.path.exists(file2_path):
        print("错误:源文件路径无效,请检查文件名。")
        return

    print(f"正在启动深度清洗合并引擎 (使用 NFKC 标准化)...")

    try:
        count = 0
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for source in [file1_path, file2_path]:
                with open(source, 'r', encoding='utf-8') as infile:
                    for line in infile:
                        cleaned = clean_line(line)
                        if cleaned.strip(): 
                            outfile.write(cleaned)
                            count += 1
        
        absolute_output_path = os.path.abspath(output_path)
        print("------------------------------------------------------------------")
        print(f"✅ 深度清理合并完成！共处理 {count} 行数据。")
        print(f"💡 采用了 NFKC 标准化逻辑,VS Code 的 Unicode 歧义提示应已消除。")
        print(f"文件位置: {absolute_output_path}")
        print("------------------------------------------------------------------")

    except Exception as e:
        print(f"合并过程中发生错误: {e}")

# ============== 配置 ==============
file_one = "wwise_training_with_instructions.jsonl" 
file_two = "11.jsonl" 
output_file = "combined_wwise_data_v1.jsonl"

merge_jsonl_files(file_one, file_two, output_file)