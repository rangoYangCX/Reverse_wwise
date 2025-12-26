# -*- coding: utf-8 -*-
"""
【样本裂变器】DSL Sample Fission V1.0
功能：基于现有 DSL 样本进行合法裂变，扩充训练数据量

核心原则：
1. 参数值必须基于真实存在的值（从现有数据中提取）
2. 命名可以变化（组合、替换前后缀）
3. 结构可以简化或重组（但必须保持语法正确）
4. 不能凭空捏造不存在的参数值

裂变策略：
- Simple: 仅改名、微调数值
- Medium: 结构简化、子集提取
- Advanced: 组合拼接、参数交叉

作者: NeuroWwise Team
版本: V1.0
"""

import json
import random
import re
import argparse
import os
import copy
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field


# =============================================================================
# 参数池 - 从真实数据中提取
# =============================================================================

@dataclass
class ParameterPool:
    """参数池 - 存储所有合法的参数值"""
    
    # 引用目标（Bus, Attenuation, Conversion 等）
    buses: Set[str] = field(default_factory=set)
    attenuations: Set[str] = field(default_factory=set)
    conversions: Set[str] = field(default_factory=set)
    switch_groups: Set[str] = field(default_factory=set)
    state_groups: Set[str] = field(default_factory=set)
    
    # 属性值
    prop_values: Dict[str, Set] = field(default_factory=lambda: defaultdict(set))
    
    # 命名组件（用于生成新名称）
    name_prefixes: Set[str] = field(default_factory=set)
    name_suffixes: Set[str] = field(default_factory=set)
    name_middles: Set[str] = field(default_factory=set)
    
    # 对象类型
    object_types: Set[str] = field(default_factory=set)
    
    def extract_from_dsl(self, dsl_code: str):
        """从 DSL 代码中提取参数"""
        
        # 提取 LINK 目标
        link_pattern = r'LINK\s+"[^"]+"\s+TO\s+"([^"]+)"\s+AS\s+"(\w+)"'
        for match in re.finditer(link_pattern, dsl_code):
            target, link_type = match.groups()
            if link_type == "Bus":
                self.buses.add(target)
            elif link_type == "Attenuation":
                self.attenuations.add(target)
            elif link_type == "Conversion":
                self.conversions.add(target)
            elif link_type == "SwitchGroupOrStateGroup":
                self.switch_groups.add(target)
        
        # 提取 SET_PROP 值
        prop_pattern = r'SET_PROP\s+"[^"]+"\s+"(\w+)"\s*=\s*(.+)'
        for match in re.finditer(prop_pattern, dsl_code):
            prop_name, prop_value = match.groups()
            self.prop_values[prop_name].add(prop_value.strip())
        
        # 提取对象类型
        create_pattern = r'CREATE\s+(\w+)\s+"([^"]+)"'
        for match in re.finditer(create_pattern, dsl_code):
            obj_type, obj_name = match.groups()
            self.object_types.add(obj_type)
            
            # 分解名称
            self._decompose_name(obj_name)
    
    def _decompose_name(self, name: str):
        """分解名称为组件"""
        # 按下划线分割
        parts = name.split("_")
        
        if len(parts) >= 1:
            self.name_prefixes.add(parts[0])
        if len(parts) >= 2:
            self.name_suffixes.add(parts[-1])
        if len(parts) >= 3:
            for p in parts[1:-1]:
                self.name_middles.add(p)
        
        # 提取数字后缀
        num_match = re.search(r'(\d+)$', name)
        if num_match:
            self.name_suffixes.add(num_match.group(1))
    
    def get_random_bus(self) -> str:
        return random.choice(list(self.buses)) if self.buses else "Master"
    
    def get_random_attenuation(self) -> str:
        return random.choice(list(self.attenuations)) if self.attenuations else None
    
    def get_random_conversion(self) -> str:
        return random.choice(list(self.conversions)) if self.conversions else "Default Conversion Settings"
    
    def get_random_switch_group(self) -> str:
        return random.choice(list(self.switch_groups)) if self.switch_groups else None


# =============================================================================
# 名称变异器
# =============================================================================

