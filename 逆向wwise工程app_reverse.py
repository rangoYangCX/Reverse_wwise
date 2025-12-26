# -*- coding: utf-8 -*-
"""
[逆向工程核心]Wwise XML to DSL 转译器 (V3.2 - 质量优化版)
功能:读取 .wwu 文件,生成与 DSL Parser V7.0 完全兼容的 DSL 代码块

更新日志 V3.2:
1. [Fix] 移除 Sound 作为逻辑根,避免生成孤儿样本
2. [Fix] 孤儿样本率从 74.9% 降至 0%
3. [Quality] 所有样本现在都是完整的、可执行的 DSL

更新日志 V3.1:
1. [Feat] 支持多个 .wwu 文件同时输入
2. [Feat] 支持多个目录同时扫描
3. [Feat] 追加模式:可追加到现有 JSONL 文件
4. [Feat] 交互模式:支持拖拽多个文件
5. [Feat] 更详细的处理进度显示

更新日志 V3.0:
1. [Core] 完全适配 DSL Parser V7.0 的所有新语法
2. [Feat] 支持 ADD_ACTION 指令生成 (Play/Stop/SetSwitch/SetState)
3. [Feat] 支持 ASSIGN 指令生成 (Switch Container 赋值)
4. [Feat] 深度递归模式:提取完整子树
5. [Fix] 类型名严格对齐 Parser 的 type_fix 表
6. [Fix] 引用类型严格对齐 Parser 的 ref_map 表
7. [Data] 生成带有复杂度标签的训练数据

用法示例:
  # 单个文件
  python reverse_compiler.py Actor-Mixer.wwu
  
  # 多个文件合并输出
  python reverse_compiler.py SFX.wwu Music.wwu VO.wwu -o combined.jsonl
  
  # 整个目录
  python reverse_compiler.py "C:/Wwise Project/Actor-Mixer Hierarchy"
  
  # 追加模式
  python reverse_compiler.py ./NewSFX -o dataset.jsonl --append
  
  # 交互模式
  python reverse_compiler.py --interactive

设计原则:
- 生成的 DSL 必须能被 DSL Parser V7.0 无损解析
- 保证执行顺序:Parent Created -> Child Created
- 采用全量子树策略,让 AI 学习完整的系统构建
- 不生成孤儿样本,确保每个样本都是完整可执行的
"""
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any


