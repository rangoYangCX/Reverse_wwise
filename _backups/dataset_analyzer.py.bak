# -*- coding: utf-8 -*-
"""
【数据集分析与预处理工具】V1.0
功能：
1. 分析数据集的样本分布（类型、长度、复杂度）
2. 检查是否包含各类数据（Audio/Event/参数）
3. 自动计算最佳 max_seq_length
4. 过滤或截断超长样本
5. 生成训练就绪的数据集

使用方法：
    python dataset_analyzer.py optimized_dataset_processed.jsonl
"""

import json
import argparse
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import os

# =============================================================================
# 数据集分析器
# =============================================================================

class DatasetAnalyzer:
    """数据集分析器"""
    
    def __init__(self, samples: List[Dict]):
        self.samples = samples
        self.stats = {}
    
    def analyze(self) -> Dict:
        """完整分析"""
        print("=" * 60)
        print("📊 数据集分析")
        print("=" * 60)
        
        # 基础统计
        self.stats["total_samples"] = len(self.samples)
        print(f"\n总样本数: {self.stats['total_samples']}")
        
        # 按类型统计
        self._analyze_by_type()
        
        # 按复杂度统计
        self._analyze_by_complexity()
        
        # 长度分析
        self._analyze_length()
        
        # 数据完整性检查
        self._check_data_coverage()
        
        # Token 估算
        self._estimate_tokens()
        
        return self.stats
    
    def _analyze_by_type(self):
        """按 root_type 分类统计"""
        type_counter = Counter()
        for s in self.samples:
            root_type = s.get("meta", {}).get("root_type", "Unknown")
            type_counter[root_type] += 1
        
        self.stats["by_type"] = dict(type_counter)
        
        print(f"\n📂 按类型分布:")
        for t, count in type_counter.most_common():
            pct = count / len(self.samples) * 100
            print(f"   {t}: {count} ({pct:.1f}%)")
    
    def _analyze_by_complexity(self):
        """按复杂度统计"""
        complexity_counter = Counter()
        for s in self.samples:
            complexity = s.get("meta", {}).get("complexity", "Unknown")
            complexity_counter[complexity] += 1
        
        self.stats["by_complexity"] = dict(complexity_counter)
        
        print(f"\n📈 按复杂度分布:")
        for c, count in complexity_counter.most_common():
            pct = count / len(self.samples) * 100
            print(f"   {c}: {count} ({pct:.1f}%)")
    
    def _analyze_length(self):
        """长度分析"""
        line_counts = []
        char_counts = []
        
        for s in self.samples:
            output = s.get("output", "")
            line_counts.append(s.get("meta", {}).get("line_count", output.count("\n") + 1))
            char_counts.append(len(output))
        
        self.stats["line_count"] = {
            "min": min(line_counts),
            "max": max(line_counts),
            "avg": sum(line_counts) / len(line_counts),
            "median": sorted(line_counts)[len(line_counts) // 2]
        }
        
        self.stats["char_count"] = {
            "min": min(char_counts),
            "max": max(char_counts),
            "avg": sum(char_counts) / len(char_counts),
            "median": sorted(char_counts)[len(char_counts) // 2]
        }
        
        # 长度分布
        length_buckets = {
            "1-30行": 0,
            "31-50行": 0,
            "51-100行": 0,
            "101-150行": 0,
            "151-200行": 0,
            "200+行": 0
        }
        
        for lc in line_counts:
            if lc <= 30:
                length_buckets["1-30行"] += 1
            elif lc <= 50:
                length_buckets["31-50行"] += 1
            elif lc <= 100:
                length_buckets["51-100行"] += 1
            elif lc <= 150:
                length_buckets["101-150行"] += 1
            elif lc <= 200:
                length_buckets["151-200行"] += 1
            else:
                length_buckets["200+行"] += 1
        
        self.stats["length_distribution"] = length_buckets
        
        print(f"\n📏 长度统计:")
        print(f"   行数: 最小={self.stats['line_count']['min']}, 最大={self.stats['line_count']['max']}, 平均={self.stats['line_count']['avg']:.1f}, 中位数={self.stats['line_count']['median']}")
        print(f"   字符: 最小={self.stats['char_count']['min']}, 最大={self.stats['char_count']['max']}, 平均={self.stats['char_count']['avg']:.0f}")
        
        print(f"\n📊 长度分布:")
        for bucket, count in length_buckets.items():
            pct = count / len(self.samples) * 100
            bar = "█" * int(pct / 2)
            print(f"   {bucket}: {count:5d} ({pct:5.1f}%) {bar}")
    
    def _check_data_coverage(self):
        """检查数据覆盖完整性"""
        coverage = {
            "has_audio": False,      # Container/Sound 层级
            "has_event": False,      # Event + ADD_ACTION
            "has_attenuation": False, # Attenuation 曲线
            "has_game_param": False,  # GameParameter
            "has_switch_group": False, # SwitchGroup
            "has_state_group": False,  # StateGroup
            "has_workflow": False,    # Event + Target 组合
        }
        
        for s in self.samples:
            root_type = s.get("meta", {}).get("root_type", "")
            output = s.get("output", "")
            
            if root_type in ["RandomSequenceContainer", "SwitchContainer", "BlendContainer", "ActorMixer"]:
                coverage["has_audio"] = True
            
            if root_type == "Event":
                coverage["has_event"] = True
                # 检查是否有完整工作流（Event + 包含 Container 创建）
                if "RandomSequenceContainer" in output or "SwitchContainer" in output:
                    coverage["has_workflow"] = True
            
            # 检查 Workflow 类型（由 dataset_optimizer 生成）
            if root_type == "Workflow":
                coverage["has_event"] = True
                coverage["has_workflow"] = True
            
            if root_type == "Attenuation":
                coverage["has_attenuation"] = True
            
            if root_type == "GameParameter":
                coverage["has_game_param"] = True
            
            if root_type == "SwitchGroup":
                coverage["has_switch_group"] = True
            
            if root_type == "StateGroup":
                coverage["has_state_group"] = True
        
        self.stats["coverage"] = coverage
        
        print(f"\n✅ 数据覆盖检查:")
        status = {True: "✓", False: "✗"}
        print(f"   {status[coverage['has_audio']]} Audio 层级 (Container/Sound)")
        print(f"   {status[coverage['has_event']]} Event 事件")
        print(f"   {status[coverage['has_attenuation']]} Attenuation 曲线")
        print(f"   {status[coverage['has_game_param']]} GameParameter 参数")
        print(f"   {status[coverage['has_switch_group']]} SwitchGroup 切换组")
        print(f"   {status[coverage['has_state_group']]} StateGroup 状态组")
        print(f"   {status[coverage['has_workflow']]} Event+Target 工作流")
    
    def _estimate_tokens(self):
        """估算 Token 数量"""
        # 粗略估算: 中文约 1.5 token/字符, 英文约 0.25 token/字符
        # DSL 代码主要是英文，估算 0.3 token/字符
        
        token_estimates = []
        for s in self.samples:
            instruction = s.get("instruction", "")
            output = s.get("output", "")
            
            # 完整 prompt 的字符数
            total_chars = len(instruction) + len(output) + 100  # 100 for system prompt overhead
            
            # 估算 tokens (DSL代码主要是英文关键词)
            estimated_tokens = int(total_chars * 0.35)
            token_estimates.append(estimated_tokens)
        
        self.stats["token_estimate"] = {
            "min": min(token_estimates),
            "max": max(token_estimates),
            "avg": sum(token_estimates) / len(token_estimates),
            "p90": sorted(token_estimates)[int(len(token_estimates) * 0.9)],
            "p95": sorted(token_estimates)[int(len(token_estimates) * 0.95)],
            "p99": sorted(token_estimates)[int(len(token_estimates) * 0.99)],
        }
        
        # 超长样本统计
        over_2048 = len([t for t in token_estimates if t > 2048])
        over_4096 = len([t for t in token_estimates if t > 4096])
        
        self.stats["overlength"] = {
            "over_2048": over_2048,
            "over_4096": over_4096,
        }
        
        print(f"\n🔢 Token 估算 (近似值):")
        print(f"   最小: {self.stats['token_estimate']['min']}")
        print(f"   最大: {self.stats['token_estimate']['max']}")
        print(f"   平均: {self.stats['token_estimate']['avg']:.0f}")
        print(f"   P90: {self.stats['token_estimate']['p90']}")
        print(f"   P95: {self.stats['token_estimate']['p95']}")
        print(f"   P99: {self.stats['token_estimate']['p99']}")
        
        print(f"\n⚠️ 超长样本:")
        print(f"   超过 2048 tokens: {over_2048} ({over_2048/len(self.samples)*100:.1f}%)")
        print(f"   超过 4096 tokens: {over_4096} ({over_4096/len(self.samples)*100:.1f}%)")
        
        # 推荐 max_seq_length
        if self.stats['token_estimate']['p95'] <= 2048:
            recommended = 2048
        elif self.stats['token_estimate']['p95'] <= 4096:
            recommended = 4096
        else:
            recommended = 8192
        
        self.stats["recommended_max_seq_length"] = recommended
        print(f"\n💡 推荐 max_seq_length: {recommended}")


# =============================================================================
# 数据集预处理器
# =============================================================================

class DatasetPreprocessor:
    """数据集预处理器"""
    
    def __init__(self, samples: List[Dict]):
        self.samples = samples
        self.processed = []
    
    def process(
        self,
        max_lines: int = 100,
        max_tokens: int = 2048,
        strategy: str = "truncate",  # truncate, filter, split
        keep_ratio: float = 0.95,     # 保留 95% 的样本
    ) -> List[Dict]:
        """
        预处理数据集
        
        Args:
            max_lines: 最大行数
            max_tokens: 最大 token 数（估算）
            strategy: 处理策略
                - truncate: 截断超长部分
                - filter: 过滤超长样本
                - split: 拆分超长样本（暂未实现）
            keep_ratio: 期望保留的样本比例
        """
        print("\n" + "=" * 60)
        print("🔧 数据集预处理")
        print("=" * 60)
        print(f"   策略: {strategy}")
        print(f"   最大行数: {max_lines}")
        print(f"   最大 tokens (估算): {max_tokens}")
        
        self.processed = []
        truncated_count = 0
        filtered_count = 0
        
        for s in self.samples:
            output = s.get("output", "")
            lines = output.split("\n")
            line_count = len(lines)
            
            # 估算 token 数
            total_chars = len(s.get("instruction", "")) + len(output) + 100
            estimated_tokens = int(total_chars * 0.35)
            
            # 判断是否超长
            is_overlength = line_count > max_lines or estimated_tokens > max_tokens
            
            if not is_overlength:
                # 正常样本直接添加
                self.processed.append(s)
            elif strategy == "filter":
                # 过滤策略：直接跳过
                filtered_count += 1
            elif strategy == "truncate":
                # 截断策略
                if line_count > max_lines:
                    # 保留前 max_lines 行
                    truncated_output = "\n".join(lines[:max_lines])
                    new_sample = s.copy()
                    new_sample["output"] = truncated_output
                    new_sample["meta"] = s.get("meta", {}).copy()
                    new_sample["meta"]["line_count"] = max_lines
                    new_sample["meta"]["truncated"] = True
                    new_sample["meta"]["original_line_count"] = line_count
                    self.processed.append(new_sample)
                    truncated_count += 1
                else:
                    self.processed.append(s)
        
        print(f"\n📊 处理结果:")
        print(f"   原始样本: {len(self.samples)}")
        print(f"   处理后: {len(self.processed)}")
        if strategy == "truncate":
            print(f"   截断样本: {truncated_count}")
        elif strategy == "filter":
            print(f"   过滤样本: {filtered_count}")
        
        actual_ratio = len(self.processed) / len(self.samples)
        print(f"   保留比例: {actual_ratio*100:.1f}%")
        
        return self.processed
    
    def balance_dataset(self, target_ratio: Dict[str, float] = None) -> List[Dict]:
        """
        平衡数据集（按类型）
        
        Args:
            target_ratio: 目标比例，如 {"audio": 0.5, "event": 0.2, ...}
        """
        if target_ratio is None:
            # 默认比例
            target_ratio = {
                "audio": 0.50,      # Container/Sound
                "event": 0.20,      # Event
                "attenuation": 0.12,
                "gameparam": 0.10,
                "switch_state": 0.08,
            }
        
        # 分类样本
        categorized = defaultdict(list)
        for s in self.processed:
            root_type = s.get("meta", {}).get("root_type", "")
            
            if root_type in ["RandomSequenceContainer", "SwitchContainer", "BlendContainer", "ActorMixer"]:
                categorized["audio"].append(s)
            elif root_type == "Event":
                categorized["event"].append(s)
            elif root_type == "Attenuation":
                categorized["attenuation"].append(s)
            elif root_type == "GameParameter":
                categorized["gameparam"].append(s)
            elif root_type in ["SwitchGroup", "StateGroup"]:
                categorized["switch_state"].append(s)
            else:
                categorized["other"].append(s)
        
        print(f"\n📊 当前分布:")
        for cat, samples in categorized.items():
            print(f"   {cat}: {len(samples)}")
        
        return self.processed
    
    def save(self, output_path: str):
        """保存处理后的数据集"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for s in self.processed:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
        
        print(f"\n✅ 已保存到: {output_path}")
        print(f"   样本数: {len(self.processed)}")


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


def main():
    parser = argparse.ArgumentParser(description="数据集分析与预处理工具")
    parser.add_argument("input", type=str, help="输入 JSONL 文件路径")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--max-lines", type=int, default=100, help="最大行数 (默认 100)")
    parser.add_argument("--max-tokens", type=int, default=2048, help="最大 tokens (默认 2048)")
    parser.add_argument("--strategy", type=str, default="truncate", 
                        choices=["truncate", "filter"], help="处理策略")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析，不处理")
    
    args = parser.parse_args()
    
    # 加载数据
    print(f"📂 加载数据集: {args.input}")
    samples = load_jsonl(args.input)
    
    # 分析
    analyzer = DatasetAnalyzer(samples)
    stats = analyzer.analyze()
    
    if args.analyze_only:
        print("\n✅ 分析完成 (仅分析模式)")
        return
    
    # 预处理
    preprocessor = DatasetPreprocessor(samples)
    processed = preprocessor.process(
        max_lines=args.max_lines,
        max_tokens=args.max_tokens,
        strategy=args.strategy
    )
    
    # 保存
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_processed{ext}"
    
    preprocessor.save(output_path)
    
    # 输出推荐配置
    print("\n" + "=" * 60)
    print("💡 推荐 Colab 训练配置")
    print("=" * 60)
    print(f"""
# 基于数据分析的推荐配置
MAX_SEQ_LENGTH = {stats['recommended_max_seq_length']}

# 数据集信息
DATASET_PATH = "{output_path}"
TOTAL_SAMPLES = {len(processed)}

# 训练参数 (根据样本量调整)
TRAINING_CONFIG = {{
    "num_epochs": 3,
    "learning_rate": 2e-4,
    "batch_size": 4,
    "gradient_accumulation": 4,
}}
""")


if __name__ == "__main__":
    main()
