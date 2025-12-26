import unicodedata
import os

def analyze_file_issues(file_path):
    print(f"正在对文件进行显微镜级检查: {file_path}")
    print("-" * 60)
    
    if not os.path.exists(file_path):
        print("❌ 文件不存在！请检查路径。")
        return

    issues_found = 0
    line_number = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                for i, char in enumerate(line):
                    # 跳过标准 ASCII 可打印字符 (英文、数字、标点)
                    if 0x20 <= ord(char) <= 0x7E:
                        continue
                    
                    # 跳过标准换行符
                    if char in ['\n', '\r', '\t']:
                        continue

                    # 跳过常用的 CJK 汉字范围 (基本区)
                    if 0x4E00 <= ord(char) <= 0x9FFF:
                        continue
                        
                    # --- 开始捕捉可疑字符 ---
                    
                    # 获取字符的详细信息
                    code_point = f"U+{ord(char):04X}"
                    try:
                        name = unicodedata.name(char)
                    except ValueError:
                        name = "<UNKNOWN NAME>"
                    
                    category = unicodedata.category(char)
                    
                    # 判定是否为"高风险"字符
                    # 1. 控制字符 (Cc, Cf) - 比如零宽空格
                    # 2. 全角符号 (VS Code 经常报警 Ambiguous)
                    # 3. 各种看起来像空格但不是空格的符号
                    
                    risk_level = "INFO"
                    risk_reason = "非标准字符"
                    
                    if category.startswith('C'): # 控制字符
                        risk_level = "CRITICAL"
                        risk_reason = "不可见/控制字符 (VS Code 警告源)"
                    elif 0xFF00 <= ord(char) <= 0xFFEF: # 全角字符
                        risk_level = "WARNING"
                        risk_reason = "全角字符 (可能被判定为 Ambiguous)"
                    elif char == '\u3000':
                        risk_level = "WARNING"
                        risk_reason = "全角空格 (容易导致格式错误)"
                    
                    # 打印报告
                    print(f"[行 {line_number}, 列 {i+1}] [{risk_level}]")
                    print(f"  字符: '{char}' (如果不可见则为空)")
                    print(f"  编码: {code_point}")
                    print(f"  名称: {name}")
                    print(f"  原因: {risk_reason}")
                    print("-" * 30)
                    
                    issues_found += 1
                    
                    # 为了防止刷屏,如果发现太多问题,暂停一下
                    if issues_found >= 20:
                        print("... (已发现超过 20 个可疑点,停止输出以免刷屏) ...")
                        print("建议:文件确实包含大量非标准字符,请检查以上报告的字符类型。")
                        return

    except UnicodeDecodeError:
        print("❌ 致命错误:文件甚至不是有效的 UTF-8 编码！这本身就是最大的问题。")
        return

    if issues_found == 0:
        print("✅ 检查通过！未发现明显的 Unicode 风险字符。")
        print("如果 VS Code 依然报错,可能是 VS Code 的 'Ambiguous Characters' 设置过于敏感,")
        print("或者它把正常的中文标点(如全角逗号)也误判了。")
    else:
        print(f"检查结束。共发现 {issues_found} 个潜在风险点。")

# 运行诊断
# 请将文件名替换为您当前生成的有问题的文件名
target_file = "wwise_character_action_refined.jsonl" 
analyze_file_issues(target_file)