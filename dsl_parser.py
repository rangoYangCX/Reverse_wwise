# -*- coding: utf-8 -*-
"""
[逻辑引擎]DSL 解析器 (V7.2 - 父子同名修复版)
功能:将 DSL (Domain Specific Language) 翻译为 WAAPI JSON 执行计划。
维护者:NeuroWwise Architecture Team

版本历史:
V7.2:   [Critical Fix] 修复父子同名问题 - 优先返回容器类型作为父对象
        [Fix] _resolve_via_registry 和 get_guid 都增加容器优先逻辑

V7.0:   [Feat] 新增 ADD_ACTION 语法 (Play/Stop/Pause/Resume/SetSwitch/SetState)
        [Feat] 新增 IMPORT_AUDIO 语法 (音频资源导入)
        [Feat] 新增 SET_RTPC_CURVE 语法 (RTPC 曲线设置)
        [Feat] 新增 COPY / MOVE / DELETE 语法 (对象操作)
        [Fix] 增强错误诊断信息
        [Compat] 完全向后兼容 V6.5 及以下版本

V6.5:   [Fix] 物理文件夹穿透 (Physical Folder Penetration)。
V6.4:   [Fix] 智能降级策略 (Smart Downgrade)。
V6.3:   [Fix] 针对 WorkUnit 创建,将 onNameConflict 策略改为 "rename"。
V6.1:   [Fix] Attenuation 属性修正 (OverridePositioning)。
V6.0:   [Feat] Registry 协同完全体。
"""
import re
import json