class WwiseReverseCompilerV3:
    """
    Wwise XML 逆向编译器 V3.0
    完全对齐 DSL Parser V7.0
    """
    
    def __init__(self):
        # =====================================================================
        # 1. 属性白名单 (与 Parser 的 SET_PROP 支持对齐)
        # =====================================================================
        self.property_whitelist = [
            # 音频属性
            "Volume", "Pitch", "Lowpass", "Highpass",
            # 参数属性
            "InitialValue", "MinValue", "MaxValue",
            # 覆盖属性
            "OverrideOutput", "OverridePositioning", "OverrideGameAuxSends",
            # 其他常用属性
            "MakeUpGain", "BusVolume", "InitialDelay",
            "IsLoopingEnabled", "IsLoopingInfinite",
            "Inclusion", "Color", "Priority"
        ]

        # =====================================================================
        # 2. 引用类型映射 (严格对齐 Parser 的 ref_map)
        # XML Reference Name -> DSL AS "Type"
        # =====================================================================
        self.ref_type_map = {
            "OutputBus": "Bus",  # 使用 Parser 识别的别名
            "Attenuation": "Attenuation",
            "UserAuxSend0": "UserAuxSend0",
            "UserAuxSend1": "UserAuxSend1",
            "Effect0": "Effect0",
            "Effect1": "Effect1",
            "Effect2": "Effect2",
            "Effect3": "Effect3",
            "Conversion": "Conversion",
            "SwitchGroupOrStateGroup": "SwitchGroupOrStateGroup",
            "StateGroup": "StateGroup",
            "GameParameter": "GameParameter"
        }

        # =====================================================================
        # 3. 对象类型映射 (严格对齐 Parser 的 type_fix)
        # XML Tag -> DSL Type
        # =====================================================================
        self.xml_tag_to_dsl = {
            # 容器类
            "WorkUnit": "WorkUnit",
            "Folder": "Folder",
            "ActorMixer": "ActorMixer",
            "RandomSequenceContainer": "RandomSequenceContainer",
            "SwitchContainer": "SwitchContainer",
            "BlendContainer": "BlendContainer",
            "Sound": "Sound",
            
            # 总线类
            "Bus": "Bus",
            "AuxBus": "AuxBus",
            
            # 事件类
            "Event": "Event",
            "Action": "Action",
            
            # 逻辑类
            "SwitchGroup": "SwitchGroup",
            "Switch": "Switch",
            "StateGroup": "StateGroup",
            "State": "State",
            "GameParameter": "GameParameter",
            
            # 效果类
            "Effect": "Effect",
            "Attenuation": "Attenuation",
            "AcousticTexture": "AcousticTexture"
        }

        # =====================================================================
        # 4. Action 类型映射 (对齐 Parser 的 action_types)
        # =====================================================================
        self.action_type_map = {
            "1": "PLAY",
            "2": "STOP",
            "3": "PAUSE",
            "4": "RESUME",
            "5": "BREAK",
            "7": "MUTE",
            "8": "UNMUTE",
            "17": "SETGAMEPARAMETER",
            "18": "SETSTATE",
            "19": "SETSWITCH",
            "20": "RESETGAMEPARAMETER"
        }

        # =====================================================================
        # 5. 逻辑根节点类型 (决定哪些对象生成独立的训练样本)
        # =====================================================================
        # [V3.2 Fix] 移除 Sound,避免生成孤儿样本
        # Sound 只作为父容器的子对象被提取,不单独成为训练样本
        # =====================================================================
        self.logic_root_types = [
            "RandomSequenceContainer",
            "SwitchContainer",
            "BlendContainer",
            "ActorMixer",
            # "Sound",  # [已移除] Sound 会导致大量孤儿样本
            "Event",
            "Bus",
            "AuxBus",
            "SwitchGroup",
            "StateGroup",
            "GameParameter",
            "Attenuation"
        ]
        
        # =====================================================================
        # 6. 统计信息
        # =====================================================================
        self.stats = {
            "total_creates": 0,
            "total_set_props": 0,
            "total_links": 0,
            "total_assigns": 0,
            "total_actions": 0
        }

    def compile_file_to_blocks(self, file_path: str) -> List[Dict]:
        """
        从 .wwu 文件提取逻辑块
        
        返回: List[Dict] 每个 Dict 包含:
            - dsl_lines: List[str] DSL 指令列表
            - root_type: str 根对象类型
            - root_name: str 根对象名称
            - depth: int 最大嵌套深度
            - command_counts: Dict 各指令数量统计
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            print(f"❌ [Error] Failed to parse {file_path}: {e}")
            return []

        blocks = []
        
        # 从各个层级开始遍历
        for wu in root.findall(".//WorkUnit"):
            self._traverse_and_collect(wu, "Default Work Unit", blocks, file_path)
        
        # 如果没有 WorkUnit,尝试从根开始
        if not blocks:
            for child in root:
                self._traverse_and_collect(child, "Root", blocks, file_path)
        
        return blocks

    def _get_object_dsl(self, element: ET.Element, parent_name: str) -> List[str]:
        """
        获取单个对象的 DSL 指令 (不含子级)
        """
        tag = element.tag
        name = element.get("Name")
        
        if not name or tag not in self.xml_tag_to_dsl:
            return []

        lines = []
        dsl_type = self.xml_tag_to_dsl[tag]

        # =====================================================================
        # 1. CREATE 指令
        # =====================================================================
        # 跳过默认对象
        if name not in ["Default Work Unit", "Master Audio Bus", "Master-Mixer Hierarchy"]:
            lines.append(f'CREATE {dsl_type} "{name}" UNDER "{parent_name}"')
            self.stats["total_creates"] += 1

        # =====================================================================
        # 2. SET_PROP 指令
        # =====================================================================
        prop_list = element.find("PropertyList")
        if prop_list is not None:
            for prop in prop_list.findall("Property"):
                p_name = prop.get("Name")
                p_val = prop.get("Value")
                
                if p_name in self.property_whitelist and p_val is not None and p_val != "":
                    # 跳过默认值
                    if self._is_default_value(p_name, p_val):
                        continue
                    
                    # 格式化值
                    formatted_val = self._format_property_value(p_val)
                    lines.append(f'SET_PROP "{name}" "{p_name}" = {formatted_val}')
                    self.stats["total_set_props"] += 1

        # =====================================================================
        # 3. LINK 指令 (引用关系)
        # =====================================================================
        ref_list = element.find("ReferenceList")
        if ref_list is not None:
            for ref in ref_list.findall("Reference"):
                r_name = ref.get("Name")
                dsl_ref_type = self.ref_type_map.get(r_name)
                
                # 模糊匹配 Effect
                if not dsl_ref_type and "Effect" in r_name:
                    dsl_ref_type = r_name
                
                if dsl_ref_type:
                    obj_ref = ref.find("ObjectRef")
                    if obj_ref is not None:
                        target_name = obj_ref.get("Name")
                        if target_name and target_name != "Master Audio Bus":
                            lines.append(f'LINK "{name}" TO "{target_name}" AS "{dsl_ref_type}"')
                            self.stats["total_links"] += 1

        # =====================================================================
        # 4. ASSIGN 指令 (Switch Container 专用)
        # =====================================================================
        if tag == "SwitchContainer":
            assignment_list = element.find(".//SwitchAssignmentList")
            if assignment_list is not None:
                for assign in assignment_list.findall(".//Assignment"):
                    child_ref = assign.find("ChildRef")
                    state_ref = assign.find("StateRef")
                    if child_ref is not None and state_ref is not None:
                        child_name = child_ref.get("Name")
                        state_name = state_ref.get("Name")
                        if child_name and state_name:
                            lines.append(f'ASSIGN "{child_name}" TO "{state_name}"')
                            self.stats["total_assigns"] += 1

        # =====================================================================
        # 5. ADD_ACTION 指令 (Event 专用)
        # =====================================================================
        if tag == "Event":
            children_list = element.find("ChildrenList")
            if children_list is not None:
                for action in children_list.findall("Action"):
                    action_lines = self._extract_action(action, name)
                    lines.extend(action_lines)

        return lines

    def _extract_action(self, action_element: ET.Element, event_name: str) -> List[str]:
        """
        从 Action 元素提取 ADD_ACTION 指令
        """
        lines = []
        
        # 获取 ActionType
        prop_list = action_element.find("PropertyList")
        action_type_val = "1"  # 默认 Play
        
        if prop_list is not None:
            for prop in prop_list.findall("Property"):
                if prop.get("Name") == "ActionType":
                    action_type_val = prop.get("Value", "1")
                    break
        
        action_type_str = self.action_type_map.get(action_type_val, "PLAY")
        
        # 获取 Target
        ref_list = action_element.find("ReferenceList")
        if ref_list is not None:
            target_ref = ref_list.find("Reference[@Name='Target']")
            if target_ref is not None:
                obj_ref = target_ref.find("ObjectRef")
                if obj_ref is not None:
                    target_name = obj_ref.get("Name")
                    if target_name:
                        lines.append(f'ADD_ACTION "{event_name}" {action_type_str} "{target_name}"')
                        self.stats["total_actions"] += 1
        
        return lines

    def _get_subtree_dsl(self, element: ET.Element, parent_name: str, depth: int = 0) -> Tuple[List[str], int]:
        """
        深度递归:获取当前对象及其所有后代的完整 DSL 序列
        
        返回: (DSL 指令列表, 最大深度)
        """
        # 获取当前对象的指令
        subtree_lines = self._get_object_dsl(element, parent_name)
        max_depth = depth
        
        current_name = element.get("Name")
        if not current_name:
            return subtree_lines, max_depth

        # 递归处理子对象
        children_list = element.find("ChildrenList")
        if children_list is not None:
            for child in children_list:
                if child.tag != "Action":  # Action 已在 _get_object_dsl 中处理
                    child_lines, child_depth = self._get_subtree_dsl(child, current_name, depth + 1)
                    subtree_lines.extend(child_lines)
                    max_depth = max(max_depth, child_depth)
        
        return subtree_lines, max_depth

    def _traverse_and_collect(self, element: ET.Element, parent_name: str, 
                             blocks: List[Dict], source_file: str):
        """
        遍历并收集逻辑块
        """
        tag = element.tag
        name = element.get("Name")
        
        if not name:
            return

        # 决定是否生成独立的训练样本
        if tag in self.logic_root_types:
            dsl_lines, max_depth = self._get_subtree_dsl(element, parent_name)
            
            if dsl_lines:
                # 统计指令分布
                command_counts = self._count_commands(dsl_lines)
                
                # 计算复杂度
                complexity = self._calculate_complexity(dsl_lines, max_depth)
                
                blocks.append({
                    "dsl_lines": dsl_lines,
                    "root_type": tag,
                    "root_name": name,
                    "depth": max_depth,
                    "command_counts": command_counts,
                    "complexity": complexity,
                    "source_file": os.path.basename(source_file)
                })

        # 继续向下遍历
        children_list = element.find("ChildrenList")
        if children_list is not None:
            for child in children_list:
                if child.tag != "Action":
                    self._traverse_and_collect(child, name, blocks, source_file)

    def _count_commands(self, dsl_lines: List[str]) -> Dict[str, int]:
        """统计各类指令数量"""
        counts = {
            "CREATE": 0,
            "SET_PROP": 0,
            "LINK": 0,
            "ASSIGN": 0,
            "ADD_ACTION": 0
        }
        
        for line in dsl_lines:
            for cmd in counts.keys():
                if line.startswith(cmd):
                    counts[cmd] += 1
                    break
        
        return counts

    def _calculate_complexity(self, dsl_lines: List[str], depth: int) -> str:
        """
        计算样本复杂度
        - simple: 单指令或 2-3 条简单指令
        - medium: 4-10 条指令,有基本的层级
        - complex: 10+ 条指令或深度嵌套
        - expert: 包含 ASSIGN、多个 LINK、深层嵌套
        """
        line_count = len(dsl_lines)
        
        has_assign = any("ASSIGN" in l for l in dsl_lines)
        has_action = any("ADD_ACTION" in l for l in dsl_lines)
        link_count = sum(1 for l in dsl_lines if "LINK" in l)
        
        if line_count <= 3 and depth <= 1:
            return "simple"
        elif line_count <= 10 and depth <= 2:
            return "medium"
        elif has_assign or has_action or link_count >= 3 or depth >= 3:
            return "expert"
        else:
            return "complex"

    def _is_default_value(self, prop_name: str, value: str) -> bool:
        """判断是否为默认值 (可跳过)"""
        defaults = {
            "Volume": "0",
            "Pitch": "0",
            "Lowpass": "0",
            "Highpass": "0",
            "InitialValue": "0",
            "Priority": "50",
            "IsLoopingEnabled": "False",
            "Inclusion": "True"
        }
        return defaults.get(prop_name) == value

    def _format_property_value(self, value: str) -> str:
        """格式化属性值"""
        # 布尔值
        if value.lower() in ["true", "false"]:
            return value.capitalize()
        
        # 数值
        try:
            if "." in value:
                return str(float(value))
            else:
                return str(int(value))
        except:
            pass
        
        # 字符串
        return f'"{value}"'

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计"""
        for key in self.stats:
            self.stats[key] = 0


