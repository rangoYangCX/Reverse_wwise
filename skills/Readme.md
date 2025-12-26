# NeuroWwise - Wwise DSL 逆向工程工具链

## 简介

NeuroWwise 是一套完整的 Wwise 音频工程逆向工具链,用于:
- 将 Wwise 工程文件 (.wwu) 逆向转换为 DSL 代码
- 生成 AI 训练数据
- 通过 DSL 控制 Wwise(创建、修改音频结构)

## 核心组件版本

| 组件 | 版本 | 说明 |
|------|------|------|
| Reverse Compiler | **V3.2** | WWU → DSL 逆向编译 |
| DSL Parser | **V7.2** | DSL → WAAPI 执行计划 |
| Registry | **V8.2** | 对象 GUID 注册与查找 |
| Instruction Generator | **V1.0** | 自然语言指令生成 |
| DSL Fission | **V1.0** | 样本裂变扩充 |

## 快速开始

### 1. 逆向编译 WWU 文件

```bash
# 单个文件
python tools/reverse_compiler.py Actor-Mixer.wwu -o dataset.jsonl

# 整个目录
python tools/reverse_compiler.py "D:/WwiseProject/Actor-Mixer Hierarchy" -o dataset.jsonl

# 交互模式(拖拽文件)
python tools/reverse_compiler.py --interactive
```

### 2. 后处理修复

生成的数据需要修复子样本的 UNDER 引用:

```python
import json

# 读取数据
samples = []
with open('dataset.jsonl', 'r') as f:
    for line in f:
        samples.append(json.loads(line))

# 收集所有样本根名称
root_names = {s['meta']['root_name'] for s in samples}

# 修复 UNDER 引用
for s in samples:
    lines = s['output'].split('\n')
    first_line = lines[0]
    
    if 'UNDER "' in first_line:
        start = first_line.find('UNDER "') + 7
        end = first_line.find('"', start)
        parent = first_line[start:end]
        
        if parent in root_names:
            lines[0] = first_line[:start] + "Default Work Unit" + first_line[end:]
            s['output'] = '\n'.join(lines)

# 保存修复后的数据
with open('dataset_fixed.jsonl', 'w') as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
```

### 3. 生成训练指令

```bash
python tools/instruction_generator.py dataset_fixed.jsonl training_data.jsonl
```

### 4. 样本裂变(可选)

```bash
# 扩充到 10000 样本
python tools/dsl_fission.py training_data.jsonl expanded.jsonl --target 10000 --level simple
```

## DSL 语法示例

```dsl
# 创建容器
CREATE RandomSequenceContainer "PlayerAttack" UNDER "Default Work Unit"

# 设置属性
SET_PROP "PlayerAttack" "RandomAvoidRepeating" = True
SET_PROP "PlayerAttack" "Volume" = -3

# 建立引用
LINK "PlayerAttack" TO "player_skill" AS "Attenuation"
LINK "PlayerAttack" TO "HostPlayerSkill" AS "Bus"

# 创建子对象
CREATE Sound "Attack_01" UNDER "PlayerAttack"
CREATE Sound "Attack_02" UNDER "PlayerAttack"
```

## 目录结构

```
neurowwise_v9/
├── src/
│   ├── app.py              # Streamlit 主应用
│   ├── dsl_parser.py       # DSL 解析器 V7.2
│   ├── registry.py         # 对象注册表 V8.2
│   ├── waapi_driver.py     # WAAPI 驱动
│   └── neuro_core.py       # 核心代理
│
├── tools/
│   ├── reverse_compiler.py      # 逆向编译器 V3.2
│   ├── instruction_generator.py # 指令生成器 V1.0
│   ├── dsl_fission.py          # 样本裂变器 V1.0
│   └── batch_dsl_verifier.py   # 批量验证器
│
├── SKILL.md                # 完整技能文档
└── README.md               # 本文件
```

## 已知问题与修复

### 父子同名问题 (V7.2/V8.2 已修复)

**问题**: 当父对象和子对象同名时,执行报错 `Sound can't be child of Sound`

**原因**: Registry 返回了最后创建的对象(Sound)而非父容器

**修复**: 
- Registry V8.2: `get_guid` 增加 `prefer_container` 参数
- DSL Parser V7.2: 查找父对象时优先返回容器类型

### 子样本引用问题 (后处理修复)

**问题**: 子样本的 UNDER 指向其他样本的根对象,独立验证失败

**原因**: 逆向编译器为嵌套的逻辑根也生成了独立样本

**修复**: 后处理脚本将子样本的 UNDER 改为 "Default Work Unit"

## 训练数据统计

典型数据集分布:

| 长度范围 | 占比 |
|----------|------|
| 1-30 行 | ~82% |
| 31-100 行 | ~13% |
| 101-200 行 | ~3% |
| 200+ 行 | ~2% |

推荐样本量:5,000-10,000 条用于高质量训练

## 依赖

- Python 3.8+
- waapi (Wwise Authoring API)
- streamlit (Web UI)
- lxml (XML 解析)

## 许可

仅供内部使用

---

*NeuroWwise Team*