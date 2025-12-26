import json
import re
import random
import unicodedata

# ==============================================================================
# 🎭 资深音频设计师 - 动态话术库 (Character Action 专用)
# ==============================================================================
# 这里的 Key 对应 analyze_code() 解析出的 intent (意图)

DESIGNER_PHRASES = {
    # --- 1. 脚步系统 (Footsteps) ---
    "footstep_system_setup": [
        "搭建一套标准的主角脚步声逻辑，根节点叫 {name}，记得把定位(Positioning)覆盖打开。",
        "给主角整一套脚步声架构 {name}，挂在 {parent} 下面。衰减要设好，走 OutputBus 路由。",
        "初始化主角的脚步系统 {name}。技术要求：开启 OverridePositioning，并关联到材质 Switch Group。",
        "我们需要一个基于 Switch 的脚步声系统 {name}，父级是 {parent}。逻辑要清晰，方便后面加材质。"
    ],
    "footstep_material_switch": [
        "现在处理 {material} 材质的脚步声逻辑。在 {parent} 下建个 SwitchContainer 叫 {name}。",
        "新增一种地表材质：{material}。创建对应的容器 {name}，别忘了把 Switch Group 连上。",
        "策划加了个 {material} 地形，我们需要对应的脚步声容器 {name}，挂在 {parent} 下。",
        "配置 {material} 材质的 Switch 逻辑，容器命名为 {name}，信号走 HostPlayerSkill 总线。"
    ],
    "footstep_sfx_assets": [
        "导入一批 {material} 的脚步声素材 {name}，要那种{adjective}的感觉。",
        "填充 {parent} 容器的内容，创建一组随机脚步声 {name}。听感要{adjective}一点。",
        "把美术给的 {material} 脚步声 {name} 导进去，放到 {parent} 下面，做成 Random 容器。",
        "增加 {name} 作为 {material} 的脚步声采样。注意样本的多样性。"
    ],

    # --- 2. 动作与受击 (Impacts & Foley) ---
    "land_impact": [
        "角色落地的音效 {name}，要根据地面材质做 Switch 切换。如果是石头，要厚重一点。",
        "处理跳跃落地的反馈 {name}。逻辑是：侦测材质 -> 播放对应的 Random Container。",
        "加一个落地缓冲的声音 {name}，父级是 {parent}。高处掉落时要有重音。",
        "实现 Land Impact 逻辑 {name}，挂载到 Material Switch Group 上。"
    ],
    "foley_layer": [
        "现在的动作太干了，加一层衣服摩擦声(Foley) {name}，音量设小一点({vol})。",
        "给动作加点细节，创建 {name} 作为 Foley 层。要体现出皮甲/布料的质感。",
        "在 {parent} 下叠一层 Foley {name}，让动作听起来更真实。衰减跟主脚步声一致。",
        "增加衣物摆动的随机层 {name}，丰富听觉细节。"
    ],
    "body_fall": [
        "角色死亡倒地的声音 {name}，要那种沉重的肉体撞击感。",
        "制作 Body Fall 音效 {name}。如果是 {material} 地面，要有对应的碰撞声。",
        "处理被击倒的音效 {name}，挂在 {parent} 下面。"
    ],

    # --- 3. 战斗与Buff (Combat & Buffs) ---
    "weapon_whoosh": [
        "武器挥舞的破空声(Whoosh) {name}，要轻快一点，加点随机 Pitch。",
        "给轻攻击配一个通用的挥舞声 {name}，不要带打击感，只要风声。",
        "创建 {name} 作为武器 Swing 音效。衰减距离设为 skill_small_1500。",
        "处理普攻的挥动层 {name}，随机化 Pitch ({pitch_range}) 以避免重复感。"
    ],
    "buff_feedback": [
        "做一个 Buff 激活的提示音 {name}。当获得 {buff_type} 状态时播放。",
        "处理 {buff_type} 的状态反馈音效 {name}。颜色标记设为 {color} 以便区分。",
        "UI 这种不明显的 Buff 需要一个 SFX {name} 来提示玩家。挂在 {parent} 下。",
        "创建 {name}，用于表现 {buff_type} 的持续/激活状态。"
    ],

    # --- 4. 通用/调试 (General/Debug) ---
    "volume_adjustment": [
        "这就太吵了，把 {name} 的音量压低到 {vol}。",
        "调整 {name} 的混合比例，Volume 设为 {vol}。",
        "平衡一下响度，{name} 需要衰减 {vol} dB。"
    ],
    "property_randomization": [
        "现在的声音太机械了，给 {name} 加点随机 {prop} 变化。",
        "优化听感：对 {name} 的 {prop} 属性做 Randomization 处理，范围 {range}。",
        "让 {name} 听起来自然点，随机化一下 {prop}。"
    ],
    "default": [
        "创建 {type} 对象 {name}，父级是 {parent}。",
        "在 {parent} 节点下新增 {name}。",
        "实现 {name} 的逻辑配置，类型为 {type}。"
    ]
}