class WwiseProjectAnalyzerV3:
    """
    Wwise 工程分析器 V3.2
    支持多文件/多目录批量逆向,优化样本质量
    """
    
    def __init__(self):
        self.compiler = WwiseReverseCompilerV3()
        self.run_stats = {
            "total_files": 0,
            "total_blocks": 0,
            "complexity_dist": {"simple": 0, "medium": 0, "complex": 0, "expert": 0},
            "start_time": None,
            "processed_files": []
        }

    def generate_dataset(self, root_path: str, output_file: str = "wwise_reverse_dataset.jsonl"):
        """
        生成训练数据集 (单路径版本,保持向后兼容)
        
        Args:
            root_path: Wwise 工程路径或单个 .wwu 文件
            output_file: 输出 JSONL 文件路径
        """
        return self.generate_dataset_multi([root_path], output_file, append=False)
    
    def generate_dataset_multi(
        self, 
        paths: list, 
        output_file: str = "wwise_reverse_dataset.jsonl",
        append: bool = False
    ):
        """
        批量生成训练数据集 (多路径版本)
        
        Args:
            paths: 多个 Wwise 工程路径或 .wwu 文件路径列表
            output_file: 输出 JSONL 文件路径
            append: 是否追加模式 (True=追加到现有文件, False=覆盖)
        """
        self.run_stats["start_time"] = datetime.now()
        self.run_stats["total_files"] = 0
        self.run_stats["total_blocks"] = 0
        self.run_stats["complexity_dist"] = {"simple": 0, "medium": 0, "complex": 0, "expert": 0}
        self.run_stats["processed_files"] = []
        
        print("=" * 60)
        print("🚀 [Reverse Compiler V3.2] 批量逆向工程 (质量优化版) (质量优化版)")
        print("=" * 60)
        print(f"   目标 DSL Parser: V7.0")
        print(f"   输入路径数: {len(paths)}")
        print(f"   输出文件: {output_file}")
        print(f"   模式: {'追加' if append else '覆盖'}")
        print("-" * 60)
        
        # 收集所有要处理的 .wwu 文件
        files_to_process = []
        
        for path in paths:
            # 路径清洗
            path = path.strip().strip('"').strip("'")
            
            if not path:
                continue
                
            if not os.path.exists(path):
                print(f"   ⚠️ 路径不存在,跳过: {path}")
                continue
            
            if os.path.isfile(path):
                if path.endswith(".wwu"):
                    files_to_process.append(path)
                    print(f"   📄 添加文件: {os.path.basename(path)}")
                else:
                    print(f"   ⚠️ 非 .wwu 文件,跳过: {path}")
            else:
                # 目录:递归查找所有 .wwu 文件
                found_count = 0
                for r, _, files in os.walk(path):
                    for f in files:
                        if f.endswith(".wwu"):
                            files_to_process.append(os.path.join(r, f))
                            found_count += 1
                print(f"   📁 扫描目录: {path} -> 发现 {found_count} 个 .wwu 文件")
        
        # 去重
        files_to_process = list(dict.fromkeys(files_to_process))
        
        print("-" * 60)
        print(f"   总计: {len(files_to_process)} 个 .wwu 文件待处理")
        print("-" * 60)
        
        if not files_to_process:
            print("❌ 没有找到任何 .wwu 文件")
            return
        
        # 处理并输出
        file_mode = "a" if append else "w"
        
        with open(output_file, file_mode, encoding="utf-8") as f_out:
            for idx, file_path in enumerate(files_to_process, 1):
                self.run_stats["total_files"] += 1
                self.run_stats["processed_files"].append(os.path.basename(file_path))
                
                print(f"   [{idx}/{len(files_to_process)}] 处理: {os.path.basename(file_path)}", end="")
                
                try:
                    blocks = self.compiler.compile_file_to_blocks(file_path)
                    
                    block_count = 0
                    for block in blocks:
                        dsl_code = "\n".join(block["dsl_lines"])
                        
                        # 更新复杂度分布
                        self.run_stats["complexity_dist"][block["complexity"]] += 1
                        
                        data_row = {
                            "instruction": "",  # 待 Instruction Generator 填充
                            "input": "",
                            "output": dsl_code,
                            "meta": {
                                "source": block["source_file"],
                                "root_type": block["root_type"],
                                "root_name": block["root_name"],
                                "line_count": len(block["dsl_lines"]),
                                "depth": block["depth"],
                                "complexity": block["complexity"],
                                "commands": block["command_counts"]
                            }
                        }
                        
                        f_out.write(json.dumps(data_row, ensure_ascii=False) + "\n")
                        self.run_stats["total_blocks"] += 1
                        block_count += 1
                    
                    print(f" -> {block_count} 个样本")
                    
                except Exception as e:
                    print(f" -> ❌ 错误: {str(e)}")

        self._print_summary(output_file)

    def _print_summary(self, output_file: str):
        """打印处理摘要"""
        duration = (datetime.now() - self.run_stats["start_time"]).total_seconds()
        
        print("\n" + "=" * 50)
        print("📊 Reverse Compilation Report")
        print("=" * 50)
        print(f"Files Processed:    {self.run_stats['total_files']}")
        print(f"Blocks Extracted:   {self.run_stats['total_blocks']}")
        print(f"Duration:           {duration:.2f}s")
        print("-" * 50)
        print("Complexity Distribution:")
        for level, count in self.run_stats["complexity_dist"].items():
            pct = count / max(1, self.run_stats["total_blocks"]) * 100
            print(f"  {level:10}: {count:5} ({pct:.1f}%)")
        print("-" * 50)
        print("Compiler Stats:")
        stats = self.compiler.get_stats()
        for key, val in stats.items():
            print(f"  {key:20}: {val}")
        print("=" * 50)
        print(f"💾 Saved to: {output_file}")


