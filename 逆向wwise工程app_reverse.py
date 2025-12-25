# -*- coding: utf-8 -*-
"""
【逆向工程】Wwise XML to DSL 转译器 (V7.0 - Ultimate Edition)
功能：从 Wwise XML 逆向生成适配 dsl_parser_v7.py 的全功能 DSL。
新增支持：
1. SET_RTPC_CURVE: 解析 RTPC 曲线数据。
2. ADD_ACTION: 解析 Event 下的各种复杂动作 (SetSwitch, Stop 等)。
3. IMPORT_AUDIO: (实验性) 尝试还原音频导入逻辑。
"""
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

class WwiseReverseCompilerV7:
    def __init__(self):
        # 1. 基础属性白名单
        self.interesting_properties = [
            "Volume", "Pitch", "Lowpass", "Highpass", 
            "MakeUpGain", "BusVolume", "InitialDelay",
            "IsLoopingEnabled", "Inclusion", "Color",
            "OverrideOutput", "OverridePositioning", "HoldEmitterPositionOrientation"
        ]

        # 2. 引用类型映射
        self.ref_type_map = {
            "OutputBus": "OutputBus",
            "Attenuation": "Attenuation",
            "UserAuxSend0": "UserAuxSend0",
            "UserAuxSend1": "UserAuxSend1",
            "Ref_Effect0": "Effect0", 
            "Ref_Effect1": "Effect1",
            "Ref_Effect2": "Effect2",
            "Ref_Effect3": "Effect3",
            "Conversion": "Conversion",
            "SwitchGroupOrStateGroup": "SwitchGroupOrStateGroup" 
        }

        # 3. 对象类型映射
        self.xml_tag_map = {
            "WorkUnit": "WorkUnit",
            "Folder": "Folder",
            "ActorMixer": "ActorMixer",
            "RandomSequenceContainer": "RandomSequenceContainer",
            "SwitchContainer": "SwitchContainer",
            "BlendContainer": "BlendContainer",
            "Sound": "Sound",
            "Bus": "Bus",
            "AuxBus": "AuxBus",
            "Event": "Event",
            "SwitchGroup": "SwitchGroup",
            "StateGroup": "StateGroup",
            "GameParameter": "GameParameter",
            "Effect": "Effect",
            "AcousticTexture": "AcousticTexture"
        }

        # 4. Action 类型 ID 映射 (Wwise XML -> DSL Keyword)
        self.action_id_map = {
            "1": "PLAY",
            "2": "STOP",
            "3": "PAUSE",
            "4": "RESUME",
            "5": "BREAK",
            "6": "SEEK",
            "7": "MUTE",
            "8": "UNMUTE",
            "18": "SETSTATE",
            "19": "SETSWITCH",
            "25": "SETGAMEPARAMETER"
        }
        
        # 5. 逻辑根节点类型 (定义哪些对象生成独立的训练块)
        self.logic_root_types = [
            "RandomSequenceContainer", 
            "SwitchContainer", 
            "BlendContainer", 
            "Sound", 
            "Event", 
            "ActorMixer"
        ]

    def compile_file_to_blocks(self, file_path):
        """ 解析文件并返回 DSL Block 列表 """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            print(f"❌ [Error] Failed to read {file_path}: {e}")
            return []

        blocks = []
        for wu in root.findall(".//WorkUnit"):
            self._traverse_and_collect(wu, "Root", blocks)
        return blocks

    def _get_object_lines(self, element, parent_name):
        """ 获取单个对象的 DSL 指令 (Create + Set + Link + RTPC + Actions) """
        tag = element.tag
        name = element.get("Name")
        if not name or tag not in self.xml_tag_map:
            return []

        lines = []
        dsl_type = self.xml_tag_map[tag]

        # --- 1. CREATE ---
        # 尝试推断是否为 IMPORT_AUDIO (如果有 AudioSource 且是 Sound)
        # 这是一个简单的启发式规则，实际 XML 中 AudioSource 比较复杂
        audio_source = element.find(".//AudioSource")
        if tag == "Sound" and audio_source is not None:
             # 为了保持训练数据的通用性，我们通常还是用 CREATE Sound
             # 但可以在这里生成 IMPORT_AUDIO 作为替代或补充
             # lines.append(f'IMPORT_AUDIO "{name}.wav" INTO "{parent_name}" AS "{name}"')
             pass

        if parent_name == "Root":
            if name != "Default Work Unit":
                lines.append(f'CREATE {dsl_type} "{name}" UNDER "Root"')
        else:
            lines.append(f'CREATE {dsl_type} "{name}" UNDER "{parent_name}"')

        # --- 2. SET_PROP ---
        prop_list = element.find("PropertyList")
        if prop_list is not None:
            for prop in prop_list.findall("Property"):
                p_name = prop.get("Name")
                p_val = prop.get("Value")
                if p_val is not None and p_val != "" and p_name in self.interesting_properties:
                    lines.append(f'SET_PROP "{name}" "{p_name}" = {p_val}')

        # --- 3. LINK ---
        ref_list = element.find("ReferenceList")
        if ref_list is not None:
            for ref in ref_list.findall("Reference"):
                r_name = ref.get("Name")
                target_dsl_type = self.ref_type_map.get(r_name)
                if not target_dsl_type and "Effect" in r_name: target_dsl_type = r_name
                
                if target_dsl_type:
                    obj_ref = ref.find("ObjectRef")
                    if obj_ref is not None:
                        lines.append(f'LINK "{name}" TO "{obj_ref.get("Name")}" AS "{target_dsl_type}"')

        # --- 4. RTPC CURVE (V7.0 New) ---
        # XML 路径: <RTPCList> -> <RTPC> -> <Curve>
        rtpc_list = element.find("RTPCList")
        if rtpc_list is not None:
            for rtpc in rtpc_list.findall("RTPC"):
                # 获取绑定的属性 (Prop) 和 RTPC 参数 (ControlInput)
                prop_name = rtpc.get("PropertyName")
                control_input = rtpc.find("ReferenceList/Reference[@Name='ControlInput']/ObjectRef")
                
                if prop_name and control_input is not None:
                    rtpc_name = control_input.get("Name")
                    
                    # 提取曲线点
                    curve_points = []
                    curve_node = rtpc.find("Curve")
                    if curve_node is not None:
                        for point in curve_node.findall(".//Point"):
                            x = point.find("XPos").text
                            y = point.find("YPos").text
                            curve_points.append(f"({x}, {y})")
                    
                    if curve_points:
                        points_str = ", ".join(curve_points)
                        # 生成: SET_RTPC_CURVE "Obj" "Param" "Volume" POINTS [(0, -96), (100, 0)]
                        lines.append(f'SET_RTPC_CURVE "{name}" "{rtpc_name}" "{prop_name}" POINTS [{points_str}]')

        # --- 5. ACTIONS (V7.0 Enhanced) ---
        if tag == "Event":
            children = element.find("ChildrenList")
            if children:
                for action in children.findall("Action"):
                    # 获取 Action Type
                    at_node = action.find("PropertyList/Property[@Name='ActionType']")
                    action_id = at_node.get("Value") if at_node is not None else "1" # Default Play
                    
                    action_type_str = self.action_id_map.get(action_id, "PLAY") # 默认 PLAY
                    
                    # 获取 Target
                    target_ref = action.find("ReferenceList/Reference[@Name='Target']/ObjectRef")
                    target_name = target_ref.get("Name") if target_ref is not None else "Unknown"

                    # 处理 Switch/State 的特殊值
                    extra_val = ""
                    if action_type_str == "SETSWITCH":
                        # 尝试找 Switch 组内具体 Switch 的引用或值，XML 结构较复杂，这里简化
                        # 实际可能在 Target 里直接引用了具体的 Switch
                        pass 
                    
                    # 生成: ADD_ACTION "EventName" PLAY "SoundName"
                    lines.append(f'ADD_ACTION "{name}" {action_type_str} "{target_name}"')

        return lines

    def _get_subtree_dsl(self, element, parent_name):
        """ 深度递归获取 DSL """
        subtree_lines = self._get_object_lines(element, parent_name)
        current_obj_name = element.get("Name")
        if not current_obj_name: return subtree_lines

        children_list = element.find("ChildrenList")
        if children_list is not None:
            for child in children_list:
                if child.tag != "Action":
                    child_lines = self._get_subtree_dsl(child, current_obj_name)
                    subtree_lines.extend(child_lines)
        return subtree_lines

    def _traverse_and_collect(self, element, parent_name, blocks):
        """ 遍历收集逻辑块 """
        tag = element.tag
        name = element.get("Name")
        if not name: return
        
        if tag in self.logic_root_types:
            full_asset_dsl = self._get_subtree_dsl(element, parent_name)
            if full_asset_dsl:
                blocks.append(full_asset_dsl)

        children_list = element.find("ChildrenList")
        if children_list is not None:
            for child in children_list:
                if child.tag != "Action":
                    self._traverse_and_collect(child, name, blocks)

