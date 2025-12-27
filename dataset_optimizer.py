# -*- coding: utf-8 -*-
"""
【数据集优化器】V1.0
功能：
1. 自动降采样过多的 GameParameter
2. 生成真正的 Event+Target 工作流样本（Container + Event 一体）
3. 平衡数据集各类型占比

使用方法：
    python dataset_optimizer.py combined_wwise_data_v1.jsonl -o optimized_dataset.jsonl
"""

import json
import random
import argparse
from collections import Counter
from typing import List, Dict

# =============================================================================
# 目标占比配置
# =============================================================================

# 理想的数据类型占比
TARGET_RATIOS = {
    "RandomSequenceContainer": 0.20,  # 20%
    "SwitchContainer": 0.15,          # 15%
    "BlendContainer": 0.03,           # 3%
    "ActorMixer": 0.03,               # 3%
    "Event": 0.25,                    # 25% (含工作流)
    "Attenuation": 0.08,              # 8%
    "GameParameter": 0.10,            # 10% ← 从30%降到10%
    "SwitchGroup": 0.08,              # 8%
    "StateGroup": 0.08,               # 8%
}

# 可生成工作流的容器类型
WORKFLOW_CONTAINER_TYPES = [
    "RandomSequenceContainer",
    "SwitchContainer", 
    "BlendContainer",
]

# =============================================================================
# 工作流生成器
# =============================================================================

class WorkflowGenerator:
    """生成 Event+Target 完整工作流样本"""
    
    # Instruction 模板
    WORKFLOW_TEMPLATES = [
        "创建 {name} 的完整音效结构，并生成对应的播放 Event",
        "帮我搭建 {name}，包含音效层级和触发事件",
        "做 {name} 的 SFX 结构和播放 Event",
        "创建 {name} 相关的音效和 Event，要能在游戏中播放",
        "构建 {name} 的完整工作流：先建结构，再建事件",
        "生成 {name} 的音效层级，并创建 Play Event",
        "搭建 {name}，需要包含容器结构和对应的触发 Event",
        "做一套 {name} 的完整音效，包括层级和播放事件",
    ]
    
    # Event 父级选项
    EVENT_PARENTS = ["Default Work Unit", "SFX", "Skills", "Combat", "Player", "Monster"]
    
    @classmethod
    def generate_workflow_sample(cls, container_sample: Dict) -> Dict:
        """
        从 Container 样本生成工作流样本
        
        将 Container 的 DSL 代码 + Event 创建合并为一个完整工作流
        """
        root_name = container_sample.get("meta", {}).get("root_name", "Unknown")
        root_type = container_sample.get("meta", {}).get("root_type", "")
        original_output = container_sample.get("output", "")
        
        # 生成 Event 部分
        event_parent = random.choice(cls.EVENT_PARENTS)
        event_name = f"Play_{root_name}"
        
        event_dsl = f'\nCREATE Event "{event_name}" UNDER "{event_parent}"\n'
        event_dsl += f'ADD_ACTION "{event_name}" PLAY "{root_name}"'
        
        # 合并 DSL
        combined_output = original_output + "\n" + event_dsl
        
        # 生成新的 instruction
        instruction = random.choice(cls.WORKFLOW_TEMPLATES).format(name=root_name)
        
        # 统计命令
        commands = {
            "CREATE": combined_output.count("CREATE"),
            "SET_PROP": combined_output.count("SET_PROP"),
            "LINK": combined_output.count("LINK"),
            "ASSIGN": combined_output.count("ASSIGN"),
            "ADD_ACTION": combined_output.count("ADD_ACTION"),
        }
        
        # 构建新样本
        workflow_sample = {
            "instruction": instruction,
            "input": "",
            "output": combined_output,
            "meta": {
                "source": "workflow_generated",
                "root_type": "Workflow",  # 标记为工作流类型
                "root_name": root_name,
                "line_count": combined_output.count("\n") + 1,
                "depth": container_sample.get("meta", {}).get("depth", 1) + 1,
                "complexity": "medium",
                "commands": commands,
                "container_type": root_type,
                "event_name": event_name,
            }
        }
        
        return workflow_sample


# =============================================================================
# 数据集优化器
# =============================================================================