# 形容词库，用于填充 {adjective}
ADJECTIVES = ["湿漉漉", "清脆", "厚重", "沉闷", "尖锐", "有弹性", "拖沓", "利落", "带金属感", "松软"]

# ==============================================================================
# 🧠 核心解析逻辑
# ==============================================================================

def clean_text(text):
    """
    核弹级清洗：将所有全角/中文标点强制转换为 ASCII 标点，
    并剔除所有非白名单字符。
    """
    if not text: return ""

    # 1. 强制全角转半角
    char_map = {
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '：': ':', '（': '(', '）': ')', '，': ',',
        '；': ';', '　': ' ', '。': '.', 
        '、': ',', '？': '?', '！': '!',
        '【': '[', '】': ']' 
    }
    for k, v in char_map.items():
        text = text.replace(k, v)

    # 2. NFKC 标准化
    text = unicodedata.normalize('NFKC', text)

    # 3. 正则白名单 (保留 Tab, 换行, ASCII, 中文)
    # 这一步能有效去除不可见的控制字符和奇怪的 unicode 符号
    pattern = re.compile(r'[^\u0009\u000A\u000D\u0020-\u007E\u4E00-\u9FFF]')
    text = pattern.sub('', text)

    return text.strip()

def analyze_wwise_code(code_str):
    """
    解析 Wwise DSL 代码，提取关键信息并推断意图。
    返回: (intent, params_dict)
    """
    lines = code_str.split('\n')
    first_line = lines[0]
    
    # 1. 提取基础信息 (Create X "Name" Under "Parent")
    # 正则匹配：CREATE (Type) "Name" UNDER "Parent"
    match = re.search(r'CREATE\s+(\w+)\s+"([^"]+)"\s+UNDER\s+"([^"]+)"', first_line)
    
    params = {}
    if match:
        obj_type, obj_name, parent_name = match.groups()
        params = {
            "type": obj_type,
            "name": obj_name,
            "parent": parent_name,
            "adjective": random.choice(ADJECTIVES)
        }
    else:
        # 可能是 SET_PROP 开头
        if "SET_PROP" in first_line:
             match_prop = re.search(r'SET_PROP\s+"([^"]+)"\s+"([^"]+)"\s+=\s+(.+)', first_line)
             if match_prop:
                 name, prop, val = match_prop.groups()
                 params = {"name": name, "prop": prop, "val": val, "type": "Property", "range": val}
                 if "Random" in val:
                     return "property_randomization", params
                 if prop == "Volume":
                     params["vol"] = val
                     return "volume_adjustment", params

    if not params:
        return "default", {"name": "Unknown", "type": "Unknown", "parent": "Unknown"}

    # 2. 意图推断 (Rule-based Intent Inference)
    
    name_lower = params["name"].lower()
    parent_lower = params.get("parent", "").lower()
    full_code = code_str.lower()

    # --- 脚步声逻辑 ---
    if "footstep" in name_lower or "footstep" in parent_lower:
        if params["type"] == "ActorMixer" or "overridepositioning" in full_code:
            return "footstep_system_setup", params
        if params["type"] == "SwitchContainer" or "switchgroup" in full_code:
            # 提取材质名
            for mat in ["grass", "water", "stone", "metal", "wood", "dirt", "swamp"]:
                if mat in name_lower:
                    params["material"] = mat
                    return "footstep_material_switch", params
            params["material"] = "某种"
            return "footstep_material_switch", params
        if params["type"] in ["Sound", "RandomSequenceContainer"]:
            for mat in ["grass", "water", "stone", "metal", "wood", "dirt", "swamp"]:
                if mat in name_lower:
                    params["material"] = mat
                    return "footstep_sfx_assets", params
            params["material"] = "通用"
            return "footstep_sfx_assets", params

    # --- 动作/Foley ---
    if "foley" in name_lower or "leather" in name_lower or "cloth" in name_lower:
        vol_match = re.search(r'Volume"\s+=\s+(-?\d+)', code_str)
        params["vol"] = vol_match.group(1) if vol_match else "-4"
        return "foley_layer", params
        
    if "land" in name_lower or "jump" in name_lower:
        return "land_impact", params
        
    if "bodyfall" in name_lower or "death" in name_lower:
        params["material"] = "硬地"
        return "body_fall", params

    # --- 战斗/Buff ---
    if "swing" in name_lower or "whoosh" in name_lower:
        params["pitch_range"] = "Random(-200, 200)"
        return "weapon_whoosh", params
        
    if "buff" in name_lower or "shield" in name_lower or "active" in name_lower:
        params["buff_type"] = name_lower.replace("_", " ").title()
        color_match = re.search(r'Color"\s+=\s+(\d+)', code_str)
        params["color"] = color_match.group(1) if color_match else "None"
        return "buff_feedback", params

    # 默认回退
    return "default", params

