import json
import re
import random

# ==========================================
# 资深音频设计师 - 动态话术库 (V3.0)
# ==========================================

# 1. 演出语境映射 (New)
CONTEXT_MAP = {
    "MVP": ["MVP结算", "全场最佳展示", "胜者结算动画"],
    "CG": ["过场动画", "剧情演出", "Cutscene"],
    "FB": ["副本演出", "Boss战流程", "关卡动画"],
    "World": ["大世界", "野外Boss演出"]
}

# 2. 动画阶段映射 (New)
PHASE_MAP = {
    "JieSuan": ["结算阶段", "最后定格", "分数统计"],
    "ChuChang": ["登场表演", "入场动画", "亮相瞬间"],
    "TuiChang": ["退场动画", "死亡/击败演出", "消失阶段"],
    "ZhuanChang": ["转场过渡", "阶段切换"],
    "ZhanDou": ["战斗循环", "交战状态"],
    "Montage": ["蒙太奇展示", "高光剪辑"]
}

# 3. 角色/体型/题材映射 (New)
THEME_MAP = {
    "ChengNan": "成男体型",
    "ChengNv": "成女体型",
    "LuoLi": "萝莉体型",
    "XiaoTong": "正太/小童体型",
    "JiuSeLu": "[九色鹿]主题",
    "LiBai": "[李白]主题",
    "BiYao": "[碧瑶]主题",
    "GuiLi": "[鬼厉]主题",
    "ZengShuShu": "[曾书书]主题",
    "LuXueQi": "[陆雪琪]主题",
    "JinWu": "[金乌]主题",
    "NeZha": "[哪吒]主题",
    "RuiHe": "[瑞鹤]主题",
    "WuShe": "[舞狮/舞蛇]主题",
    "ZhongBuQiao": "[钟不敲/特定时装]",
    "ZiTengHua": "[紫藤花]主题"
}

# 4. 设计意图库 (针对线性与UI)
INTENTS = {
    "Cinematic": [
        "配合镜头运动,强调画面的冲击力。",
        "作为线性动画的音频轨道,需严格对齐画面。",
        "提升演出的沉浸感,细节要丰富。"
    ],
    "Music": [
        "这是配乐层,负责烘托整体情绪。",
        "注意与画面的情绪起伏保持同步。",
        "作为BGM,动态范围控制要得当。"
    ],
    "UI_Feedback": [
        "增强界面的交互反馈感。",
        "给玩家明确的结算爽感。",
        "短促有力,强调结果展示。"
    ],
    "Generic": [
        "标准音频资源配置。",
        "按需配置,保证基础听感。"
    ]
}

# 5. 技术执行话术
TECH_PHRASES = {
    "routing_sfx": ["路由至音效总线 `{bus}`。", "发送给 `{bus}` SFX层。", "走 `{bus}` 通道。"],
    "routing_music": ["路由至音乐总线 `{bus}`。", "作为BGM发送给 `{bus}`。", "归类到 `{bus}` 音乐层。"],
    "override_out": [
        "**注意**:勾选 'Override Output',切断父级继承,单独指定路由。",
        "开启 Output 重写,因为这里的路由逻辑比较特殊。",
        "强制指定输出总线,不受父级控制。"
    ],
    "color_mark": [
        "标个 Color {c} 方便分类。",
        "设置颜色为 {c},保持工程整洁。",
        "Color 设为 {c}。"
    ]
}

def analyze_name(obj_name):
    """解析名字中的元数据"""
    name_lower = obj_name.lower()
    
    # 提取语境
    context = "通用资源"
    for k, v_list in CONTEXT_MAP.items():
        if k.lower() in name_lower:
            context = random.choice(v_list)
            break
            
    # 提取阶段
    phase = ""
    for k, v_list in PHASE_MAP.items():
        if k.lower() in name_lower:
            phase = random.choice(v_list)
            break
            
    # 提取题材
    theme = ""
    for k, v in THEME_MAP.items():
        if k.lower() in name_lower:
            theme = v
            break
            
    return context, phase, theme

