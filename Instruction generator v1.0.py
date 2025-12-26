# -*- coding: utf-8 -*-
"""
[指令生成器]Instruction Generator V1.0
功能:为 DSL 训练数据生成专业的自然语言指令
模拟资深游戏音频设计师 / 制作人的口吻

特点:
1. 随机化表达方式,避免重复
2. 专业术语与口语化表达混合
3. 覆盖多种业务场景(技能、BOSS、小怪、动作等)
4. 支持中英文混合(行业习惯)

作者: NeuroWwise Team
版本: V1.0
"""

import json
import random
import re
import argparse
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# 随机词库 - 模拟真实的音频设计师表达习惯
# =============================================================================

class VocabularyBank:
    """词汇库 - 提供多样化的表达方式"""
    
    # =========================================================================
    # 角色/主体称呼
    # =========================================================================
    PLAYER_NAMES = [
        "玩家", "主角", "本地玩家", "主玩家", "Host玩家", "本机角色",
        "玩家角色", "主控角色", "操作角色", "我方角色"
    ]
    
    NPC_NAMES = [
        "NPC", "场景NPC", "非玩家角色", "环境NPC", "剧情NPC", "任务NPC"
    ]
    
    OTHER_PLAYER_NAMES = [
        "其他玩家", "联机玩家", "远程玩家", "队友", "其他角色", "网络玩家"
    ]
    
    MONSTER_NAMES = [
        "怪物", "小怪", "普通怪", "野怪", "杂兵", "敌人", "敌方单位"
    ]
    
    BOSS_NAMES = [
        "BOSS", "Boss", "首领", "大怪", "精英怪", "副本BOSS", "关底BOSS",
        "世界BOSS", "团队BOSS"
    ]
    
    # =========================================================================
    # 动作/行为描述
    # =========================================================================
    ACTION_VERBS = {
        "create": ["创建", "搭建", "构建", "制作", "建立", "设计", "配置"],
        "setup": ["搭建", "设置", "配置", "布置", "安排", "规划"],
        "implement": ["实现", "落地", "执行", "完成", "做出"],
        "add": ["添加", "加入", "放入", "补充", "新增"],
        "design": ["设计", "规划", "策划", "构思", "拟定"]
    }
    
    # =========================================================================
    # 音频专业术语
    # =========================================================================
    AUDIO_TERMS = {
        "sound": ["音效", "声音", "声效", "SFX", "音频"],
        "layer": ["层级", "层次", "结构", "架构", "体系"],
        "container": ["容器", "Container", "结构", "组织"],
        "mixer": ["混音器", "Mixer", "混音层", "音频混合器"],
        "bus": ["总线", "Bus", "输出总线", "音频总线"],
        "attenuation": ["衰减", "Attenuation", "距离衰减", "3D衰减"],
        "switch": ["切换", "Switch", "状态切换", "条件切换"],
        "random": ["随机", "Random", "随机播放", "随机容器"],
        "loop": ["循环", "Loop", "循环播放"],
        "conversion": ["转换设置", "Conversion", "音频转换"]
    }
    
    # =========================================================================
    # 业务场景描述
    # =========================================================================
    SKILL_CONTEXTS = [
        "技能音效", "战斗技能", "主动技能", "被动技能", "连招技能",
        "AOE技能", "范围技能", "单体技能", "位移技能", "控制技能",
        "爆发技能", "持续技能", "瞬发技能", "引导技能", "蓄力技能"
    ]
    
    BOSS_CONTEXTS = [
        "BOSS战技能", "BOSS机制", "BOSS大招", "BOSS AOE",
        "团队机制", "副本机制", "阶段技能", "狂暴技能", "终极技能"
    ]
    
    FOOTSTEP_CONTEXTS = [
        "脚步声", "移动音效", "行走声", "跑步声", "足音",
        "地面交互", "材质脚步", "环境脚步"
    ]
    
    MOUNT_CONTEXTS = [
        "坐骑音效", "骑乘音效", "载具声音", "飞行坐骑", "地面坐骑",
        "水上坐骑", "特殊坐骑"
    ]
    
    UI_CONTEXTS = [
        "UI音效", "界面音效", "系统提示", "操作反馈", "交互音效"
    ]
    
    # =========================================================================
    # 角色区分相关
    # =========================================================================
    CHARACTER_DIFF_FEATURES = [
        "主角和NPC的区分",
        "本地玩家和其他玩家的差异化处理",
        "不同角色类型的音效切换",
        "Host和Remote的音量差异",
        "自己和队友的声音区分",
        "玩家和场景NPC的分离控制"
    ]
    
    # =========================================================================
    # 3D音效相关
    # =========================================================================
    SPATIAL_FEATURES = [
        "3D空间定位",
        "距离衰减效果",
        "空间化处理",
        "定位音效",
        "环绕声支持",
        "距离感表现"
    ]
    
    # =========================================================================
    # 材质/环境相关
    # =========================================================================
    MATERIAL_FEATURES = [
        "不同材质的声音变化",
        "地面材质切换",
        "环境材质响应",
        "草地/石头/木头等材质区分",
        "雪地/水面等特殊材质"
    ]
    
    # =========================================================================
    # 随机播放相关
    # =========================================================================
    RANDOM_FEATURES = [
        "多变体随机播放",
        "避免重复的随机机制",
        "多音效轮播",
        "随机变化增加真实感"
    ]
    
    # =========================================================================
    # 循环相关
    # =========================================================================
    LOOP_FEATURES = [
        "无缝循环播放",
        "持续循环效果",
        "Loop音效支持",
        "循环底噪/氛围"
    ]


