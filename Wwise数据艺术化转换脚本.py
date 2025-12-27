import json
import random
import re
from typing import Dict, List, Optional

# ==========================================
# 配置区域
# ==========================================
INPUT_FILE = 'optimized_dataset_processed_processed.jsonl'
OUTPUT_FILE = 'artistic_design_dataset.jsonl'

# ==========================================
# 行业黑话与仙侠结合映射 (Industry Slang + Xianxia Lore)
# ==========================================
SEMANTIC_MAPPINGS = {
    # --- 门派 (Classes) ---
    "fenxiang": ["焚香谷", "火法", "Fx"],
    "guiwang": ["鬼王", "大T", "重坦"],
    "qingyun": ["青云", "雷剑", "Qy"],
    "tianyin": ["天音", "和尚", "奶爸"],
    "hehuan": ["合欢", "刺客", "Hh"],
    "lingxi": ["灵汐", "水奶", "辅助"],
    
    # --- 元素 (Elements) - 口语化描述 ---
    "huo": ["火元素炸裂的感觉", "灼烧感", "火系大招那味儿", "烈火燎原的压迫感"],
    "bing": ["冰晶破碎", "这种冷冽的质感", "寒气逼人", "清脆的冰冻反馈"],
    "lei": ["高频的雷电滋滋声", "雷霆万钧的轰鸣", "电光火石的瞬态", "麻痹感"],
    "feng": ["那种撕裂的风声", "气流快速流动的Whoosh", "空灵的风"],
    "tu": ["厚重的石头撞击", "低频要足的岩石感", "崩山裂地"],
    "du": ["那种粘稠的毒液声", "腐蚀的Foley", "令人不适的嘶嘶声"],
    "fazhen": ["法阵启动的翁鸣", "能量场共鸣", "这种玄幻的Layer"],
    "shui": ["水流的包裹感", "润泽的听感", "清澈的Liquid质感"],
    
    # --- 动作与反馈 (Action) ---
    "atk": ["普攻打击感", "拳拳到肉", "Attack瞬态要快"],
    "hit": ["受击反馈", "被打痛的感觉", "Fleshy的肉感"],
    "cast": ["施法前摇", "蓄力那种张力", "能量积蓄的过程"],
    "skill": ["技能释放", "大招", "关键技能"],
    "step": ["脚步", "Footstep", "踩在地上的质感"],
    
    # --- 场景与系统 (Context) ---
    "boss": ["Boss战P2阶段", "高压战斗环境", "Boss出场"],
    "cg": ["过场动画里", "这段Timeline", "剧情演出"],
    "ui": ["UI点击", "界面反馈", "交互音效"],
    "sidechain": ["侧链避让", "压一下伴奏", "把人声凸出来"],
    "rtpc": ["挂个RTPC", "参数控制", "动态变化"],
    "switch": ["切状态", "Switch组", "逻辑判断"]
}

# --- 2025 音频策划常用形容词/口头禅 ---
VIBE_KEYWORDS = [
    "听感要润", "打击感拉满", "要有史诗感", "细节要丰富", 
    "别太干", "高频别太刺", "要有颗粒感", "沉浸感要强", 
    "炸裂一点", "稍微收一点", "要有空间感", "仙气飘飘的"
]