class NameMutator:
    """名称变异器 - 生成合法的新名称"""
    
    # 常用游戏音效前缀
    PREFIXES = [
        "SFX", "Skill", "Attack", "Cast", "Impact", "Hit", "Effect",
        "Buff", "Debuff", "Aura", "Summon", "Spell", "Ability",
        "Action", "Move", "Idle", "Run", "Walk", "Jump", "Land",
        "Fire", "Ice", "Thunder", "Wind", "Earth", "Dark", "Light",
        "Slash", "Pierce", "Crush", "Magic", "Physical", "Range"
    ]
    
    # 常用动作后缀
    SUFFIXES = [
        "Start", "Loop", "End", "Cast", "Impact", "Charge", "Release",
        "Hit", "Miss", "Crit", "Block", "Dodge", "Parry",
        "01", "02", "03", "04", "05",
        "A", "B", "C", "H", "N", "O", "S",
        "Light", "Medium", "Heavy", "Small", "Large"
    ]
    
    # 中间部分
    MIDDLES = [
        "Fire", "Ice", "Thunder", "Poison", "Heal", "Shield",
        "Sword", "Bow", "Staff", "Axe", "Spear", "Dagger",
        "Dragon", "Phoenix", "Tiger", "Wolf", "Bear", "Eagle",
        "Normal", "Special", "Ultimate", "Basic", "Advanced"
    ]
    
    @classmethod
    def mutate(cls, original_name: str, pool: ParameterPool, mutation_level: float = 0.3) -> str:
        """
        变异名称
        
        Args:
            original_name: 原始名称
            pool: 参数池
            mutation_level: 变异程度 (0-1)
            
        Returns:
            变异后的名称
        """
        if random.random() > mutation_level:
            return original_name
        
        mutation_type = random.choice(["suffix", "prefix", "number", "swap", "combine"])
        
        if mutation_type == "suffix":
            # 替换后缀
            base = re.sub(r'_?\d+$', '', original_name)
            base = re.sub(r'_[A-Z]$', '', base)
            new_suffix = random.choice(cls.SUFFIXES)
            return f"{base}_{new_suffix}"
        
        elif mutation_type == "prefix":
            # 替换前缀
            parts = original_name.split("_")
            if len(parts) > 1:
                new_prefix = random.choice(list(pool.name_prefixes) or cls.PREFIXES)
                parts[0] = new_prefix
                return "_".join(parts)
            return original_name
        
        elif mutation_type == "number":
            # 变更数字
            if re.search(r'\d+', original_name):
                new_num = str(random.randint(1, 10)).zfill(2)
                return re.sub(r'\d+', new_num, original_name)
            else:
                return f"{original_name}_{random.randint(1, 5):02d}"
        
        elif mutation_type == "swap":
            # 从池中选择类似名称的组件
            parts = original_name.split("_")
            if len(parts) > 2 and pool.name_middles:
                idx = random.randint(1, len(parts) - 2)
                parts[idx] = random.choice(list(pool.name_middles))
                return "_".join(parts)
            return original_name
        
        elif mutation_type == "combine":
            # 组合
            if pool.name_prefixes and pool.name_suffixes:
                prefix = random.choice(list(pool.name_prefixes))
                suffix = random.choice(list(pool.name_suffixes))
                if pool.name_middles and random.random() > 0.5:
                    middle = random.choice(list(pool.name_middles))
                    return f"{prefix}_{middle}_{suffix}"
                return f"{prefix}_{suffix}"
            return original_name
        
        return original_name


# =============================================================================
# DSL 裂变器
# =============================================================================