class DSLParser:
    def __init__(self):
        self.registry = None  # [V6.0] 外部注入的注册表引用
        self.parse_errors = []  # [V7.0 New] 解析错误收集
        self.parse_warnings = []  # [V7.0 New] 解析警告收集

        # ==========================================================
        # 1. 引用映射表 (Reference Mapping)
        # 将 DSL 中的简写映射为 Wwise 内部的 Reference Name
        # ==========================================================
        self.ref_map = {
            "OutputBus": "OutputBus",
            "Bus": "OutputBus",  # Alias: 常用别名
            "Target": "Target",  # Action 的目标
            "SwitchGroupOrStateGroup": "SwitchGroupOrStateGroup",
            "SwitchGroup": "SwitchGroupOrStateGroup",  # Alias
            "StateGroup": "StateGroup",
            "Attenuation": "Attenuation",
            "Effect0": "Effect0",
            "Effect1": "Effect1",
            "Effect2": "Effect2",
            "Effect3": "Effect3",
            "GameParameter": "GameParameter",
            "Conversion": "Conversion",
            "UserAuxSend0": "UserAuxSend0",
            "UserAuxSend1": "UserAuxSend1"
        }
        
        # ==========================================================
        # 2. 类型纠错表 (Type Correction)
        # 将 LLM 可能生成的各种非标准写法统一为 Wwise Type ID
        # ==========================================================
        self.type_fix = {
            # 容器类
            "Actor-Mixer": "ActorMixer",
            "ActorMixer": "ActorMixer",
            "Random Sequence Container": "RandomSequenceContainer",
            "RandomSequenceContainer": "RandomSequenceContainer",
            "RandomContainer": "RandomSequenceContainer",  # [V7.0] 新增别名
            "SequenceContainer": "RandomSequenceContainer",  # [V7.0] 新增别名
            "Switch Container": "SwitchContainer",
            "SwitchContainer": "SwitchContainer",
            "Blend Container": "BlendContainer",
            "BlendContainer": "BlendContainer",
            "Folder": "Folder",
            
            # 逻辑类
            "Switch Group": "SwitchGroup",
            "SwitchGroup": "SwitchGroup",
            "State Group": "StateGroup",
            "StateGroup": "StateGroup",
            "Game Parameter": "GameParameter",
            "GameParameter": "GameParameter",
            "RTPC": "GameParameter",  # [V7.0] 新增别名
            "Work Unit": "WorkUnit",
            "WorkUnit": "WorkUnit",
            
            # 核心资源
            "Event": "Event",
            "Sound": "Sound",
            "SoundSFX": "Sound",  # [V7.0] 新增别名
            "SoundVoice": "Sound",  # [V7.0] 新增别名 (Wwise 实际用 Sound)
            "Bus": "Bus",
            "AudioBus": "Bus",  # [V7.0] 新增别名
            "Aux Bus": "AuxBus",
            "AuxBus": "AuxBus",
            "AuxiliaryBus": "AuxBus",  # [V7.0] 新增别名
            "Action": "Action",
            
            # 效果与参数
            "Effect": "Effect",
            "AcousticTexture": "AcousticTexture",
            "Attenuation": "Attenuation"
        }
        
        # ==========================================================
        # 3. [V7.0 New] Action 类型映射表
        # ==========================================================
        self.action_types = {
            "play": 1,
            "stop": 2,
            "pause": 3,
            "resume": 4,
            "break": 5,
            "seek": 6,
            "setswitch": 19,
            "setstate": 18,
            "setgameparameter": 17,
            "resetgameparameter": 20,
            "mute": 7,
            "unmute": 8,
        }

    def set_registry(self, registry):
        """ [V6.0] 注入 Registry 实例,用于增强路径解析能力 """
        self.registry = registry

    def parse(self, dsl_lines):
        """
        [核心解析函数]
        输入: DSL 代码列表 (list of strings)
        输出: WAAPI 执行计划 (list of dicts)
        """
        plan = []
        self.parse_errors = []
        self.parse_warnings = []
        
        for line_idx, line in enumerate(dsl_lines):
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            
            # [V7.0] 清洗行号前缀 (LLM 可能生成 "1. CREATE..." 格式)
            line = re.sub(r'^\d+\.\s*', '', line)
                
            try:
                parsed = self._parse_single_line(line, line_idx, plan)
                if parsed:
                    plan.extend(parsed)
            except Exception as e:
                self.parse_errors.append(f"Line {line_idx+1}: {str(e)}")

        return plan

    def _parse_single_line(self, line, line_idx, current_plan):
        """
        [V7.0 Refactored] 解析单行 DSL,返回生成的 plan 步骤列表
        """
        steps = []
        
        # ------------------------------------------------------
        # 指令 1: CREATE (创建对象)
        # 语法: CREATE [Type] "Name" UNDER "Parent"
        # ------------------------------------------------------
        match_create = re.match(r'CREATE\s+(\w+[\-\w\s]*)\s+"([^"]+)"\s+UNDER\s+"([^"]+)"', line, re.IGNORECASE)
        if match_create:
            raw_type, name, raw_parent = match_create.groups()
            raw_type = raw_type.strip()
            return self._handle_create(raw_type, name, raw_parent, current_plan)

        # ------------------------------------------------------
        # 指令 2: SET_PROP (设置属性)
        # 语法: SET_PROP "Object" "Prop" = Value
        # ------------------------------------------------------
        match_set = re.match(r'SET_PROP\s+"([^"]+)"\s+"([^"]+)"\s*=\s*(.+)', line, re.IGNORECASE)
        if match_set:
            obj_name, prop, val = match_set.groups()
            val = self._parse_val(val)
            return [{
                "action": "ak.wwise.core.object.setProperty",
                "args": {
                    "object": obj_name,
                    "property": prop,
                    "value": val
                }
            }]

        # ------------------------------------------------------
        # 指令 3: LINK (建立引用/路由)
        # 语法: LINK "Child" TO "Target" AS "Type"
        # ------------------------------------------------------
        match_link = re.match(r'LINK\s+"([^"]+)"\s+TO\s+"([^"]+)"\s+AS\s+"([^"]+)"', line, re.IGNORECASE)
        if match_link:
            child, target, link_type = match_link.groups()
            return self._handle_link(child, target, link_type)

        # ------------------------------------------------------
        # 指令 4: ASSIGN (Switch/State 赋值) [V5.7]
        # 语法: ASSIGN "ChildObject" TO "SwitchState"
        # ------------------------------------------------------
        match_assign = re.match(r'ASSIGN\s+"([^"]+)"\s+TO\s+"([^"]+)"', line, re.IGNORECASE)
        if match_assign:
            child, state = match_assign.groups()
            return [{
                "action": "ak.wwise.core.switchContainer.addAssignment",
                "args": {
                    "child": child,
                    "stateOrSwitch": state
                }
            }]

        # ------------------------------------------------------
        # 指令 5: ADD_ACTION (事件动作) [V7.0 New]
        # 语法: ADD_ACTION "EventName" [ActionType] "Target"
        # ActionType: PLAY, STOP, PAUSE, RESUME, SETSWITCH, SETSTATE
        # ------------------------------------------------------
        match_action = re.match(r'ADD_ACTION\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"(?:\s+"([^"]+)")?', line, re.IGNORECASE)
        if match_action:
            event_name, action_type, target, extra = match_action.groups()
            return self._handle_add_action(event_name, action_type.lower(), target, extra)

        # ------------------------------------------------------
        # 指令 6: CREATE_EVENT (事件宏指令) [Legacy + Enhanced]
        # 语法: CREATE_EVENT "EventName" PLAY "SoundName"
        #       CREATE_EVENT "EventName" UNDER "Parent" PLAY "SoundName"
        # ------------------------------------------------------
        match_event = re.match(r'CREATE_EVENT\s+"([^"]+)"(?:\s+UNDER\s+"([^"]+)")?\s+PLAY\s+"([^"]+)"', line, re.IGNORECASE)
        if match_event:
            event_name, parent, target = match_event.groups()
            parent = parent or "Default Work Unit"
            return self._handle_create_event(event_name, parent, target)

        # ------------------------------------------------------
        # 指令 7: IMPORT_AUDIO (音频导入) [V7.0 New]
        # 语法: IMPORT_AUDIO "FilePath" INTO "Parent" AS "SoundName"
        # ------------------------------------------------------
        match_import = re.match(r'IMPORT_AUDIO\s+"([^"]+)"\s+INTO\s+"([^"]+)"(?:\s+AS\s+"([^"]+)")?', line, re.IGNORECASE)
        if match_import:
            file_path, parent, sound_name = match_import.groups()
            return self._handle_import_audio(file_path, parent, sound_name)

        # ------------------------------------------------------
        # 指令 8: SET_RTPC_CURVE (RTPC 曲线设置) [V7.0 New]
        # 语法: SET_RTPC_CURVE "Object" "GameParameter" "Property" POINTS [(x1,y1), (x2,y2)]
        # ------------------------------------------------------
        match_rtpc = re.match(r'SET_RTPC_CURVE\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]+)"\s+POINTS\s+\[(.+)\]', line, re.IGNORECASE)
        if match_rtpc:
            obj, param, prop, points_str = match_rtpc.groups()
            return self._handle_rtpc_curve(obj, param, prop, points_str)

        # ------------------------------------------------------
        # 指令 9: DELETE (删除对象) [V7.0 New]
        # 语法: DELETE "ObjectName"
        # ------------------------------------------------------
        match_delete = re.match(r'DELETE\s+"([^"]+)"', line, re.IGNORECASE)
        if match_delete:
            obj_name = match_delete.group(1)
            return [{
                "action": "ak.wwise.core.object.delete",
                "args": {"object": obj_name}
            }]

        # ------------------------------------------------------
        # 指令 10: COPY (复制对象) [V7.0 New]
        # 语法: COPY "Source" TO "Parent" AS "NewName"
        # ------------------------------------------------------
        match_copy = re.match(r'COPY\s+"([^"]+)"\s+TO\s+"([^"]+)"\s+AS\s+"([^"]+)"', line, re.IGNORECASE)
        if match_copy:
            source, parent, new_name = match_copy.groups()
            return [{
                "action": "ak.wwise.core.object.copy",
                "args": {
                    "object": source,
                    "parent": parent,
                    "onNameConflict": "rename"
                },
                "options": {"return": ["name", "id"]}
            }]

        # ------------------------------------------------------
        # 指令 11: MOVE (移动对象) [V7.0 New]
        # 语法: MOVE "Object" TO "NewParent"
        # ------------------------------------------------------
        match_move = re.match(r'MOVE\s+"([^"]+)"\s+TO\s+"([^"]+)"', line, re.IGNORECASE)
        if match_move:
            obj, new_parent = match_move.groups()
            return [{
                "action": "ak.wwise.core.object.move",
                "args": {
                    "object": obj,
                    "parent": new_parent,
                    "onNameConflict": "rename"
                }
            }]

        # ------------------------------------------------------
        # 指令 12: RENAME (重命名) [V7.0 Enhanced]
        # 语法: RENAME "OldName" TO "NewName"
        # ------------------------------------------------------
        match_rename = re.match(r'RENAME\s+"([^"]+)"\s+TO\s+"([^"]+)"', line, re.IGNORECASE)
        if match_rename:
            old_name, new_name = match_rename.groups()
            return [{
                "action": "ak.wwise.core.object.setName",
                "args": {
                    "object": old_name,
                    "value": new_name
                }
            }]

        # ------------------------------------------------------
        # 容错处理:未知指令
        # ------------------------------------------------------
        if line and not line.startswith(('<', '>', '```', '---', '===')):
            self.parse_warnings.append(f"Unrecognized instruction: {line[:50]}...")
        
        return []

    def _handle_create(self, raw_type, name, raw_parent, current_plan):
        """处理 CREATE 指令"""
        steps = []
        
        # 1.1 类型标准化
        obj_type = self.type_fix.get(raw_type, raw_type)
        
        # 1.2 路径/父级 智能解析 (核心导航逻辑)
        parent = self._resolve_parent_strategy(raw_parent, obj_type)

        # 1.3 [V6.0] Registry 协同消歧 + 类型精确制导兜底
        if not parent.startswith(("\\", "$", "{")):
            resolved_path = self._resolve_via_registry(parent, obj_type)
            if resolved_path:
                parent = resolved_path
            else:
                valid_types_str = self._get_valid_parent_types(obj_type)
                if valid_types_str:
                    parent = f'$ from type {valid_types_str} where name="{parent}"'

        # ==========================================================
        # [V6.5] 物理文件夹防御 (Physical Folder Defense)
        # ==========================================================
        asset_types = ["ActorMixer", "Sound", "RandomSequenceContainer", "SwitchContainer", "BlendContainer"]
        
        if obj_type in asset_types and self.registry:
            parent_guid = parent
            if not parent.startswith("{"):
                # [V7.2 Fix] 使用 prefer_container=True 解决父子同名问题
                parent_guid = self.registry.get_guid(parent, prefer_container=True) if self.registry else None
            
            if parent_guid and hasattr(self.registry, 'is_physical_folder') and self.registry.is_physical_folder(parent_guid):
                wu_name = f"{raw_parent}_Content"
                
                steps.append({
                    "action": "ak.wwise.core.object.create",
                    "args": {
                        "type": "WorkUnit",
                        "name": wu_name,
                        "parent": parent_guid,
                        "onNameConflict": "merge"
                    }
                })
                
                parent_path = self.registry.get_path_by_guid(parent_guid)
                if parent_path:
                    parent = f"{parent_path}\\{wu_name}"
                else:
                    parent = f'$ from type WorkUnit where name="{wu_name}"'

        # [V6.4] 智能降级策略 (Smart Downgrade to Actor-Mixer)
        if obj_type == "WorkUnit":
            is_guid_parent = parent.startswith("{")
            is_deep_hierarchy = "\\actor-mixer hierarchy\\" in parent.lower()
            
            if is_guid_parent or is_deep_hierarchy:
                obj_type = "ActorMixer"

        # [V6.3] WorkUnit 文件冲突防御
        conflict_strategy = "merge"
        if obj_type == "WorkUnit":
            conflict_strategy = "rename"

        # 构建执行块
        steps.append({
            "action": "ak.wwise.core.object.create",
            "args": {
                "type": obj_type,
                "name": name,
                "parent": parent,
                "onNameConflict": conflict_strategy
            }
        })
        
        return steps

    def _handle_link(self, child, target, link_type):
        """处理 LINK 指令"""
        steps = []
        
        # 映射引用类型 (例如 "Bus" -> "OutputBus")
        w_ref = self.ref_map.get(link_type, link_type)
        
        # ==========================================================
        # [V7.1 Fix] LINK 目标的智能解析
        # 重要:setReference 不支持 WAQL！只支持 GUID/Path/Name
        # 策略:
        # 1. 如果是 GUID 或绝对路径,直接使用
        # 2. 如果是名称,尝试通过 Registry 解析为路径
        # 3. 如果 Registry 找不到,保留名称(让 Driver 去查找)
        # ==========================================================
        
        resolved_target = target
        
        if not target.startswith(("\\", "{", "$")):
            # 尝试通过 Registry 解析
            if self.registry:
                # 根据引用类型,确定目标层级
                target_hierarchy = None
                if w_ref == "OutputBus":
                    target_hierarchy = "Master-Mixer Hierarchy"
                elif w_ref == "Attenuation":
                    target_hierarchy = "Attenuations"
                elif w_ref in ["UserAuxSend0", "UserAuxSend1"]:
                    target_hierarchy = "Master-Mixer Hierarchy"
                elif w_ref == "SwitchGroupOrStateGroup":
                    target_hierarchy = "Switches"  # 优先 Switches
                elif w_ref == "StateGroup":
                    target_hierarchy = "States"
                elif w_ref == "GameParameter":
                    target_hierarchy = "Game Parameters"
                
                # 查找匹配的路径
                found_path = self._find_reference_path(target, target_hierarchy)
                if found_path:
                    resolved_target = found_path
                # 如果找不到,保留原始名称(Driver 会尝试查找)

        # [V5.6] 自动处理 OutputBus 的 Override 逻辑
        if w_ref == "OutputBus":
            steps.append({
                "action": "ak.wwise.core.object.setProperty",
                "args": {
                    "object": child,
                    "property": "OverrideOutput",
                    "value": True
                }
            })

        # [V6.1] 自动处理 Attenuation 的 Override 逻辑
        if w_ref == "Attenuation":
            steps.append({
                "action": "ak.wwise.core.object.setProperty",
                "args": {
                    "object": child,
                    "property": "OverridePositioning",
                    "value": True
                }
            })

        steps.append({
            "action": "ak.wwise.core.object.setReference",
            "args": {
                "object": child,
                "reference": w_ref,
                "value": resolved_target
            }
        })
        
        return steps

    def _find_reference_path(self, name: str, hierarchy_hint: str = None) -> str:
        """
        [V7.1 New] 通过 Registry 查找引用目标的路径
        
        Args:
            name: 目标名称
            hierarchy_hint: 层级提示 (如 "Master-Mixer Hierarchy")
        
        Returns:
            找到的路径,或 None
        """
        if not self.registry:
            return None
        
        # 从 Registry 获取候选路径
        candidates = self.registry.name_index.get(name, [])
        
        if not candidates:
            return None
        
        # 如果有层级提示,优先匹配
        if hierarchy_hint:
            for path in candidates:
                if hierarchy_hint in path:
                    return path
        
        # 没有提示或没找到匹配,返回第一个
        return candidates[0] if candidates else None

    def _handle_add_action(self, event_name, action_type, target, extra=None):
        """[V7.0 New] 处理 ADD_ACTION 指令"""
        steps = []
        
        # 获取 action type ID
        action_type_id = self.action_types.get(action_type, 1)  # 默认 Play
        
        # 构建 action 创建参数
        action_args = {
            "parent": event_name,
            "type": "Action",
            "name": "",  # Wwise 会自动命名
            "onNameConflict": "merge",
            "@ActionType": action_type_id,
            "@Target": target
        }
        
        # 特殊处理 SetSwitch/SetState
        if action_type == "setswitch" and extra:
            action_args["@SwitchValue"] = extra
        elif action_type == "setstate" and extra:
            action_args["@StateValue"] = extra
        
        steps.append({
            "action": "ak.wwise.core.object.create",
            "args": action_args
        })
        
        return steps

    def _handle_create_event(self, event_name, parent, target):
        """[V7.0 Enhanced] 处理 CREATE_EVENT 宏指令"""
        steps = []
        
        # 1. 解析父级
        event_parent = self._resolve_parent_strategy(parent, "Event")
        
        # 2. 创建 Event
        steps.append({
            "action": "ak.wwise.core.object.create",
            "args": {
                "type": "Event",
                "name": event_name,
                "parent": event_parent,
                "onNameConflict": "merge"
            }
        })
        
        # 3. 创建 Play Action
        # 注意:Wwise Event 的 Action 是特殊结构
        # 使用 setReference 来设置 Target 可能更可靠
        # 这里简化处理,实际可能需要更复杂的 API 调用
        steps.append({
            "action": "ak.wwise.core.object.create",
            "args": {
                "parent": event_name,  # 使用 event name 作为父级
                "type": "Action",
                "name": "",
                "onNameConflict": "merge",
                "@ActionType": 1,  # Play
                "@Target": target
            }
        })
        
        return steps

    def _handle_import_audio(self, file_path, parent, sound_name=None):
        """[V7.0 New] 处理 IMPORT_AUDIO 指令"""
        import os
        
        # 如果没有指定名称,从文件路径提取
        if not sound_name:
            sound_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 解析父级
        parent_resolved = self._resolve_parent_strategy(parent, "Sound")
        
        return [{
            "action": "ak.wwise.core.audio.import",
            "args": {
                "importOperation": "useExisting",
                "default": {
                    "importLanguage": "SFX"
                },
                "imports": [{
                    "audioFile": file_path,
                    "objectPath": f"<Sound>{sound_name}",
                    "parent": parent_resolved
                }]
            }
        }]

    def _handle_rtpc_curve(self, obj, param, prop, points_str):
        """[V7.0 New] 处理 SET_RTPC_CURVE 指令"""
        # 解析点集 "(x1,y1), (x2,y2)" -> [(x1,y1), (x2,y2)]
        points = []
        point_matches = re.findall(r'\(([^,]+),\s*([^)]+)\)', points_str)
        for x, y in point_matches:
            points.append({
                "x": float(x.strip()),
                "y": float(y.strip()),
                "shape": "Linear"
            })
        
        return [{
            "action": "ak.wwise.core.object.setAttenuationCurve",
            "args": {
                "object": obj,
                "curveType": prop,
                "use": param,
                "points": points
            }
        }]

    # ==========================================================
    # 辅助方法 (保持原有逻辑)
    # ==========================================================

    def _get_valid_parent_types(self, obj_type):
        """ [V6.0 Helper] 获取合法的父级类型白名单字符串 """
        am_child_types = ["ActorMixer", "Sound", "RandomSequenceContainer", "SwitchContainer", "BlendContainer", "Folder", "WorkUnit"]
        if obj_type in am_child_types:
            return "WorkUnit,Folder,ActorMixer,RandomSequenceContainer,SwitchContainer,BlendContainer"
        elif obj_type == "Event":
            return "WorkUnit,Folder"
        elif obj_type in ["Bus", "AuxBus"]:
            return "WorkUnit,Folder,Bus,AuxBus"
        elif obj_type == "GameParameter":
            return "WorkUnit,Folder"
        elif obj_type in ["SwitchGroup", "Switch"]:
            return "WorkUnit,Folder,SwitchGroup"
        elif obj_type in ["StateGroup", "State"]:
            return "WorkUnit,Folder,StateGroup"
        return None

    def _resolve_via_registry(self, name, obj_type):
        """
        [V6.0] 通过 Registry 查找最佳匹配路径
        [V7.2 Fix] 优先返回容器类型,解决父子同名问题
        """
        if not self.registry:
            return None
        
        candidates = self.registry.name_index.get(name, [])
        if not candidates:
            return None
            
        filtered = []
        target_hierarchy_keyword = ""
        
        if obj_type in ["ActorMixer", "Sound", "RandomSequenceContainer", "SwitchContainer", "BlendContainer"]:
            target_hierarchy_keyword = "Actor-Mixer Hierarchy"
        elif obj_type == "Event":
            target_hierarchy_keyword = "Events"
        elif obj_type in ["Bus", "AuxBus"]:
            target_hierarchy_keyword = "Master-Mixer Hierarchy"
        elif obj_type == "GameParameter":
            target_hierarchy_keyword = "Game Parameters"
        elif obj_type in ["SwitchGroup", "Switch"]:
            target_hierarchy_keyword = "Switches"
        elif obj_type in ["StateGroup", "State"]:
            target_hierarchy_keyword = "States"

        for path in candidates:
            if "Attenuations" in path:
                continue
            if target_hierarchy_keyword and target_hierarchy_keyword not in path:
                continue
            filtered.append(path)
            
        if len(filtered) == 1:
            return filtered[0]
        elif len(filtered) > 1:
            # [V7.2 Fix] 优先返回容器类型
            container_types = {
                "ActorMixer", "RandomSequenceContainer", "SwitchContainer", 
                "BlendContainer", "Folder", "WorkUnit", "Bus", "AuxBus"
            }
            
            # 从后往前找容器类型
            for path in reversed(filtered):
                guid = self.registry.path_map.get(path)
                if guid:
                    path_obj_type = self.registry.type_map.get(guid, "")
                    if path_obj_type in container_types:
                        return path
            
            # 如果没找到容器,返回第一个(最早创建的)
            return filtered[0]
        return None

    def _resolve_parent_strategy(self, p, child_type=""):
        """
        [路径导航仪](The Navigation Strategy)
        功能:解决 "Default Work Unit" 到底是在 Actor-Mixer 还是 Events 里的问题。
        """
        p_low = p.lower()
        child_type = self.type_fix.get(child_type, child_type)

        # --- 策略 A: 绝对路径 ---
        if p.startswith("\\"):
            return p
        
        # --- 策略 B: GUID ---
        if p.startswith("{") and p.endswith("}"):
            return p

        # --- 策略 C: 智能归位 ---
        if p_low == "default work unit" or p_low == "root":
            if child_type in ["Bus", "AuxBus"]: 
                return "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus"
            if child_type in ["SwitchGroup", "Switch"]:
                return "\\Switches\\Default Work Unit"
            if child_type in ["StateGroup", "State"]:
                return "\\States\\Default Work Unit"
            if child_type in ["GameParameter"]:
                return "\\Game Parameters\\Default Work Unit"
            if child_type in ["Event"]:
                return "\\Events\\Default Work Unit"
            if child_type in ["Effect", "AcousticTexture"]:
                return "\\Effects\\Default Work Unit"
            if child_type in ["Sound", "RandomSequenceContainer", "SwitchContainer", "BlendContainer", "ActorMixer", "Folder", "WorkUnit"]:
                return "\\Actor-Mixer Hierarchy\\Default Work Unit"
            return "\\Actor-Mixer Hierarchy\\Default Work Unit"

        # --- 策略 D: 显式层级名处理 ---
        if "master audio bus" in p_low or p_low == "master":
            return "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus"

        # --- 策略 E: 模糊匹配补全 ---
        if "actor-mixer" in p_low and "hierarchy" not in p_low:
            return "\\Actor-Mixer Hierarchy\\Default Work Unit"
        if p_low == "actor-mixer hierarchy":
            return "\\Actor-Mixer Hierarchy\\Default Work Unit"
        if p_low == "events" or ("event" in p_low and "hierarchy" not in p_low and "work unit" not in p_low):
            return "\\Events\\Default Work Unit"
        if p_low == "switches":
            return "\\Switches\\Default Work Unit"
        if p_low == "states":
            return "\\States\\Default Work Unit"
        if p_low == "master-mixer hierarchy":
            return "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus"
        if "attenuation" in p_low:
            return "\\Attenuations\\Default Work Unit"
        if "game parameter" in p_low or p_low == "game parameters":
            return "\\Game Parameters\\Default Work Unit"

        # --- 策略 F: AI 幻觉修正 ---
        if "ai_playplace" in p_low:
            return p.replace("AI_Playplace", "AI_Playground")

        # --- 策略 G: 双重保险 ---
        if child_type in ["Bus", "AuxBus"] and "default work unit" in p_low:
            return "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus"

        return p

    def _parse_val(self, v):
        """
        [数值清洗器]
        """
        s = str(v).strip()
        
        # 单位清洗 (V5.1)
        s = re.sub(r'\s*(dB|db|DB|%|cents|Cents|ms|s|Hz|hz)$', '', s)
        
        if s.lower() == "true": return True
        if s.lower() == "false": return False
        
        try:
            if "." in s: 
                return float(s)
            return int(s)
        except:
            pass
            
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
            
        return s

    def validate_plan(self, plan):
        """
        [计划校验器]
        """
        if not plan:
            return False, "Plan is empty"
        return True, "OK"
    
    def get_parse_diagnostics(self):
        """[V7.0 New] 获取解析诊断信息"""
        return {
            "errors": self.parse_errors,
            "warnings": self.parse_warnings
        }