def analyze_commands(output_commands):
    """解析 Wwise 命令块"""
    lines = output_commands.split('\n')
    root_cmd = lines[0]
    
    match = re.search(r'CREATE (\w+) "([^"]+)" UNDER "([^"]+)"', root_cmd)
    if not match: return None
    
    obj_type, obj_name, parent_name = match.groups()
    
    bus_match = re.search(r'LINK ".*" TO "([^"]+)" AS "OutputBus"', output_commands)
    target_bus = bus_match.group(1) if bus_match else "Master Audio Bus"
    
    att_match = re.search(r'LINK ".*" TO "([^"]+)" AS "Attenuation"', output_commands)
    attenuation = att_match.group(1) if att_match else None
    
    # 提取 Override 属性
    props = {}
    prop_matches = re.findall(r'SET_PROP "[^"]+" "([^"]+)" = (.+)', output_commands)
    for p_name, p_val in prop_matches:
        props[p_name] = p_val
        
    return {
        "type": obj_type, "name": obj_name, "parent": parent_name,
        "bus": target_bus, "attenuation": attenuation,
        "props": props
    }

def generate_natural_language(data):
    """生成 V3.0 指令"""
    info = analyze_commands(data.get("output", ""))
    if not info: return "无法解析指令。"
    
    obj_name = info['name']
    asset_ref = f"`{obj_name}`"
    
    # 1. 语义分析
    context_txt, phase_txt, theme_txt = analyze_name(obj_name)
    
    # 组合描述词
    desc_parts = []
    if theme_txt: desc_parts.append(theme_txt)
    if context_txt: desc_parts.append(context_txt)
    if phase_txt: desc_parts.append(phase_txt)
    full_desc = " ".join(desc_parts) if desc_parts else "通用游戏资产"
    
    # 2. 意图判定
    is_music = "Mus" in obj_name or "BGM" in info['bus']
    if is_music:
        intent = random.choice(INTENTS["Music"])
        tech_route = random.choice(TECH_PHRASES["routing_music"]).format(bus=info['bus'])
    elif "MVP" in obj_name or "JieSuan" in obj_name:
        intent = random.choice(INTENTS["UI_Feedback"] + INTENTS["Cinematic"])
        tech_route = random.choice(TECH_PHRASES["routing_sfx"]).format(bus=info['bus'])
    else:
        intent = random.choice(INTENTS["Cinematic"])
        tech_route = random.choice(TECH_PHRASES["routing_sfx"]).format(bus=info['bus'])

    # 3. 技术步骤构建
    tech_actions = []
    tech_actions.append(f"在 `{info['parent']}` 下创建 `{info['type']}`。")
    
    # Override 处理
    if info['props'].get("OverrideOutput") == "True":
        override_msg = random.choice(TECH_PHRASES["override_out"])
        tech_actions.append(f"{override_msg} {tech_route}")
    else:
        tech_actions.append(tech_route)
        
    if info['attenuation']:
        tech_actions.append(f"挂载衰减曲线 `{info['attenuation']}`。")
        
    if "Color" in info['props']:
        tech_actions.append(random.choice(TECH_PHRASES["color_mark"]).format(c=info['props']['Color']))

    # 4. 随机模板生成
    templates = [
        # 模板 A: 任务导向
        f"任务:制作 {full_desc} ({asset_ref})。\n设计意图:{intent}\n执行步骤:{' '.join(tech_actions)}",
        
        # 模板 B: 制作人语气
        f"处理一下 {asset_ref},这是{full_desc}的内容。\n要点:{intent}\n技术上:\n- " + "\n- ".join(tech_actions),
        
        # 模板 C: 简报风格
        f"[配置]{full_desc}\n资源ID:{asset_ref}\n参数配置:{' '.join(tech_actions)} (目标是{intent})"
    ]
    
    return random.choice(templates)

def main():
    input_file = "wwise_training_data_v7.jsonl"
    output_file = "wwise_training_v7_instruct_v3.jsonl"
    
    print(f"开始处理 V7 数据 (V3.0 演出/MVP模式)...")
    processed_count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        with open(input_file, 'r', encoding='utf-8') as infile:
            for line in infile:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    data["instruction"] = generate_natural_language(data)
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    processed_count += 1
                except json.JSONDecodeError: continue
                    
    print(f"完成！已生成 {processed_count} 条演出级指令。")

if __name__ == "__main__":
    main()