class DatasetOptimizer:
    """数据集优化器"""
    
    def __init__(self, samples: List[Dict], seed: int = 42):
        self.samples = samples
        self.seed = seed
        random.seed(seed)
    
    def analyze(self):
        """分析当前数据集"""
        type_counter = Counter()
        for s in self.samples:
            root_type = s.get("meta", {}).get("root_type", "Unknown")
            type_counter[root_type] += 1
        
        print("=" * 60)
        print("📊 当前数据集分布")
        print("=" * 60)
        
        total = len(self.samples)
        for t, count in type_counter.most_common():
            pct = count / total * 100
            print(f"   {t}: {count} ({pct:.1f}%)")
        
        return type_counter
    
    def downsample_type(self, type_name: str, target_ratio: float) -> List[Dict]:
        """
        降采样指定类型到目标占比
        """
        # 分离目标类型和其他类型
        target_samples = []
        other_samples = []
        
        for s in self.samples:
            if s.get("meta", {}).get("root_type") == type_name:
                target_samples.append(s)
            else:
                other_samples.append(s)
        
        current_count = len(target_samples)
        other_count = len(other_samples)
        
        # 计算目标数量
        # target_ratio = target_count / (target_count + other_count)
        # target_count = target_ratio * other_count / (1 - target_ratio)
        target_count = int(target_ratio * other_count / (1 - target_ratio))
        target_count = min(target_count, current_count)  # 不能超过当前数量
        
        print(f"\n🔧 降采样 {type_name}:")
        print(f"   当前: {current_count}")
        print(f"   目标: {target_count}")
        print(f"   删除: {current_count - target_count}")
        
        # 随机采样
        if target_count < current_count:
            target_samples = random.sample(target_samples, target_count)
        
        return other_samples + target_samples
    
    def generate_workflows(self, ratio: float = 0.3) -> List[Dict]:
        """
        为部分 Container 样本生成工作流版本
        
        Args:
            ratio: 生成工作流的比例（默认 30% 的 Container 会有工作流版本）
        """
        workflow_samples = []
        container_count = 0
        
        for s in self.samples:
            root_type = s.get("meta", {}).get("root_type", "")
            
            if root_type not in WORKFLOW_CONTAINER_TYPES:
                continue
            
            container_count += 1
            
            # 按比例生成
            if random.random() > ratio:
                continue
            
            # 检查原始 output 长度，太长的不生成工作流
            original_lines = s.get("meta", {}).get("line_count", 0)
            if original_lines > 60:  # 超过60行的不生成，避免太长
                continue
            
            workflow = WorkflowGenerator.generate_workflow_sample(s)
            workflow_samples.append(workflow)
        
        print(f"\n🔧 生成 Event+Target 工作流:")
        print(f"   可用 Container: {container_count}")
        print(f"   生成工作流: {len(workflow_samples)}")
        
        return workflow_samples
    
    def optimize(
        self,
        downsample_gameparam: bool = True,
        generate_workflows: bool = True,
        workflow_ratio: float = 0.3,
    ) -> List[Dict]:
        """
        执行完整优化
        """
        print("\n" + "=" * 60)
        print("🚀 开始数据集优化")
        print("=" * 60)
        
        optimized = self.samples.copy()
        
        # 1. 降采样 GameParameter
        if downsample_gameparam:
            optimized = self.downsample_type("GameParameter", TARGET_RATIOS["GameParameter"])
            self.samples = optimized  # 更新引用
        
        # 2. 生成工作流样本
        workflows = []
        if generate_workflows:
            workflows = self.generate_workflows(ratio=workflow_ratio)
        
        # 3. 合并
        final = optimized + workflows
        
        # 4. 打乱
        random.shuffle(final)
        
        # 5. 最终统计
        print("\n" + "=" * 60)
        print("📊 优化后数据集分布")
        print("=" * 60)
        
        type_counter = Counter()
        for s in final:
            root_type = s.get("meta", {}).get("root_type", "Unknown")
            type_counter[root_type] += 1
        
        total = len(final)
        for t, count in type_counter.most_common():
            pct = count / total * 100
            # 标记改善
            if t == "GameParameter":
                status = "✅ 已优化" if pct < 15 else "⚠️"
            elif t == "Workflow":
                status = "✅ 新增"
            else:
                status = ""
            print(f"   {t}: {count} ({pct:.1f}%) {status}")
        
        print(f"\n   总计: {total}")
        
        return final


# =============================================================================
# 主函数
# =============================================================================

def load_jsonl(path: str) -> List[Dict]:
    """加载 JSONL 文件"""
    samples = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def save_jsonl(samples: List[Dict], path: str):
    """保存 JSONL 文件"""
    with open(path, 'w', encoding='utf-8') as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description="数据集优化器")
    parser.add_argument("input", type=str, help="输入 JSONL 文件")
    parser.add_argument("-o", "--output", type=str, help="输出文件路径")
    parser.add_argument("--no-downsample", action="store_true", 
                        help="不降采样 GameParameter")
    parser.add_argument("--no-workflow", action="store_true",
                        help="不生成工作流样本")
    parser.add_argument("--workflow-ratio", type=float, default=0.3,
                        help="工作流生成比例 (默认 0.3)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎮 Wwise 数据集优化器 V1.0")
    print("=" * 60)
    
    # 加载
    print(f"\n📂 加载: {args.input}")
    samples = load_jsonl(args.input)
    print(f"   样本数: {len(samples)}")
    
    # 分析
    optimizer = DatasetOptimizer(samples, seed=args.seed)
    optimizer.analyze()
    
    # 优化
    optimized = optimizer.optimize(
        downsample_gameparam=not args.no_downsample,
        generate_workflows=not args.no_workflow,
        workflow_ratio=args.workflow_ratio,
    )
    
    # 保存
    if args.output:
        output_path = args.output
    else:
        import os
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_optimized{ext}"
    
    save_jsonl(optimized, output_path)
    print(f"\n✅ 已保存: {output_path}")
    
    # 输出工作流示例
    workflow_samples = [s for s in optimized if s.get("meta", {}).get("root_type") == "Workflow"]
    if workflow_samples:
        print("\n" + "=" * 60)
        print("📝 工作流样本示例")
        print("=" * 60)
        example = workflow_samples[0]
        print(f"\nInstruction: {example['instruction']}")
        print(f"\nOutput (前30行):")
        lines = example['output'].split('\n')[:30]
        for line in lines:
            print(f"  {line}")
        if len(example['output'].split('\n')) > 30:
            print("  ...")


if __name__ == "__main__":
    main()
