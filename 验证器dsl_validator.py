# -*- coding: utf-8 -*-
"""
【DSL 验证器】DSL Validator (V2.0 - DSL Parser V7.0 完全适配版)
功能：验证逆向生成的 DSL 是否能被 Parser V7.0 正确解析

更新日志 V2.0:
1. [Core] 完全适配 DSL Parser V7.0 的所有语法
2. [Feat] 多层次验证：语法 → 语义 → 依赖
3. [Feat] 详细的错误诊断报告
4. [Feat] 批量验证与统计
5. [Feat] 自动过滤无效样本

验证层次：
- Level 1: 语法验证 (Parser 能否解析)
- Level 2: 语义验证 (指令是否合理)
- Level 3: 依赖验证 (父级/引用是否存在)
"""
import json
import re
import os
import sys
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

# 导入 DSL Parser
try:
    # 尝试从当前目录或 src 目录导入
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from dsl_parser import DSLParser
except ImportError:
    print("⚠️ 警告: 无法导入 DSLParser，将使用内置简化版本")
    DSLParser = None


@dataclass
class ValidationResult:
    """单条 DSL 的验证结果"""
    line_number: int
    is_valid: bool
    syntax_ok: bool
    semantic_ok: bool
    dependency_ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    plan_length: int = 0
    commands_found: Dict[str, int] = field(default_factory=dict)


