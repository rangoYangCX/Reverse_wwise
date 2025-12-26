import json
import re
import random
import unicodedata

# ==========================================
# V9.0: 修复遗漏代码 + 全量翻译 + 核弹级清洗
# ==========================================

def clean_text(text):
    """
    核弹级清洗:将所有全角/中文标点强制转换为 ASCII 标点,
    并剔除所有非白名单字符。
    """
    if not text: return ""

    # 1. 强制全角转半角
    char_map = {
        '"': '"', '"': '"', ''': "'", ''': "'",
        ':': ':', '(': '(', ')': ')', ',': ',',
        ';': ';', ' ': ' ', '。': '.', 
        '、': ',', '？': '?', '！': '!',
        '[': '[', ']': ']' 
    }
    for k, v in char_map.items():
        text = text.replace(k, v)

    # 2. NFKC 标准化
    text = unicodedata.normalize('NFKC', text)

    # 3. 正则白名单 (保留 Tab, 换行, ASCII, 中文)
    pattern = re.compile(r'[^\u0009\u000A\u000D\u0020-\u007E\u4E00-\u9FFF]')
    text = pattern.sub('', text)
    
    return text.strip()

# --- 语境库 ---
CONTEXTS = {
    "MVP": [
        "针对 MVP 结算界面的听觉反馈,我们需要一段高品质的音频。",
        "这是玩家的高光时刻展示,请配置相应的结算音效。",
        "配合 MVP 动画演出的音频资源配置。",
        "处理一下MVP环节的声音,这块是面子工程,得做得细致点。",
        "结算界面这里缺个反馈,整一个对应的音频资产。"
    ],
    "Boss_Combat": [
        "针对 BOSS 战的核心战斗体验,请配置以下打击反馈资源。",
        "为了增强战斗的沉浸感,处理这组 BOSS 行为音效。",
        "这是 BOSS 战中的关键技能或动作音效。",
        "Boss战这块比较吃资源,这个音效是用来强调动作同步的。",
        "搞一下Boss这边的资源,要把压迫感做进工程结构里。"
    ],
    "Activity_3D": [
        "大世界运营活动场景的 3D 音效配置。",
        "为了营造节日或特定活动的现场氛围,请搭建这组资源。",
        "处理活动场景中的空间化音频资产。",
        "这块是运营活动的需求,注意空间感的那些参数设置。",
        "大世界的活动点位,需要配置一下这组声音。"
    ],
    "General": [
        "请根据设计文档,在 Wwise 工程中落实以下资产。",
        "执行以下音频资源的工程整合任务。",
        "标准音频资产配置任务。",
        "有个新资产需要进工程,麻烦处理下。",
        "按照规范把这个资源加进去。"
    ]
}

TASK_PHRASES = [
    "任务目标:构建资产 `{obj_name}`。",
    "当前的工单是制作 `{obj_name}`。",
    "麻烦落地一下这个资产:`{obj_name}`。",
    "需要创建一个新对象 `{obj_name}`。",
    "要把 `{obj_name}` 这个资源配进工程里。",
    "对象名称定为 `{obj_name}`,请创建。"
]

STRICT_PHRASES = [
    "请严格执行以下工程参数配置,确保无遗漏:",
    "技术参数卡死如下,严禁随意更改:",
    "按照下面这个清单配,参数必须1:1对应:",
    "注意,不要自由发挥,严格遵守以下属性设置:",
    "工程规范要求严格,请逐条执行以下配置:",
    "别动其他参数,只配置下面列出来的这些:"
]

# 扩展翻译表,涵盖更多属性
PROP_TRANSLATION = {
    "OverrideOutput": "开启 Output Override (路由重写)",
    "OverridePositioning": "开启 Positioning Override (定位重写)",
    "Color": "设置 Color 标签",
    "Volume": "设置 Volume (音量)",
    "Pitch": "设置 Pitch (音高)",
    "Lowpass": "设置 Low-pass Filter (低通滤波)",
    "Highpass": "设置 High-pass Filter (高通滤波)"
}

def get_context(obj_name, parent_name):
    name_check = (obj_name + parent_name).lower()
    if "mvp" in name_check or "jiesuan" in name_check:
        return random.choice(CONTEXTS["MVP"])
    elif "boss" in name_check or "monster" in name_check or "atk" in name_check:
        return random.choice(CONTEXTS["Boss_Combat"])
    elif "activity" in name_check or "national" in name_check:
        return random.choice(CONTEXTS["Activity_3D"])
    return random.choice(CONTEXTS["General"])