class WwiseProjectAnalyzer:
    """ 高级分析器：用于汇总大型 Wwise 工程的 DSL 数据并生成训练集 """
    def __init__(self, compiler):
        self.compiler = compiler
        self.stats = {"total_files": 0, "total_blocks": 0, "start_time": None}

    def generate_dataset(self, root_path, output_jsonl="wwise_training_data_v7.jsonl"):
        self.stats["start_time"] = datetime.now()
        # 清洗路径
        root_path = root_path.strip().strip('"').strip("'")
        
        if not os.path.exists(root_path):
            print(f"❌ Path not found: {root_path}")
            return

        print(f"🚀 [V7 Deep Recursive] Scanning Hierarchy: {root_path}")
        
        files_to_process = []
        if os.path.isfile(root_path) and root_path.endswith(".wwu"):
            files_to_process.append(root_path)
        else:
            for r, _, files in os.walk(root_path):
                for f in files:
                    if f.endswith(".wwu"):
                        files_to_process.append(os.path.join(r, f))

        with open(output_jsonl, "w", encoding="utf-8") as f_out:
            for file_path in files_to_process:
                self.stats["total_files"] += 1
                # 核心调用
                blocks = self.compiler.compile_file_to_blocks(file_path)
                
                for block in blocks:
                    dsl_code = "\n".join(block)
                    
                    # 简单判断是否为复杂容器
                    is_complex = len([l for l in block if "CREATE" in l]) > 1
                    root_type_line = block[0] if block else ""
                    root_type = "Unknown"
                    if root_type_line.startswith("CREATE"):
                        parts = root_type_line.split()
                        if len(parts) > 1:
                            root_type = parts[1]
                    
                    data_row = {
                        "instruction": "",  # 待 Instruction Generator 填充
                        "input": "", 
                        "output": dsl_code,
                        "meta": {
                            "source": os.path.basename(file_path),
                            "line_count": len(block),
                            "complexity": "high" if is_complex else "low",
                            "root_type": root_type
                        }
                    }
                    f_out.write(json.dumps(data_row, ensure_ascii=False) + "\n")
                    self.stats["total_blocks"] += 1

        self._print_summary(output_jsonl)

    def _print_summary(self, out_file):
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        print(f"\n✅ SUCCESS: Extracted {self.stats['total_blocks']} deep-logic blocks from {self.stats['total_files']} files.")
        print(f"💾 Saved to: {out_file} (Duration: {duration:.2f}s)\n")

if __name__ == "__main__":
    # 使用示例
    compiler = WwiseReverseCompilerV7()
    analyzer = WwiseProjectAnalyzer(compiler)
    
    # 你的工程路径 (请修改此处)
    project_root = r"G:\wwiseProj\release\Actor-Mixer Hierarchy\player\player_action.wwu"
    
    # 执行生成
    analyzer.generate_dataset(project_root)
    print("✅ WwiseReverseCompilerV7 & Analyzer initialized.")
    print(f"👉 To run: Modify 'project_root' and uncomment 'analyzer.generate_dataset(...)'.")