class DSLValidatorV2:
    """
    DSL 验证器 V2.0
    适配 DSL Parser V7.0
    """
    
    def __init__(self):
        # 初始化 Parser
        if DSLParser:
            self.parser = DSLParser()
        else:
            self.parser = None
        
        # 预置的 Wwise 系统对象 (这些肯定存在)
        self.system_objects = {
            "Master Audio Bus", "Master", "Root", 
            "Default Work Unit", "Default Conversion Settings",
            "Master-Mixer Hierarchy", "Actor-Mixer Hierarchy",
            "Events", "Switches", "States", "Game Parameters",
            "Attenuations", "Effects"
        }
        
        # 本次 Session 创建的对象
        self.created_objects: Set[str] = set()
        
        # 验证统计
        self.stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "syntax_errors": 0,
            "semantic_errors": 0,
            "dependency_warnings": 0
        }
        
        # 详细结果
        self.results: List[ValidationResult] = []

    def reset(self):
        """重置验证状态"""
        self.created_objects = set()
        self.stats = {k: 0 for k in self.stats}
        self.results = []

    def validate_dataset(self, file_path: str, 
                        output_valid: str = None,
                        output_invalid: str = None) -> Dict:
        """
        验证整个数据集
        
        Args:
            file_path: 输入 JSONL 文件路径
            output_valid: 有效样本输出路径 (可选)
            output_invalid: 无效样本输出路径 (可选)
        
        Returns:
            验证报告
        """
        print(f"🔍 DSL Validator V2.0 (Parser V7.0 Compatible)")
        print(f"   Input: {file_path}")
        print("-" * 50)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return {}

        self.reset()
        
        # 打开输出文件
        f_valid = open(output_valid, 'w', encoding='utf-8') if output_valid else None
        f_invalid = open(output_invalid, 'w', encoding='utf-8') if output_invalid else None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    result = self._validate_single(data, idx + 1)
                    self.results.append(result)
                    
                    # 更新统计
                    self.stats["total"] += 1
                    if result.is_valid:
                        self.stats["valid"] += 1
                        if f_valid:
                            f_valid.write(line)
                    else:
                        self.stats["invalid"] += 1
                        if f_invalid:
                            f_invalid.write(line)
                    
                    if not result.syntax_ok:
                        self.stats["syntax_errors"] += 1
                    if not result.semantic_ok:
                        self.stats["semantic_errors"] += 1
                    if result.warnings:
                        self.stats["dependency_warnings"] += len(result.warnings)
                        
                except json.JSONDecodeError:
                    self.stats["total"] += 1
                    self.stats["invalid"] += 1
                    self.stats["syntax_errors"] += 1
                    self.results.append(ValidationResult(
                        line_number=idx + 1,
                        is_valid=False,
                        syntax_ok=False,
                        semantic_ok=False,
                        dependency_ok=False,
                        errors=["JSON 解析错误"]
                    ))

        finally:
            if f_valid:
                f_valid.close()
            if f_invalid:
                f_invalid.close()

        return self._generate_report()

    def _validate_single(self, data: Dict, line_num: int) -> ValidationResult:
        """
        验证单条数据
        """
        result = ValidationResult(
            line_number=line_num,
            is_valid=True,
            syntax_ok=True,
            semantic_ok=True,
            dependency_ok=True
        )
        
        dsl_code = data.get('output', '')
        if not dsl_code.strip():
            result.is_valid = False
            result.syntax_ok = False
            result.errors.append("DSL 代码为空")
            return result

        dsl_lines = dsl_code.split('\n')
        
        # =====================================================================
        # Level 1: 语法验证 (使用 Parser)
        # =====================================================================
        if self.parser:
            try:
                plan = self.parser.parse(dsl_lines)
                result.plan_length = len(plan)
                
                if not plan:
                    result.syntax_ok = False
                    result.is_valid = False
                    result.errors.append("Parser 返回空计划")
                else:
                    # 收集解析诊断
                    if hasattr(self.parser, 'get_parse_diagnostics'):
                        diag = self.parser.get_parse_diagnostics()
                        result.errors.extend(diag.get('errors', []))
                        result.warnings.extend(diag.get('warnings', []))
                    
                    # 分析 Plan
                    result = self._analyze_plan(plan, result)
                    
            except Exception as e:
                result.syntax_ok = False
                result.is_valid = False
                result.errors.append(f"Parser 异常: {str(e)}")
        else:
            # 使用简化的正则验证
            result = self._regex_validate(dsl_lines, result)
        
        # =====================================================================
        # Level 2: 语义验证
        # =====================================================================
        if result.syntax_ok:
            result = self._semantic_validate(dsl_lines, result)
        
        # =====================================================================
        # Level 3: 依赖验证
        # =====================================================================
        if result.semantic_ok:
            result = self._dependency_validate(dsl_lines, result)
        
        # 最终判定
        result.is_valid = result.syntax_ok and result.semantic_ok and len(result.errors) == 0
        
        return result

    def _analyze_plan(self, plan: List[Dict], result: ValidationResult) -> ValidationResult:
        """分析解析出的 WAAPI Plan"""
        commands = {"CREATE": 0, "SET_PROP": 0, "LINK": 0, "ASSIGN": 0, "ADD_ACTION": 0, "OTHER": 0}
        
        for step in plan:
            action = step.get('action', '')
            args = step.get('args', {})
            
            if 'create' in action:
                commands["CREATE"] += 1
                obj_name = args.get('name')
                if obj_name:
                    self.created_objects.add(obj_name)
                    
            elif 'setProperty' in action:
                commands["SET_PROP"] += 1
                
            elif 'setReference' in action:
                commands["LINK"] += 1
                
            elif 'addAssignment' in action:
                commands["ASSIGN"] += 1
                
            else:
                commands["OTHER"] += 1
        
        result.commands_found = commands
        return result

    def _regex_validate(self, dsl_lines: List[str], result: ValidationResult) -> ValidationResult:
        """使用正则表达式进行简化验证"""
        valid_patterns = [
            r'^CREATE\s+\w+\s+"[^"]+"\s+UNDER\s+"[^"]+"',
            r'^SET_PROP\s+"[^"]+"\s+"[^"]+"\s*=\s*.+',
            r'^LINK\s+"[^"]+"\s+TO\s+"[^"]+"\s+AS\s+"[^"]+"',
            r'^ASSIGN\s+"[^"]+"\s+TO\s+"[^"]+"',
            r'^ADD_ACTION\s+"[^"]+"\s+\w+\s+"[^"]+"',
            r'^CREATE_EVENT\s+"[^"]+"\s+PLAY\s+"[^"]+"',
            r'^RENAME\s+"[^"]+"\s+TO\s+"[^"]+"',
            r'^DELETE\s+"[^"]+"',
            r'^COPY\s+"[^"]+"\s+TO\s+"[^"]+"\s+AS\s+"[^"]+"',
            r'^MOVE\s+"[^"]+"\s+TO\s+"[^"]+"',
            r'^IMPORT_AUDIO\s+"[^"]+"\s+INTO\s+"[^"]+"',
            r'^#',  # 注释
            r'^\s*$'  # 空行
        ]
        
        commands = {"CREATE": 0, "SET_PROP": 0, "LINK": 0, "ASSIGN": 0, "ADD_ACTION": 0, "OTHER": 0}
        
        for line in dsl_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 清洗行号前缀
            line = re.sub(r'^\d+\.\s*', '', line)
            
            matched = False
            for pattern in valid_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    matched = True
                    # 统计指令
                    for cmd in commands.keys():
                        if line.upper().startswith(cmd):
                            commands[cmd] += 1
                            break
                    break
            
            if not matched:
                result.syntax_ok = False
                result.errors.append(f"无法识别的指令: {line[:50]}...")
        
        result.commands_found = commands
        result.plan_length = sum(commands.values())
        return result

    def _semantic_validate(self, dsl_lines: List[str], result: ValidationResult) -> ValidationResult:
        """语义验证"""
        for line in dsl_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            line = re.sub(r'^\d+\.\s*', '', line)
            
            # 检查 1: CREATE 类型是否有效
            create_match = re.match(r'CREATE\s+(\w+)', line, re.IGNORECASE)
            if create_match:
                obj_type = create_match.group(1)
                valid_types = [
                    "ActorMixer", "RandomSequenceContainer", "SwitchContainer",
                    "BlendContainer", "Folder", "WorkUnit", "Sound", "Bus", "AuxBus",
                    "Event", "SwitchGroup", "Switch", "StateGroup", "State",
                    "GameParameter", "Effect", "Attenuation", "Action"
                ]
                # 也接受带空格的写法 (Parser 会自动纠正)
                if obj_type not in valid_types and obj_type.replace("-", "") not in valid_types:
                    result.warnings.append(f"非标准类型 '{obj_type}'，Parser 会尝试纠正")
            
            # 检查 2: SET_PROP 属性是否有效
            prop_match = re.match(r'SET_PROP\s+"[^"]+"\s+"([^"]+)"', line, re.IGNORECASE)
            if prop_match:
                prop_name = prop_match.group(1)
                valid_props = [
                    "Volume", "Pitch", "Lowpass", "Highpass",
                    "InitialValue", "MinValue", "MaxValue",
                    "OverrideOutput", "OverridePositioning",
                    "Priority", "IsLoopingEnabled", "Color"
                ]
                if prop_name not in valid_props:
                    result.warnings.append(f"非常规属性 '{prop_name}'，可能需要确认")
            
            # 检查 3: LINK 类型是否有效
            link_match = re.match(r'LINK\s+"[^"]+"\s+TO\s+"[^"]+"\s+AS\s+"([^"]+)"', line, re.IGNORECASE)
            if link_match:
                ref_type = link_match.group(1)
                valid_refs = [
                    "Bus", "OutputBus", "Attenuation",
                    "SwitchGroupOrStateGroup", "SwitchGroup", "StateGroup",
                    "Effect0", "Effect1", "Effect2", "Effect3",
                    "UserAuxSend0", "UserAuxSend1", "GameParameter", "Conversion"
                ]
                if ref_type not in valid_refs:
                    result.semantic_ok = False
                    result.errors.append(f"无效的引用类型 '{ref_type}'")
        
        return result

    def _dependency_validate(self, dsl_lines: List[str], result: ValidationResult) -> ValidationResult:
        """依赖验证"""
        local_created = set()
        
        for line in dsl_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            line = re.sub(r'^\d+\.\s*', '', line)
            
            # CREATE 指令：记录创建的对象，检查父级
            create_match = re.match(r'CREATE\s+\w+\s+"([^"]+)"\s+UNDER\s+"([^"]+)"', line, re.IGNORECASE)
            if create_match:
                obj_name, parent_name = create_match.groups()
                local_created.add(obj_name)
                
                # 检查父级是否存在
                if parent_name not in self.system_objects and \
                   parent_name not in self.created_objects and \
                   parent_name not in local_created:
                    result.warnings.append(
                        f"父级 '{parent_name}' 未在上下文中找到 (对象: {obj_name})"
                    )
            
            # LINK 指令：检查目标是否存在
            link_match = re.match(r'LINK\s+"([^"]+)"\s+TO\s+"([^"]+)"', line, re.IGNORECASE)
            if link_match:
                child_name, target_name = link_match.groups()
                
                # 跳过系统对象
                if target_name not in self.system_objects and \
                   target_name not in self.created_objects and \
                   target_name not in local_created:
                    result.warnings.append(
                        f"引用目标 '{target_name}' 可能不存在 (对象: {child_name})"
                    )
            
            # ASSIGN 指令：检查状态/开关是否存在
            assign_match = re.match(r'ASSIGN\s+"([^"]+)"\s+TO\s+"([^"]+)"', line, re.IGNORECASE)
            if assign_match:
                child_name, state_name = assign_match.groups()
                
                if state_name not in self.created_objects and state_name not in local_created:
                    result.warnings.append(
                        f"Switch/State '{state_name}' 可能不存在 (对象: {child_name})"
                    )
        
        # 更新全局创建记录
        self.created_objects.update(local_created)
        
        return result

    def _generate_report(self) -> Dict:
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("📊 DSL Validation Report")
        print("=" * 60)
        
        total = self.stats["total"]
        valid = self.stats["valid"]
        invalid = self.stats["invalid"]
        
        print(f"总样本数:           {total}")
        print(f"有效样本:           {valid} ({valid/max(1,total)*100:.1f}%)")
        print(f"无效样本:           {invalid} ({invalid/max(1,total)*100:.1f}%)")
        print("-" * 60)
        print(f"语法错误:           {self.stats['syntax_errors']}")
        print(f"语义错误:           {self.stats['semantic_errors']}")
        print(f"依赖警告:           {self.stats['dependency_warnings']}")
        print("-" * 60)
        
        # 显示错误样例
        error_samples = [r for r in self.results if not r.is_valid][:5]
        if error_samples:
            print("\n❌ 错误样例 (前5条):")
            for sample in error_samples:
                print(f"  Line {sample.line_number}: {', '.join(sample.errors[:2])}")
        
        # 显示警告统计
        all_warnings = []
        for r in self.results:
            all_warnings.extend(r.warnings)
        
        if all_warnings:
            # 聚合相似警告
            warning_types = {}
            for w in all_warnings:
                key = w.split("'")[0] if "'" in w else w[:30]
                warning_types[key] = warning_types.get(key, 0) + 1
            
            print("\n⚠️ 警告分布:")
            for wtype, count in sorted(warning_types.items(), key=lambda x: -x[1])[:5]:
                print(f"  {wtype}... : {count} 次")
        
        print("=" * 60)
        
        return {
            "stats": self.stats,
            "results": self.results
        }


# =============================================================================
# 命令行入口
# =============================================================================
if __name__ == "__main__":
    validator = DSLValidatorV2()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_valid = sys.argv[2] if len(sys.argv) > 2 else None
        output_invalid = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        input_file = input("请输入要验证的 JSONL 文件路径: ").strip()
        output_valid = None
        output_invalid = None
    
    validator.validate_dataset(input_file, output_valid, output_invalid)