def extract_all_params(output_commands):
    """
    全量解析每一行命令,防止遗漏。
    """
    lines = output_commands.strip().split('\n')
    params = []
    
    # 用于记录主对象名
    main_obj_name = "Unknown"
    parent_obj_name = "Unknown"

    for line in lines:
        line = line.strip()
        if not line: continue

        # 1. CREATE 命令
        create_match = re.search(r'CREATE (\w+) "([^"]+)" UNDER "([^"]+)"', line)
        if create_match:
            obj_type, obj_name, parent_name = create_match.groups()
            params.append(f"在父级 `{parent_name}` 下创建 `{obj_name}` (类型: {obj_type})")
            if main_obj_name == "Unknown": # 记录第一个创建的对象为主对象
                main_obj_name = obj_name
                parent_obj_name = parent_name
            continue

        # 2. SET_PROP 命令
        prop_match = re.search(r'SET_PROP "([^"]+)" "([^"]+)" = (.+)', line)
        if prop_match:
            target, p_name, p_val = prop_match.groups()
            # 如果是常用属性,翻译之
            if p_name in PROP_TRANSLATION:
                desc = PROP_TRANSLATION[p_name]
                params.append(f"对象 `{target}`: {desc}: {p_val}")
            else:
                # 非常用属性,直接透传,防止遗漏
                params.append(f"对象 `{target}`: 设置属性 {p_name} 为 {p_val}")
            continue

        # 3. LINK 命令 (OutputBus)
        bus_match = re.search(r'LINK "([^"]+)" TO "([^"]+)" AS "OutputBus"', line)
        if bus_match:
            target, bus = bus_match.groups()
            params.append(f"对象 `{target}`: 路由至 Output Bus `{bus}`")
            continue

        # 4. LINK 命令 (Attenuation)
        att_match = re.search(r'LINK "([^"]+)" TO "([^"]+)" AS "Attenuation"', line)
        if att_match:
            target, att = att_match.groups()
            params.append(f"对象 `{target}`: 挂载 Attenuation `{att}`")
            continue

        # 5. LINK 命令 (SwitchGroup)
        sw_match = re.search(r'LINK "([^"]+)" TO "([^"]+)" AS "SwitchGroupOrStateGroup"', line)
        if sw_match:
            target, sw = sw_match.groups()
            params.append(f"对象 `{target}`: 关联 Switch Group `{sw}`")
            continue
            
        # 6. LINK 命令 (Conversion) - 之前可能漏了这个
        conv_match = re.search(r'LINK "([^"]+)" TO "([^"]+)" AS "Conversion"', line)
        if conv_match:
            target, conv = conv_match.groups()
            # Conversion 通常是默认的,但为了全量代码,我们也加上
            # 如果是 Default Conversion Settings,可以选择性忽略以精简,或者保留以严谨
            if "Default Conversion Settings" not in conv:
                 params.append(f"对象 `{target}`: 设置 Conversion `{conv}`")
            continue

        # 7. 未知命令兜底 (Fallback)
        # 如果有正则没匹配到的行,直接原文附上
        params.append(f"执行命令: {line}")

    return main_obj_name, parent_obj_name, params

def generate_instruction(data):
    # 1. 清洗输入数据
    cmd_data = clean_text(data.get("output", ""))
    
    result = extract_all_params(cmd_data)
    # result 结构: (obj_name, parent_name, param_list)
    
    obj_name, parent_name, param_list = result
    
    context_intro = get_context(obj_name, parent_name)
    task_intro = random.choice(TASK_PHRASES).format(obj_name=obj_name)
    strict_warning = random.choice(STRICT_PHRASES)
    
    tech_block = "\n".join([f"- {item}" for item in param_list])
    
    # 2. 组合文本
    prompt = (
        f"{context_intro}\n"
        f"{task_intro}\n"
        f"{strict_warning}\n"
        f"{tech_block}"
    )
    
    # 3. 最终清洗
    return clean_text(prompt)

def main():
    input_file = "wwise_training_data_v7.jsonl"
    output_file = "wwise_training_v7_final_v9.jsonl"
    
    print(f"开始处理 V9.0 数据 (全量代码解析)...")
    processed_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in infile:
                line = clean_text(line)
                if not line: continue
                
                try:
                    data = json.loads(line)
                    data["instruction"] = generate_instruction(data)
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    processed_count += 1
                except json.JSONDecodeError: continue
                    
    print(f"处理完成! 生成 {processed_count} 条全量数据.")
    print(f"输出文件: {output_file}")

if __name__ == "__main__":
    main()