# =============================================================================
# 名称分析器 - 从对象名推断业务场景
# =============================================================================

class NameAnalyzer:
    """分析 Wwise 对象名称,推断业务场景"""
    
    # 关键词映射
    KEYWORD_PATTERNS = {
        # 技能相关
        "skill": ["Skill", "skill", "Attack", "attack", "Cast", "cast", 
                  "Impact", "impact", "Hit", "hit", "Damage", "damage"],
        
        # BOSS相关
        "boss": ["Boss", "BOSS", "boss", "Elite", "elite"],
        
        # 怪物相关
        "monster": ["Monster", "monster", "Mon_", "mon_", "Mob", "mob",
                    "Enemy", "enemy", "Creature", "creature"],
        
        # 玩家技能
        "player_skill": ["PlayerSkill", "Player_Skill", "PS_", "Skill_"],
        
        # 脚步声
        "footstep": ["Footstep", "footstep", "Foot", "foot", "Step", "step",
                     "Walk", "walk", "Run", "run", "fs_"],
        
        # 坐骑
        "mount": ["Mount", "mount", "Zuoqi", "zuoqi", "Horse", "horse",
                  "Ride", "ride", "Vehicle", "vehicle"],
        
        # UI
        "ui": ["UI", "ui", "Menu", "menu", "Button", "button", "Click", "click"],
        
        # 材质
        "material": ["grass", "Grass", "stone", "Stone", "wood", "Wood",
                     "water", "Water", "snow", "Snow", "metal", "Metal",
                     "sand", "Sand", "mud", "Mud", "dirt", "Dirt"],
        
        # 动作
        "action": ["Jump", "jump", "Climb", "climb", "Swim", "swim",
                   "Fly", "fly", "Land", "land", "Roll", "roll"],
        
        # 角色类型标识
        "character_type": ["_H", "_N", "_O", "_S", "_Host", "_NPC", "_Other"],
        
        # 循环
        "loop": ["Loop", "loop", "_loop", "_Loop"],
        
        # 随机
        "random": ["Random", "random", "-001", "-002", "-003", "_01", "_02"],
        
        # 职业相关 (从文件名推断)
        "class_gw": ["_GW", "GW_", "弓箭", "射击"],
        "class_qy": ["_QY", "QY_", "枪", "长枪"],
        "class_hh": ["_HH", "HH_", "双手", "重击"],
        "class_lx": ["_LX", "LX_", "灵"],
        "class_fx": ["_FX", "FX_", "法", "魔法"],
        "class_ty": ["_TY", "TY_", "通用"],
    }
    
    @classmethod
    def analyze(cls, name: str, source: str = "") -> Dict[str, bool]:
        """分析名称,返回特征标记"""
        features = {}
        combined = f"{name} {source}"
        
        for feature, keywords in cls.KEYWORD_PATTERNS.items():
            features[feature] = any(kw in combined for kw in keywords)
        
        return features
    
    @classmethod
    def get_context_type(cls, name: str, source: str = "") -> str:
        """获取主要业务场景类型"""
        features = cls.analyze(name, source)
        
        if features.get("boss"):
            return "boss"
        if features.get("player_skill") or "PlayerSkill" in source:
            return "player_skill"
        if features.get("monster"):
            return "monster"
        if features.get("footstep"):
            return "footstep"
        if features.get("mount"):
            return "mount"
        if features.get("ui"):
            return "ui"
        if features.get("action"):
            return "action"
        
        return "general"