class WwiseDataRefiner:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.data = self._load_data()

    def _load_data(self):
        data = []
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
        except FileNotFoundError:
            return []
        return data

    def _detect_category(self, code: str) -> str:
        if "Switch" in code: return "Logic"
        if "RTPC" in code or "GameParameter" in code: return "Mixing"
        if "RandomSequenceContainer" in code: return "Container"
        if "Bus" in code: return "Routing"
        if "BlendContainer" in code: return "Layering"
        return "General"

    def _analyze_object_name(self, code: str) -> dict:
        match = re.search(r'(?:CREATE \w+|SET_PROP|LINK) "([^"]+)"', code)
        raw_name = match.group(1) if match else "Unknown"
        lower_name = raw_name.lower()
        
        found_descriptors = []
        for key, choices in SEMANTIC_MAPPINGS.items():
            if key in lower_name:
                # 随机选一个同义词,增加多样性
                found_descriptors.append(random.choice(choices))
        
        # 兜底:如果啥都没匹配到,尝试拆字
        if not found_descriptors:
            parts = lower_name.split('_')
            for part in parts:
                if part in SEMANTIC_MAPPINGS:
                    found_descriptors.append(random.choice(SEMANTIC_MAPPINGS[part]))
                    
        return {"raw_name": raw_name, "descriptors": found_descriptors}

    # ==========================================
    # 核心:口语化与随机组合逻辑
    # ==========================================
    def get_colloquial_instruction(self, entry: Dict) -> str:
        original = entry['instruction']
        code = entry['output']
        category = self._detect_category(code)
        analysis = self._analyze_object_name(code)
        descs = analysis["descriptors"]
        
        # 1. 准备素材库 (Raw Ingredients)
        
        # [A] 场景/对象描述 (Context)
        context_opts = []
        if "boss" in code.lower():
            context_opts = ["现在是Boss战,", "处理Boss资源,", "面对那个魔尊的时候,"]
        elif "cg" in code.lower():
            context_opts = ["这段CG里,", "过场动画这块,", "Timeline上的这个点,"]
        elif "ui" in code.lower():
            context_opts = ["UI这块,", "菜单界面,", "点按钮的时候,"]
        elif descs:
            # 这里的 descs 已经是口语化的了,比如 "火元素炸裂的感觉"
            combined = "".join(descs[:2])
            context_opts = [f"做个{combined},", f"针对这个{combined},", f"具体到{combined}这块,"]
        else:
            context_opts = ["这个资源,", "这种情况下,", "现在的需求是,"]
            
        context = random.choice(context_opts)

        # [B] 听感要求 (Vibe)
        vibe = random.choice(VIBE_KEYWORDS)
        
        # [C] 技术实现 (Tech Spec) - 极其口语化
        tech = ""
        if category == "Logic":
            tech = random.choice([
                "建个Switch组切一下状态。", 
                "用Switch来管理这几种变体。",
                "逻辑上走Switch Group。",
                "记得用Switch Group把逻辑分清楚。"
            ])
        elif category == "Container":
            tech = random.choice([
                "套个Random Container防止听觉疲劳。",
                "弄个随机容器,别让声音太重复。",
                "Random Container走起,随机化搞一下。",
                "包在Random Container里,多给点变化。"
            ])
        elif category == "Mixing":
            tech = random.choice([
                "挂个RTPC控制动态。",
                "用RTPC修一下参数曲线。",
                "Game Parameter连一下,随游戏状态变。",
                "做个RTPC映射。"
            ])
        elif category == "Routing":
            tech = random.choice([
                "路由别乱,走到对应的Bus去。",
                "Bus层级整理好。",
                "把信号送进正确的Bus。"
            ])
        elif category == "Layering":
             tech = random.choice([
                "用Blend Container叠几层。",
                "做个混合容器(Blend Container)增加层次感。",
                "多Layer叠一下,用Blend Container。"
             ])
        else:
            tech = f"就把这个实现了:{original}"

        # 2. 随机组合模板 (Random Templates)
        # 这就是你想要的"模块语言不固定"
        
        templates = [
            # 模板1: 场景 -> 听感 -> 技术 (标准)
            f"{context}听感上{vibe}。具体实现上,{tech}",
            
            # 模板2: 技术 -> 场景 (倒装,极客风)
            f"{tech} 主要是针对{context},希望能{vibe}。",
            
            # 模板3: 需求痛点 -> 解决方案 (产品经理风)
            f"现在听着太干了,{vibe}。{context}你能不能{tech}",
            
            # 模板4: 直接下命令 (主程风)
            f"{context}{tech} 目标是{vibe}。",
            
            # 模板5: 询问式 (协作风)
            f"这边{context}我想{vibe},是不是应该{tech}",
            
            # 模板6: 简短有力 (Deadline风)
            f"{context}要{vibe}。{tech}",
        ]
        
        return random.choice(templates)

    def process(self):
        print("Processing with Random Colloquial Styles...")
        processed_data = []
        for entry in self.data:
            new_instr = self.get_colloquial_instruction(entry)
            processed_data.append({
                "instruction": new_instr,
                "input": entry["input"],
                "output": entry["output"]
            })
            
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for entry in processed_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"Done! Saved to {self.output_path}")

if __name__ == "__main__":
    converter = WwiseDataRefiner(INPUT_FILE, OUTPUT_FILE)
    if converter.data:
        converter.process()
        
        print("\n=== 随机口语样本预览 (Sample Preview) ===")
        # 随机抽样5个展示
        sample_indices = random.sample(range(len(converter.data)), min(5, len(converter.data)))
        for idx in sample_indices:
            data = json.loads(open(OUTPUT_FILE, 'r', encoding='utf-8').readlines()[idx])
            print(f"\n[指令]: {data['instruction']}")
            # print(f"[代码]: {data['output'][:40]}...")