# ==============================================================================
# 🚀 主生成逻辑
# ==============================================================================

def generate_natural_instruction(code_str):
    """根据代码生成自然语言 Instruction"""
    intent, params = analyze_wwise_code(code_str)
    
    # 从对应的 Intent 列表中随机选一句
    templates = DESIGNER_PHRASES.get(intent, DESIGNER_PHRASES["default"])
    template = random.choice(templates)
    
    # 填充参数
    try:
        instruction = template.format(**params)
    except KeyError:
        # 如果参数缺失，回退到默认模板
        instruction = f"创建 {params.get('type')} 对象 {params.get('name')}，归属于 {params.get('parent')}。"
        
    # 关键修改：在这里强制应用清洗，确保生成的内容没有全角字符
    return clean_text(instruction), intent

def main():
    input_file = "wwise_training_data_v7.jsonl"
    output_file = "wwise_character_action_refined.jsonl"
    
    print(f"🎧 正在启动资深音频设计师模拟器...")
    print(f"📂 读取文件: {input_file}")
    
    count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # 增加 errors='ignore' 防止乱码导致的读取中断
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in infile:
                # 在读取第一步就执行清洗
                line = clean_text(line)
                if not line: continue
                
                try:
                    data = json.loads(line)
                    code_output = data.get("output", "")
                    
                    if not code_output: continue

                    # 核心魔法：生成新指令
                    new_instruction, intent = generate_natural_instruction(code_output)
                    
                    # 更新数据
                    data["instruction"] = new_instruction
                    
                    # 自动补全 input 字段 (上下文) - 同样应用清洗
                    input_text = f"工程上下文: {intent} | 对象: {data.get('meta', {}).get('root_type', 'Object')}"
                    data["input"] = clean_text(input_text)
                    
                    # 写入
                    outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                    count += 1
                    
                except json.JSONDecodeError:
                    continue
                    
    print(f"✅ 处理完成！已生成 {count} 条资深设计师指令。")
    print(f"💾 输出文件: {output_file}")

if __name__ == "__main__":
    main()