class DSLFission:
    """DSL 样本裂变器"""
    
    def __init__(self, pool: ParameterPool):
        self.pool = pool
        self.name_mutator = NameMutator()
        
        # 裂变统计
        self.stats = {
            "name_mutations": 0,
            "structure_simplifications": 0,
            "parameter_swaps": 0,
            "subset_extractions": 0
        }
    
    def fission_simple(self, dsl_code: str, count: int = 3) -> List[str]:
        """
        简单裂变 - 仅改名和微调
        
        策略：
        1. 对象名称变异
        2. 数字后缀变化
        3. Bus/Attenuation 在同类中替换
        """
        results = []
        
        for _ in range(count):
            new_dsl = dsl_code
            
            # 收集所有对象名
            names = re.findall(r'CREATE\s+\w+\s+"([^"]+)"', dsl_code)
            name_mapping = {}
            
            # 为每个名称生成变异
            for name in names:
                if name not in name_mapping:
                    mutated = self.name_mutator.mutate(name, self.pool, 0.5)
                    name_mapping[name] = mutated
            
            # 应用名称替换（注意顺序，长名称优先）
            for old_name, new_name in sorted(name_mapping.items(), key=lambda x: -len(x[0])):
                if old_name != new_name:
                    new_dsl = new_dsl.replace(f'"{old_name}"', f'"{new_name}"')
                    self.stats["name_mutations"] += 1
            
            # 随机替换 Bus（同类替换）
            if self.pool.buses and random.random() > 0.7:
                new_dsl = self._swap_link_target(new_dsl, "Bus", self.pool.get_random_bus())
                self.stats["parameter_swaps"] += 1
            
            # 随机替换 Attenuation（同类替换）
            if self.pool.attenuations and random.random() > 0.7:
                new_attn = self.pool.get_random_attenuation()
                if new_attn:
                    new_dsl = self._swap_link_target(new_dsl, "Attenuation", new_attn)
                    self.stats["parameter_swaps"] += 1
            
            if new_dsl != dsl_code:
                results.append(new_dsl)
        
        return results
    
    def fission_medium(self, dsl_code: str, count: int = 2) -> List[str]:
        """
        中级裂变 - 结构简化和子集提取
        
        策略：
        1. 提取部分子树
        2. 移除可选属性
        3. 简化层级
        """
        results = []
        lines = dsl_code.strip().split("\n")
        
        for _ in range(count):
            # 策略1: 提取子树
            subset = self._extract_subtree(lines)
            if subset and len(subset) >= 3:
                results.append("\n".join(subset))
                self.stats["subset_extractions"] += 1
            
            # 策略2: 移除部分 SET_PROP
            simplified = self._simplify_props(lines)
            if simplified != lines:
                results.append("\n".join(simplified))
                self.stats["structure_simplifications"] += 1
        
        return results
    
    def fission_advanced(self, samples: List[str], count: int = 2) -> List[str]:
        """
        高级裂变 - 跨样本组合
        
        策略：
        1. 提取不同样本的子树进行组合
        2. 参数交叉替换
        """
        results = []
        
        if len(samples) < 2:
            return results
        
        for _ in range(count):
            # 随机选择两个样本
            s1, s2 = random.sample(samples, 2)
            
            # 尝试组合
            combined = self._combine_samples(s1, s2)
            if combined:
                results.append(combined)
        
        return results
    
    def _swap_link_target(self, dsl: str, link_type: str, new_target: str) -> str:
        """替换 LINK 目标"""
        pattern = rf'(LINK\s+"[^"]+"\s+TO\s+)"[^"]+"\s+(AS\s+"{link_type}")'
        return re.sub(pattern, rf'\1"{new_target}" \2', dsl, count=1)
    
    def _extract_subtree(self, lines: List[str]) -> List[str]:
        """提取子树"""
        # 找到所有 CREATE 语句
        creates = [(i, line) for i, line in enumerate(lines) if line.strip().startswith("CREATE")]
        
        if len(creates) < 2:
            return []
        
        # 随机选择一个非根节点作为新的根
        start_idx = random.randint(1, len(creates) - 1)
        start_line_idx = creates[start_idx][0]
        
        # 提取该节点的名称
        match = re.search(r'CREATE\s+\w+\s+"([^"]+)"', creates[start_idx][1])
        if not match:
            return []
        
        root_name = match.group(1)
        
        # 收集该子树的所有行
        subtree = []
        collecting = False
        depth = 0
        
        for i, line in enumerate(lines):
            if i == start_line_idx:
                collecting = True
            
            if collecting:
                # 检查是否还在子树内
                if line.strip().startswith("CREATE"):
                    create_match = re.search(r'UNDER\s+"([^"]+)"', line)
                    if create_match:
                        parent = create_match.group(1)
                        # 检查父节点是否在我们的子树中
                        if parent == root_name or any(f'"{parent}"' in l for l in subtree if "CREATE" in l):
                            subtree.append(line)
                        elif i > start_line_idx:
                            break
                        else:
                            subtree.append(line)
                    else:
                        subtree.append(line)
                elif f'"{root_name}"' in line or any(f'"{n}"' in line for n in self._get_names_from_lines(subtree)):
                    subtree.append(line)
        
        return subtree if len(subtree) >= 3 else []
    
    def _get_names_from_lines(self, lines: List[str]) -> List[str]:
        """从行中提取对象名"""
        names = []
        for line in lines:
            match = re.search(r'CREATE\s+\w+\s+"([^"]+)"', line)
            if match:
                names.append(match.group(1))
        return names
    
    def _simplify_props(self, lines: List[str]) -> List[str]:
        """简化属性，移除部分 SET_PROP"""
        result = []
        props_removed = 0
        max_remove = random.randint(1, 3)
        
        for line in lines:
            if line.strip().startswith("SET_PROP"):
                if props_removed < max_remove and random.random() > 0.5:
                    props_removed += 1
                    continue
            result.append(line)
        
        return result
    
    def _combine_samples(self, s1: str, s2: str) -> Optional[str]:
        """组合两个样本"""
        lines1 = s1.strip().split("\n")
        lines2 = s2.strip().split("\n")
        
        # 从 s1 提取根和部分子节点
        root_lines = []
        for line in lines1[:len(lines1)//2]:
            root_lines.append(line)
        
        if not root_lines:
            return None
        
        # 获取根名称
        root_match = re.search(r'CREATE\s+\w+\s+"([^"]+)"', lines1[0])
        if not root_match:
            return None
        
        root_name = root_match.group(1)
        
        # 从 s2 提取一些子结构并重新挂载
        for line in lines2:
            if line.strip().startswith("CREATE"):
                # 修改 UNDER 指向新的根
                new_line = re.sub(r'UNDER\s+"[^"]+"', f'UNDER "{root_name}"', line)
                root_lines.append(new_line)
            elif "SET_PROP" in line or "LINK" in line:
                # 检查这个操作的对象是否已经在我们的结构中
                obj_match = re.search(r'"([^"]+)"', line)
                if obj_match:
                    obj_name = obj_match.group(1)
                    if any(f'"{obj_name}"' in l for l in root_lines):
                        root_lines.append(line)
        
        return "\n".join(root_lines) if len(root_lines) > 3 else None


# =============================================================================
# 主处理流程
# =============================================================================

class FissionProcessor:
    """裂变处理器"""
    
    def __init__(self):
        self.pool = ParameterPool()
        self.fission = None
    
    def process(
        self,
        input_path: str,
        output_path: str,
        target_count: int,
        level: str = "simple"
    ) -> Tuple[int, int]:
        """
        处理 JSONL 文件进行裂变
        
        Args:
            input_path: 输入文件
            output_path: 输出文件
            target_count: 目标样本数
            level: 裂变级别 (simple/medium/advanced/auto)
            
        Returns:
            (原始数量, 最终数量)
        """
        # 第一遍：读取所有样本并构建参数池
        print("📊 第一阶段：分析现有数据，构建参数池...")
        samples = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    samples.append(data)
                    self.pool.extract_from_dsl(data.get("output", ""))
                except:
                    pass
        
        original_count = len(samples)
        print(f"   原始样本: {original_count}")
        print(f"   Bus 类型: {len(self.pool.buses)}")
        print(f"   Attenuation 类型: {len(self.pool.attenuations)}")
        print(f"   名称前缀: {len(self.pool.name_prefixes)}")
        print(f"   名称后缀: {len(self.pool.name_suffixes)}")
        
        # 初始化裂变器
        self.fission = DSLFission(self.pool)
        
        # 计算需要裂变的数量
        needed = max(0, target_count - original_count)
        if needed == 0:
            print(f"   ✅ 已有 {original_count} 样本，无需裂变")
            # 直接复制
            with open(output_path, 'w', encoding='utf-8') as f:
                for s in samples:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            return original_count, original_count
        
        print(f"   需要裂变: {needed} 个新样本")
        
        # 第二遍：裂变
        print(f"\n🔬 第二阶段：执行 {level} 级别裂变...")
        
        new_samples = []
        iterations = 0
        max_iterations = needed * 10  # 防止无限循环
        
        # 提取所有 DSL 代码用于高级裂变
        all_dsl = [s.get("output", "") for s in samples]
        
        while len(new_samples) < needed and iterations < max_iterations:
            iterations += 1
            
            # 随机选择一个样本进行裂变
            base_sample = random.choice(samples)
            base_dsl = base_sample.get("output", "")
            
            fissioned = []
            
            if level == "simple":
                fissioned = self.fission.fission_simple(base_dsl, 2)
            elif level == "medium":
                fissioned = self.fission.fission_simple(base_dsl, 1)
                fissioned += self.fission.fission_medium(base_dsl, 1)
            elif level == "advanced":
                fissioned = self.fission.fission_simple(base_dsl, 1)
                fissioned += self.fission.fission_medium(base_dsl, 1)
                fissioned += self.fission.fission_advanced(all_dsl, 1)
            elif level == "auto":
                # 自动选择
                r = random.random()
                if r < 0.5:
                    fissioned = self.fission.fission_simple(base_dsl, 2)
                elif r < 0.8:
                    fissioned = self.fission.fission_medium(base_dsl, 2)
                else:
                    fissioned = self.fission.fission_advanced(all_dsl, 1)
            
            # 验证并添加
            for new_dsl in fissioned:
                if self._validate_dsl(new_dsl) and new_dsl not in all_dsl:
                    # 创建新样本
                    new_sample = copy.deepcopy(base_sample)
                    new_sample["output"] = new_dsl
                    new_sample["meta"]["fissioned"] = True
                    new_sample["meta"]["fission_level"] = level
                    
                    # 更新 instruction（简单变化）
                    new_sample["instruction"] = self._mutate_instruction(
                        base_sample.get("instruction", "")
                    )
                    
                    new_samples.append(new_sample)
                    all_dsl.append(new_dsl)
                    
                    if len(new_samples) >= needed:
                        break
            
            # 进度显示
            if iterations % 100 == 0:
                print(f"   已生成 {len(new_samples)}/{needed} ...")
        
        # 写入结果
        print(f"\n📝 第三阶段：写入结果...")
        
        final_samples = samples + new_samples
        random.shuffle(final_samples)  # 打乱顺序
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for s in final_samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        
        final_count = len(final_samples)
        
        print(f"\n📊 裂变统计:")
        print(f"   名称变异: {self.fission.stats['name_mutations']}")
        print(f"   参数替换: {self.fission.stats['parameter_swaps']}")
        print(f"   子集提取: {self.fission.stats['subset_extractions']}")
        print(f"   结构简化: {self.fission.stats['structure_simplifications']}")
        
        return original_count, final_count
    
    def _validate_dsl(self, dsl: str) -> bool:
        """验证 DSL 基本语法"""
        if not dsl or len(dsl) < 10:
            return False
        
        lines = dsl.strip().split("\n")
        
        # 必须有至少一个 CREATE
        has_create = any(line.strip().startswith("CREATE") for line in lines)
        if not has_create:
            return False
        
        # 检查基本语法
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 必须是已知的命令开头
            valid_starts = ["CREATE", "SET_PROP", "LINK", "ASSIGN", "ADD_ACTION", "#"]
            if not any(line.startswith(s) for s in valid_starts):
                return False
            
            # CREATE 必须有 UNDER
            if line.startswith("CREATE") and "UNDER" not in line:
                return False
            
            # LINK 必须有 TO 和 AS
            if line.startswith("LINK") and ("TO" not in line or "AS" not in line):
                return False
        
        return True
    
    def _mutate_instruction(self, instruction: str) -> str:
        """轻微变异 instruction"""
        mutations = [
            ("创建", "搭建"),
            ("搭建", "构建"),
            ("构建", "制作"),
            ("帮我", "请"),
            ("需要", "要"),
            ("一套", "一个"),
            ("玩家", "主角"),
            ("主角", "角色"),
        ]
        
        result = instruction
        for old, new in mutations:
            if old in result and random.random() > 0.7:
                result = result.replace(old, new, 1)
                break
        
        return result


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="DSL 样本裂变器 - 扩充训练数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
裂变级别说明:
  simple   - 仅改名、微调数值、同类参数替换（最安全）
  medium   - 结构简化、子集提取（中等风险）
  advanced - 跨样本组合、参数交叉（需要验证）
  auto     - 自动混合各级别

示例:
  # 简单裂变到 10000 样本
  python dsl_fission.py wwise_reverse_dataset.jsonl wwise_reverse_dataset_output.jsonl --target 12000 --level simple
  
  # 中级裂变
  python dsl_fission.py input.jsonl output.jsonl --target 8000 --level medium
  
  # 自动模式
  python dsl_fission.py input.jsonl output.jsonl --target 15000 --level auto
        """
    )
    
    parser.add_argument("input", help="输入 JSONL 文件")
    parser.add_argument("output", help="输出 JSONL 文件")
    parser.add_argument("-t", "--target", type=int, required=True,
                        help="目标样本数量")
    parser.add_argument("-l", "--level", 
                        choices=["simple", "medium", "advanced", "auto"],
                        default="simple",
                        help="裂变级别 (默认: simple)")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机种子（用于复现）")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        return
    
    if args.seed:
        random.seed(args.seed)
    
    print("=" * 70)
    print("🔬 DSL Sample Fission V1.0")
    print("=" * 70)
    print(f"   输入: {args.input}")
    print(f"   输出: {args.output}")
    print(f"   目标: {args.target} 样本")
    print(f"   级别: {args.level}")
    print("-" * 70)
    
    processor = FissionProcessor()
    original, final = processor.process(
        args.input,
        args.output,
        args.target,
        args.level
    )
    
    print("-" * 70)
    print(f"✅ 裂变完成!")
    print(f"   原始样本: {original}")
    print(f"   最终样本: {final}")
    print(f"   增加: {final - original} ({(final/original - 1)*100:.1f}%)")
    print(f"   输出: {args.output}")


if __name__ == "__main__":
    main()