# =============================================================================
# Instruction 生成器
# =============================================================================

class InstructionGenerator:
    """专业的 Instruction 生成器"""
    
    def __init__(self, style: str = "professional"):
        self.style = style
        self.vocab = VocabularyBank()
        self.analyzer = NameAnalyzer()
        
    def generate(self, dsl_output: str, meta: Dict) -> str:
        """生成 instruction"""
        root_name = meta.get("root_name", "")
        root_type = meta.get("root_type", "")
        source = meta.get("source", "")
        commands = meta.get("commands", {})
        depth = meta.get("depth", 0)
        
        context_type = self.analyzer.get_context_type(root_name, source)
        features = self.analyzer.analyze(root_name, source)
        
        if context_type == "boss":
            return self._generate_boss_instruction(root_name, features, commands, depth)
        elif context_type == "player_skill":
            return self._generate_player_skill_instruction(root_name, source, features, commands, depth)
        elif context_type == "monster":
            return self._generate_monster_instruction(root_name, features, commands, depth)
        elif context_type == "footstep":
            return self._generate_footstep_instruction(root_name, features, commands, depth)
        elif context_type == "mount":
            return self._generate_mount_instruction(root_name, features, commands, depth)
        elif context_type == "ui":
            return self._generate_ui_instruction(root_name, features, commands, depth)
        else:
            return self._generate_general_instruction(root_name, root_type, features, commands, depth)
    
    def _generate_player_skill_instruction(
        self, name: str, source: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成玩家技能相关的 instruction"""
        
        skill_name = self._extract_skill_name(name)
        player = random.choice(self.vocab.PLAYER_NAMES)
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        structure = random.choice([
            "音效层级结构", "声音架构", "SFX层级", "音频结构", 
            "Wwise结构", "音效系统", "声音层次"
        ])
        class_info = self._get_class_info(source)
        
        templates = [
            f"{action}{player}{skill_name}技能的{structure}",
            f"帮我{action}一套{player}使用{skill_name}时的{structure}",
            f"需要{action}{skill_name}这个技能的{structure},是{player}用的",
            f"{player}的{skill_name}技能,帮我{action}一下{structure}",
            f"给{player}{action}一个{skill_name}的{structure}",
            f"我要给{player}{action}{skill_name}技能的{structure}",
            f"{class_info}的{skill_name}技能,需要{action}{structure}",
            f"帮我把{player}的{skill_name}技能{structure}搭起来",
            f"{skill_name}这个技能的音效,帮{player}{action}一下",
            f"做一套{player}{skill_name}的{structure}",
            f"{action}一下{class_info}{skill_name}技能的声音层级",
            f"{player}释放{skill_name}时的音效,需要{action}结构"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_boss_instruction(
        self, name: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成 BOSS 相关的 instruction"""
        
        boss_name = self._extract_boss_name(name)
        boss_ref = random.choice(self.vocab.BOSS_NAMES)
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        
        templates = [
            f"{action}{boss_ref}「{boss_name}」的技能音效结构",
            f"帮我{action}副本{boss_ref}{boss_name}的声音层级",
            f"需要给{boss_name}这个{boss_ref}{action}音效架构",
            f"{boss_ref}战斗中{boss_name}的音效,帮我{action}一下",
            f"给{boss_name}{boss_ref}{action}一套完整的SFX结构",
            f"副本里{boss_name}{boss_ref}的技能音效,需要{action}",
            f"{action}一套{boss_name}的{boss_ref}战音效结构",
            f"团队副本{boss_ref}{boss_name}需要{action}音效层级",
            f"{boss_name}的{boss_ref}战,帮我{action}音效架构",
            f"这个{boss_ref}{boss_name}的技能音效要{action}"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_monster_instruction(
        self, name: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成小怪相关的 instruction"""
        
        monster_name = self._extract_monster_name(name)
        monster_ref = random.choice(self.vocab.MONSTER_NAMES)
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        
        templates = [
            f"{action}{monster_ref}「{monster_name}」的音效结构",
            f"帮我给{monster_name}这个{monster_ref}{action}声音层级",
            f"{monster_ref}{monster_name}的技能音效需要{action}",
            f"需要{action}一套{monster_name}{monster_ref}用的SFX架构",
            f"野外{monster_ref}{monster_name}的音效,帮我{action}",
            f"给场景{monster_ref}{monster_name}{action}音效层级",
            f"{monster_name}这个{monster_ref}的声音结构要{action}",
            f"做一套{monster_name}{monster_ref}的音效"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_footstep_instruction(
        self, name: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成脚步声相关的 instruction"""
        
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        player = random.choice(self.vocab.PLAYER_NAMES)
        has_material = features.get("material", False)
        
        if has_material:
            material_templates = [
                f"{action}一套支持多材质切换的脚步声系统",
                f"帮我{action}{player}在不同地面材质上的脚步音效结构",
                f"需要{action}能区分草地、石头、木头等材质的脚步声层级",
                f"{player}的脚步声要根据材质变化,帮我{action}这套结构",
                f"给{player}{action}一个带材质切换的Footstep系统",
                f"{action}多材质响应的脚步声架构,要区分不同地面",
                f"角色在不同地面走路的脚步声,需要{action}",
                f"做一套能切换材质的脚步声系统"
            ]
            instruction = random.choice(material_templates)
        else:
            basic_templates = [
                f"{action}{player}的脚步声音效结构",
                f"帮我{action}一套脚步声的层级架构",
                f"需要{action}角色移动的脚步音效",
                f"{player}行走/跑步的脚步声,帮我{action}",
                f"给角色{action}一套Footstep音效结构",
                f"做一套脚步声的音效层级",
                f"{player}的移动脚步声需要{action}"
            ]
            instruction = random.choice(basic_templates)
        
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_mount_instruction(
        self, name: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成坐骑相关的 instruction"""
        
        mount_name = self._extract_mount_name(name)
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        player = random.choice(self.vocab.PLAYER_NAMES)
        
        templates = [
            f"{action}{player}骑乘{mount_name}坐骑时的音效结构",
            f"帮我{action}坐骑{mount_name}的声音层级",
            f"{mount_name}坐骑的移动音效需要{action}",
            f"需要给{mount_name}坐骑{action}一套SFX架构",
            f"{player}的{mount_name}坐骑,帮我{action}音效结构",
            f"骑乘系统里{mount_name}的音效,需要{action}",
            f"做一套{mount_name}坐骑的音效",
            f"{mount_name}这个坐骑的声音层级要{action}"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_ui_instruction(
        self, name: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成 UI 相关的 instruction"""
        
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        
        templates = [
            f"{action}一套UI界面的音效结构",
            f"帮我{action}系统界面的声音层级",
            f"需要{action}菜单和按钮的音效架构",
            f"UI交互音效需要{action}一下结构",
            f"给界面操作{action}一套反馈音效",
            f"做一套UI操作的音效层级",
            f"系统界面的声音反馈需要{action}"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _generate_general_instruction(
        self, name: str, root_type: str, features: Dict, commands: Dict, depth: int
    ) -> str:
        """生成通用的 instruction"""
        
        action = random.choice(self.vocab.ACTION_VERBS["create"])
        
        type_desc = {
            "ActorMixer": "Actor-Mixer层级",
            "RandomSequenceContainer": "随机播放容器",
            "SwitchContainer": "条件切换容器",
            "BlendContainer": "混合容器"
        }.get(root_type, "音效结构")
        
        templates = [
            f"{action}一个{name}的{type_desc}",
            f"帮我{action}{name}相关的音效结构",
            f"需要{action}{name}用的Wwise层级",
            f"给{name}{action}一套{type_desc}",
            f"做一套{name}的音效架构",
            f"{name}的声音层级需要{action}"
        ]
        
        instruction = random.choice(templates)
        instruction += self._add_features(features, commands, depth)
        
        return instruction
    
    def _add_features(self, features: Dict, commands: Dict, depth: int) -> str:
        """根据特性添加额外描述"""
        
        extras = []
        
        if features.get("character_type"):
            extras.append(random.choice(self.vocab.CHARACTER_DIFF_FEATURES))
        
        if features.get("material"):
            extras.append(random.choice(self.vocab.MATERIAL_FEATURES))
        
        if features.get("random") or commands.get("CREATE", 0) > 5:
            extras.append(random.choice(self.vocab.RANDOM_FEATURES))
        
        if features.get("loop"):
            extras.append(random.choice(self.vocab.LOOP_FEATURES))
        
        if commands.get("LINK", 0) > 3 and random.random() > 0.5:
            extras.append(random.choice(self.vocab.SPATIAL_FEATURES))
        
        if depth >= 3 and random.random() > 0.6:
            extras.append(f"层级深度要到{depth}层")
        
        if extras:
            selected = random.sample(extras, min(len(extras), random.randint(1, 2)))
            connector = random.choice([",要支持", ",需要", ",包含", ",带上", ",加上"])
            return connector + "、".join(selected)
        
        return ""
    
    def _extract_skill_name(self, name: str) -> str:
        clean = name
        for prefix in ["PlayerSkill_", "Skill_", "PS_"]:
            clean = clean.replace(prefix, "")
        for suffix in ["_H", "_N", "_O", "_S", "_01", "_02"]:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
        return clean if clean else name
    
    def _extract_boss_name(self, name: str) -> str:
        clean = name
        for prefix in ["Boss_", "BOSS_", "boss_"]:
            clean = clean.replace(prefix, "")
        return clean if clean else name
    
    def _extract_monster_name(self, name: str) -> str:
        clean = name
        for prefix in ["Monster_", "Mon_", "mon_", "Mob_"]:
            clean = clean.replace(prefix, "")
        return clean if clean else name
    
    def _extract_mount_name(self, name: str) -> str:
        clean = name
        for prefix in ["Mount_", "Zuoqi_", "zuoqi_"]:
            clean = clean.replace(prefix, "")
        return clean if clean else name
    
    def _get_class_info(self, source: str) -> str:
        class_map = {
            "GW": random.choice(["弓箭手", "远程职业", "射手"]),
            "QY": random.choice(["枪系职业", "长枪手", "枪兵"]),
            "HH": random.choice(["重武器职业", "大剑师", "战士"]),
            "LX": random.choice(["灵系职业", "灵使"]),
            "FX": random.choice(["法系职业", "法师", "魔法师"]),
            "TY": random.choice(["通用技能", "公共技能", "基础技能"]),
            "Common": random.choice(["通用技能", "公共技能"]),
        }
        
        for key, value in class_map.items():
            if key in source:
                return value
        
        return "角色"


# =============================================================================
# 批量处理
# =============================================================================

def process_jsonl(
    input_path: str, 
    output_path: str,
    style: str = "professional"
) -> Tuple[int, int]:
    """处理 JSONL 文件,为每条记录生成 instruction"""
    
    generator = InstructionGenerator(style=style)
    success_count = 0
    fail_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                instruction = generator.generate(
                    dsl_output=data.get("output", ""),
                    meta=data.get("meta", {})
                )
                
                data["instruction"] = instruction
                
                f_out.write(json.dumps(data, ensure_ascii=False) + "\n")
                success_count += 1
                
                if success_count % 500 == 0:
                    print(f"   已处理 {success_count} 条...")
                    
            except Exception as e:
                print(f"   ⚠️ 第 {line_num} 行处理失败: {e}")
                fail_count += 1
    
    return success_count, fail_count


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="为 DSL 训练数据生成专业的自然语言指令"
    )
    
    parser.add_argument("input", help="输入 JSONL 文件路径")
    parser.add_argument("output", nargs="?", default=None, help="输出 JSONL 文件路径")
    parser.add_argument("--style", choices=["professional", "casual", "mixed"],
                        default="professional", help="生成风格")
    parser.add_argument("--preview", action="store_true", 
                        help="预览模式:只显示前10条生成结果")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        return
    
    if args.preview:
        print("=" * 70)
        print("📝 Instruction 生成预览")
        print("=" * 70)
        
        generator = InstructionGenerator(style=args.style)
        
        with open(args.input, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                
                data = json.loads(line)
                instruction = generator.generate(
                    dsl_output=data.get("output", ""),
                    meta=data.get("meta", {})
                )
                
                print(f"\n[样本 {i+1}]")
                print(f"  Root: {data.get('meta', {}).get('root_name', 'N/A')}")
                print(f"  Source: {data.get('meta', {}).get('source', 'N/A')}")
                print(f"  Instruction: {instruction}")
                print("-" * 70)
    else:
        if not args.output:
            args.output = args.input.replace(".jsonl", "_with_instructions.jsonl")
        
        print("=" * 70)
        print("🚀 Instruction Generator V1.0")
        print("=" * 70)
        print(f"   输入: {args.input}")
        print(f"   输出: {args.output}")
        print(f"   风格: {args.style}")
        print("-" * 70)
        
        success, fail = process_jsonl(args.input, args.output, args.style)
        
        print("-" * 70)
        print(f"✅ 处理完成!")
        print(f"   成功: {success}")
        print(f"   失败: {fail}")
        print(f"   输出: {args.output}")


if __name__ == "__main__":
    main()