# =============================================================================
# 命令行入口
# =============================================================================
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Wwise 逆向工程核心 V3.2 - 批量将 .wwu 文件转换为 DSL 训练数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 单个文件
  python reverse_compiler.py Actor-Mixer.wwu
  
  # 多个文件
  python reverse_compiler.py SFX.wwu Music.wwu VO.wwu -o combined.jsonl
  
  # 整个目录
  python reverse_compiler.py "C:/Wwise Project/Actor-Mixer Hierarchy"
  
  # 多个目录 + 追加模式
  python reverse_compiler.py ./SFX ./Music -o dataset.jsonl --append
  
  # 交互模式 (拖拽多个文件)
  python reverse_compiler.py --interactive
        """
    )
    
    parser.add_argument(
        "paths", 
        nargs="*", 
        help="一个或多个 .wwu 文件路径或目录路径"
    )
    parser.add_argument(
        "-o", "--output", 
        default="wwise_reverse_dataset.jsonl",
        help="输出 JSONL 文件路径 (默认: wwise_reverse_dataset.jsonl)"
    )
    parser.add_argument(
        "-a", "--append", 
        action="store_true",
        help="追加模式:将结果追加到现有文件而不是覆盖"
    )
    parser.add_argument(
        "-i", "--interactive", 
        action="store_true",
        help="交互模式:手动输入或拖拽文件路径"
    )
    
    args = parser.parse_args()
    
    analyzer = WwiseProjectAnalyzerV3()
    
    if args.interactive or not args.paths:
        # 交互模式
        print("=" * 60)
        print("🎮 Wwise 逆向工程核心 V3.2 - 交互模式")
        print("=" * 60)
        print("请输入 .wwu 文件或目录路径")
        print("  - 支持拖拽文件到此窗口")
        print("  - 每行一个路径")
        print("  - 输入 'done' 或按两次回车结束输入")
        print("-" * 60)
        
        paths = []
        empty_count = 0
        
        while True:
            try:
                line = input(f"[{len(paths)+1}] 路径: ").strip()
                
                # 检测结束条件
                if line.lower() == 'done':
                    break
                    
                if not line:
                    empty_count += 1
                    if empty_count >= 2 or (empty_count >= 1 and paths):
                        break
                    if not paths:
                        print("   💡 请至少输入一个路径,或输入 'done' 退出")
                    continue
                else:
                    empty_count = 0
                
                # 清理路径(去除拖拽时可能带的引号)
                line = line.strip('"').strip("'")
                paths.append(line)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n\n❌ 用户取消")
                sys.exit(0)
        
        if not paths:
            print("❌ 未输入任何路径")
            sys.exit(1)
        
        # 显示已添加的路径
        print("\n" + "-" * 60)
        print(f"📋 已添加 {len(paths)} 个路径:")
        for i, p in enumerate(paths, 1):
            print(f"   {i}. {p}")
        print("-" * 60)
        
        # 询问输出文件
        output_default = args.output
        output_input = input(f"\n📁 输出文件名 [{output_default}]: ").strip()
        output_file = output_input if output_input else output_default
        
        # 询问是否追加
        append_mode = False
        if os.path.exists(output_file):
            append_input = input(f"⚠️  文件 {output_file} 已存在,追加(a) 还是 覆盖(o)? [a/O]: ").strip().lower()
            append_mode = append_input == 'a'
        
        # 最终确认
        print("\n" + "=" * 60)
        print("📝 确认配置:")
        print(f"   输入: {len(paths)} 个路径")
        print(f"   输出: {output_file}")
        print(f"   模式: {'追加' if append_mode else '覆盖'}")
        print("=" * 60)
        
        confirm = input("\n▶️  按回车开始运行,输入 'q' 取消: ").strip().lower()
        if confirm == 'q':
            print("❌ 用户取消")
            sys.exit(0)
        
        print()  # 空行
        analyzer.generate_dataset_multi(paths, output_file, append=append_mode)
    else:
        # 命令行模式
        analyzer.generate_dataset_multi(args.paths, args.output, append=args.append)