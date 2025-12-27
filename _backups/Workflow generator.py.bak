# -*- coding: utf-8 -*-
"""
【工作流样本生成器】基于 Event 生成端到端工作流 V1.0
功能：为每个 Event 生成包含 Target 创建的完整工作流样本

设计理念：
- AI 应该学习"先创建音频结构，再创建 Event"的完整工作流
- 由于大部分 Event 指向 Sound（未被单独提取），我们基于 Event 信息推导 Target 结构

使用方法：
    python workflow_generator.wwise_reverse_event_dataset.jsonl -o workflow.jsonl
"""

import json
import re
import argparse
import random
from typing import Dict, List, Optional, Tuple


class WorkflowGenerator:
    """工作流样本生成器"""
    
    def __init__(self):
        # 工作流 instruction 模板（丰富多样）
        self.workflow_instructions = {
            "changjing": [
                "帮我创建{name}的场景音效，需要完整的容器结构和播放Event",
                "搭建{name}的环境音效系统，从随机容器到触发事件全流程",
                "设计{name}场景氛围声，包含多变体Sound和Event",
            ],
            "skill": [
                "创建{name}技能音效的完整结构，包括音频层级和Event",
                "帮我做一套{name}技能的声音设计，要能通过Event播放",
                "搭建{name}技能音效系统，从Container到播放事件",
            ],
            "boss": [
                "设计{name}BOSS技能的音效工作流",
                "创建{name}的BOSS战斗音效，包含完整的播放链路",
            ],
            "ui": [
                "帮我做{name}界面音效，需要Event触发",
                "创建{name}UI反馈音效的完整结构",
            ],
            "footstep": [
                "设计{name}脚步声系统，支持多材质切换",
                "创建{name}行走音效，包含随机变体和Event",
            ],
            "default": [
                "帮我创建{name}的音效结构，包含容器层级和播放Event",
                "搭建{name}的Wwise音频系统，从音效资产到Event触发",
                "设计{name}的完整音效工作流",
                "创建{name}的声音设计，需要Container和对应的Event",
            ]
        }
        
        # Action 类型
        self.action_types = {
            "Play_": ("PLAY", "播放"),
            "Stop_": ("STOP", "停止"),
            "Pause_": ("PAUSE", "暂停"),
            "Resume_": ("RESUME", "恢复"),
            "Set_": ("PLAY", "设置"),  # 有些 Set_ 也是播放
        }
        
        # 场景识别
        self.scene_keywords = {
            "changjing": "changjing",
            "ambient": "changjing",
            "scene": "changjing",
            "skill": "skill",
            "cast": "skill",
            "attack": "skill",
            "boss": "boss",
            "elite": "boss",
            "ui": "ui",
            "menu": "ui",
            "button": "ui",
            "footstep": "footstep",
            "walk": "footstep",
            "run": "footstep",
        }
        
        # 常用的引用模板
        self.common_buses = [
            "HostPlayerSkill", "OtherPlayerSkill", "NPCSfx", 
            "AmbientSfx", "MusicBus", "UISfx", "Master"
        ]
        
        self.common_attenuations = [
            "skill_medium_2000", "skill_far_5000", "ambient_large",
            "npc_normal", "player_close"
        ]
    
    def identify_scene(self, name: str) -> str:
        """识别场景类型"""
        name_lower = name.lower()
        for keyword, scene in self.scene_keywords.items():
            if keyword in name_lower:
                return scene
        return "default"
    
    def extract_action_info(self, event_dsl: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """提取 Action 信息: (event_name, action_type, target_name)"""
        match = re.search(r'ADD_ACTION\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"', event_dsl)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None, None, None
    
    def infer_target_type(self, target_name: str) -> str:
        """推断 Target 类型"""
        name_lower = target_name.lower()
        
        # 根据命名推断
        if "_loop" in name_lower:
            return "RandomSequenceContainer"  # 循环音效通常是随机容器
        elif any(x in name_lower for x in ["_01", "_02", "_03"]):
            return "Sound"  # 带编号的通常是 Sound
        elif "random" in name_lower or "rand" in name_lower:
            return "RandomSequenceContainer"
        elif "switch" in name_lower:
            return "SwitchContainer"
        else:
            # 默认为随机容器（最常见）
            return "RandomSequenceContainer"
    
    def generate_target_dsl(self, target_name: str, target_type: str, 
                           parent: str = "Default Work Unit") -> List[str]:
        """生成 Target 的 DSL 代码"""
        lines = []
        
        # 1. 创建容器
        lines.append(f'CREATE {target_type} "{target_name}" UNDER "{parent}"')
        
        # 2. 根据类型添加属性和子对象
        if target_type == "RandomSequenceContainer":
            # 随机容器常见属性
            if random.random() > 0.5:
                lines.append(f'SET_PROP "{target_name}" "RandomAvoidRepeating" = True')
            
            # 添加 2-3 个子 Sound
            num_sounds = random.randint(2, 3)
            for i in range(1, num_sounds + 1):
                sound_name = f"{target_name}_{i:02d}"
                lines.append(f'CREATE Sound "{sound_name}" UNDER "{target_name}"')
        
        elif target_type == "SwitchContainer":
            # Switch 容器
            lines.append(f'SET_PROP "{target_name}" "SwitchBehavior" = 0')
        
        elif target_type == "Sound":
            # 单个 Sound，可能需要循环
            if "_loop" in target_name.lower():
                lines.append(f'SET_PROP "{target_name}" "IsLoopingEnabled" = True')
        
        # 3. 添加 LINK（随机选择）
        if random.random() > 0.3:
            bus = random.choice(self.common_buses)
            lines.append(f'LINK "{target_name}" TO "{bus}" AS "Bus"')
        
        if random.random() > 0.5:
            atten = random.choice(self.common_attenuations)
            lines.append(f'LINK "{target_name}" TO "{atten}" AS "Attenuation"')
        
        return lines
    
    def generate_workflow_instruction(self, target_name: str, scene_type: str) -> str:
        """生成工作流指令"""
        templates = self.workflow_instructions.get(scene_type, self.workflow_instructions["default"])
        template = random.choice(templates)
        
        # 清理名称用于显示
        display_name = target_name.replace("_", " ").replace("-", " ")
        
        return template.format(name=display_name)
    
    def generate_workflow_sample(self, event_sample: Dict) -> Optional[Dict]:
        """为单个 Event 生成完整的工作流样本"""
        event_dsl = event_sample['output']
        event_name = event_sample['meta']['root_name']
        
        # 提取 Action 信息
        _, action_type, target_name = self.extract_action_info(event_dsl)
        
        if not target_name:
            return None
        
        # 推断场景和 Target 类型
        scene_type = self.identify_scene(target_name)
        target_type = self.infer_target_type(target_name)
        
        # 生成 Target DSL
        target_lines = self.generate_target_dsl(target_name, target_type)
        
        # 组合完整 DSL
        full_dsl_lines = target_lines + ["", "# Event 触发"] + event_dsl.split("\n")
        full_dsl = "\n".join(full_dsl_lines)
        
        # 生成 instruction
        instruction = self.generate_workflow_instruction(target_name, scene_type)
        
        # 创建样本
        return {
            "instruction": instruction,
            "input": "",
            "output": full_dsl,
            "meta": {
                "source": event_sample['meta']['source'],
                "root_type": "Workflow",
                "root_name": event_name,
                "target_name": target_name,
                "target_type": target_type,
                "scene_type": scene_type,
                "line_count": len(full_dsl_lines),
                "depth": 1,
                "complexity": "medium",
                "workflow_type": "event_with_target",
                "commands": {
                    "CREATE": len([l for l in full_dsl_lines if l.startswith("CREATE")]),
                    "SET_PROP": len([l for l in full_dsl_lines if l.startswith("SET_PROP")]),
                    "LINK": len([l for l in full_dsl_lines if l.startswith("LINK")]),
                    "ASSIGN": 0,
                    "ADD_ACTION": 1
                }
            }
        }
    
    def process(self, event_samples: List[Dict]) -> List[Dict]:
        """处理所有 Event 样本"""
        workflow_samples = []
        
        for event_sample in event_samples:
            workflow = self.generate_workflow_sample(event_sample)
            if workflow:
                workflow_samples.append(workflow)
        
        return workflow_samples


def main():
    parser = argparse.ArgumentParser(description='工作流样本生成器')
    parser.add_argument('event_file', help='Event 数据集 (JSONL)')
    parser.add_argument('-o', '--output', default='workflow_generated.jsonl', help='输出文件')
    parser.add_argument('--sample', type=int, default=0, help='只处理前 N 个样本（调试用）')
    
    args = parser.parse_args()
    
    generator = WorkflowGenerator()
    
    print("=" * 60)
    print("🔄 Workflow Generator V1.0")
    print("=" * 60)
    
    # 加载数据
    print(f"📂 加载 Event 数据: {args.event_file}")
    event_samples = []
    with open(args.event_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                event_samples.append(json.loads(line))
    
    if args.sample > 0:
        event_samples = event_samples[:args.sample]
    
    print(f"   -> {len(event_samples)} 个 Event 样本")
    
    # 生成工作流
    print("-" * 60)
    print("🔧 生成工作流样本...")
    workflow_samples = generator.process(event_samples)
    
    print(f"✅ 生成完成: {len(workflow_samples)} 个工作流样本")
    
    # 统计
    scene_count = {}
    for s in workflow_samples:
        st = s['meta']['scene_type']
        scene_count[st] = scene_count.get(st, 0) + 1
    
    print("\n📊 场景类型分布:")
    for st, cnt in sorted(scene_count.items(), key=lambda x: -x[1]):
        print(f"   {st}: {cnt}")
    
    # 保存
    with open(args.output, 'w', encoding='utf-8') as f:
        for s in workflow_samples:
            f.write(json.dumps(s, ensure_ascii=False) + '\n')
    
    print("-" * 60)
    print(f"💾 已保存: {args.output}")
    
    # 显示示例
    if workflow_samples:
        print("\n📋 示例工作流样本:")
        sample = random.choice(workflow_samples)
        print(f"Instruction: {sample['instruction']}")
        print(f"DSL:\n{sample['output']}")


if __name__ == "__main__":
    main()