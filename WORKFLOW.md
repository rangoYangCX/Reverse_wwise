# 📋 NeuroWwise 工作流详细指南

## 目录

1. [从零开始的完整流程](#从零开始的完整流程)
2. [各工具详细使用](#各工具详细使用)
3. [常见问题排查](#常见问题排查)
4. [最佳实践](#最佳实践)

---

## 从零开始的完整流程

### Phase 1: 数据采集

```
目标: 从 Wwise 工程提取 DSL 样本
时间: 1-2 小时
输出: raw_samples.jsonl
```

**Step 1.1: 准备 Wwise 工程**

```bash
# 确保有以下文件结构
WwiseProject/
├── Actor-Mixer Hierarchy/
│   └── Default Work Unit.wwu
├── Attenuations/
│   └── Default Work Unit.wwu
├── Events/
│   └── Default Work Unit.wwu
├── Game Parameters/
│   └── Default Work Unit.wwu
├── Switches/
│   └── Default Work Unit.wwu
└── States/
    └── Default Work Unit.wwu
```

**Step 1.2: 运行转译器**

```bash
python xml_to_dsl.py \
    --input ./WwiseProject \
    --output raw_samples.jsonl \
    --recursive
```

**输出示例**:
```json
{"type": "Audio", "dsl": "Audio(\"Footsteps\") { ... }"}
{"type": "Event", "dsl": "Event(\"Play_Footstep\") { ... }"}
```

---

### Phase 2: 数据验证

```
目标: 确保 DSL 语法正确
时间: 10-30 分钟
输出: validated_samples.jsonl
```

**Step 2.1: 运行验证器**

```bash
python dsl_validator.py \
    --input raw_samples.jsonl \
    --output validated_samples.jsonl
```

**验证报告示例**:
```
📊 验证结果:
   总样本: 1500
   通过: 1423 (94.9%)
   失败: 77 (5.1%)
   
❌ 失败原因统计:
   括号不匹配: 45
   缺少必需属性: 22
   未知语法: 10
```

---

### Phase 3: 指令生成

```
目标: 为 DSL 添加自然语言指令
时间: 10-20 分钟
输出: with_instructions.jsonl
```

**Step 3.1: 运行指令生成器**

```bash
python instruction_generator.py \
    --input validated_samples.jsonl \
    --output with_instructions.jsonl
```

**输出格式**:
```json
{
  "instruction": "创建一个脚步声的音频层级结构",
  "input": "",
  "output": "Audio(\"Footsteps\") { Container(\"Surface_Types\") { ... } }"
}
```

---

### Phase 4: 数据增强

```
目标: 扩充数据集规模
时间: 30-60 分钟
输出: augmented_samples.jsonl
```

**Step 4.1: 运行样本裂变器**

```bash
python sample_fission.py \
    --input with_instructions.jsonl \
    --output augmented_samples.jsonl \
    --multiplier 3
```

**增强统计**:
```
📊 裂变结果:
   原始样本: 1423
   增强后: 4269
   增强倍率: 3x
```

---

### Phase 5: 数据集优化

```
目标: 平衡样本类型分布
时间: 10-20 分钟
输出: optimized_dataset.jsonl
```

**Step 5.1: 运行优化器**

```bash
python dataset_optimizer.py \
    --input augmented_samples.jsonl \
    --output optimized_dataset.jsonl
```

**优化报告**:
```
📊 优化前分布:
   Audio: 45% → 过多
   Event: 5%  → 过少
   
📊 优化后分布:
   Audio: 25% ✓
   Event: 15% ✓
   Workflow: 15% ✓
   ...
```

---

### Phase 6: 质量检查

```
目标: 确认数据集质量
时间: 5-10 分钟
输出: 分析报告
```

**Step 6.1: 运行分析器**

```bash
python dataset_analyzer.py \
    --input optimized_dataset.jsonl
```

**分析报告示例**:
```
============================================================
📊 数据集分析报告
============================================================

📦 基本信息:
   样本数: 20182
   文件大小: 45.2 MB

📊 类型分布:
   Audio: 5045 (25.0%)
   Attenuation: 3027 (15.0%)
   Event: 3027 (15.0%)
   Workflow: 3027 (15.0%)
   SwitchGroup: 2018 (10.0%)
   StateGroup: 2018 (10.0%)
   GameParameter: 2020 (10.0%)

📏 Token 长度:
   最小: 50
   最大: 1850
   平均: 320
   中位数: 280

✅ 质量评分: 92/100
```

---

### Phase 7: 上传到 HuggingFace

```
目标: 托管数据集
时间: 5-10 分钟
输出: HuggingFace 数据集链接
```

**Step 7.1: 上传**

```bash
python upload_to_hf.py optimized_dataset.jsonl
```

**输出**:
```
✅ 已上传: https://huggingface.co/datasets/chengxuanyyy/wwise-dsl-training-data
```

---

### Phase 8: 模型训练

```
目标: 微调 LLM
时间: 3-4 小时 (L4 GPU)
输出: LoRA + GGUF 模型
```

**Step 8.1: Colab 设置**

1. 新建 Colab Notebook
2. 选择 L4 GPU (推荐) 或 A100
3. 设置 Secret: `HF_TOKEN`

**Step 8.2: 上传数据集 (可选)**

如果要用本地数据集,上传 `wwise_phase2_full_22k.jsonl` 到 Colab

**Step 8.3: 运行训练脚本**

将 `train_unsloth_v51.py` 内容复制到 Cell 运行

**训练配置 (自动优化)**:
```python
# L4 GPU (24GB)
BATCH_SIZE = 4
GRAD_ACCUM = 4
EFFECTIVE_BS = 16
EPOCHS = 2
# 步数 ≈ 2750,时间 3-4h

# A100 GPU (40GB)  
BATCH_SIZE = 8
GRAD_ACCUM = 4
EFFECTIVE_BS = 32
EPOCHS = 2
# 步数 ≈ 1375,时间 1.5-2h
```

**训练进度**:
```
🚀 训练开始!
   样本数: 20182
   总步数: 2750
[████████████████████████████░░] 95.0% | Step 2612/2750 | Loss: 0.4521 | ETA: 0:08:32
```

---

### Phase 9: 本地部署

```
目标: 使用训练好的模型
时间: 5-10 分钟
```

**Step 9.1: 下载模型**

```bash
huggingface-cli download chengxuanyyy/Wwise-Engineering-Brain \
    gguf/wwise-dsl-v2-Q4_K_M.gguf --local-dir ./model

huggingface-cli download chengxuanyyy/Wwise-Engineering-Brain \
    gguf/Modelfile --local-dir ./model
```

**Step 9.2: 创建 Ollama 模型**

```bash
cd model
ollama create wwise-dsl -f Modelfile
```

**Step 9.3: 运行**

```bash
ollama run wwise-dsl
```

**测试**:
```
>>> 创建一个脚步声系统,支持不同地面类型切换

Audio("Footsteps") {
    Container("SurfaceSwitch", mode="switch", switch_group="Surface_Type") {
        Container("Concrete") { ... }
        Container("Grass") { ... }
        Container("Wood") { ... }
    }
}
```

---

## 各工具详细使用

### DSL 解析器参数

```python
from dsl_parser import DSLParser

parser = DSLParser()
result = parser.parse(dsl_code)

# 返回结构
{
    "type": "Audio",
    "name": "Footsteps",
    "properties": {...},
    "children": [...]
}
```

### DSL 验证器参数

```bash
python dsl_validator.py \
    --input input.jsonl \      # 输入文件
    --output output.jsonl \    # 输出文件
    --strict                   # 严格模式 (可选)
```

### 指令生成器参数

```bash
python instruction_generator.py \
    --input input.jsonl \
    --output output.jsonl \
    --language zh              # zh/en/mixed
```

### 样本裂变器参数

```bash
python sample_fission.py \
    --input input.jsonl \
    --output output.jsonl \
    --multiplier 3 \           # 增强倍率
    --seed 42                  # 随机种子
```

### 数据集优化器参数

```bash
python dataset_optimizer.py \
    --input input.jsonl \
    --output output.jsonl \
    --target-distribution config.json  # 目标分布配置
```

---

## 常见问题排查

### Q1: 转译器无法解析 .wwu 文件

```
原因: XML 格式不标准
解决: 确保 Wwise 工程已保存,使用 Wwise 2021+ 版本
```

### Q2: 验证器报告大量失败

```
原因: DSL 语法不完整
解决: 
1. 检查转译器输出日志
2. 更新 DSL 解析器到最新版本
3. 手动修复常见错误模式
```

### Q3: 训练显存不足

```
原因: L4 GPU 显存 24GB 不够
解决:
1. 减少 batch_size: 4 → 2
2. 减少 max_seq_length: 2048 → 1024
3. 启用 gradient_checkpointing
```

### Q4: GGUF 导出失败

```
原因: 显存不足
解决: 在导出前清理显存
import gc, torch
del trainer
torch.cuda.empty_cache()
gc.collect()
```

### Q5: Ollama 运行报错

```
原因: Modelfile 路径错误
解决: 确保 GGUF 和 Modelfile 在同一目录
```

---

## 最佳实践

### 数据质量

1. **多样性**: 确保覆盖所有 7 种 DSL 类型
2. **平衡性**: 使用优化器平衡分布
3. **长度**: 控制样本长度在 200-1500 tokens

### 训练配置

1. **Epoch**: 3 轮通常足够
2. **学习率**: 2e-4 适合大多数情况
3. **LoRA Rank**: 64 是性价比最高的选择

### 模型使用

1. **温度**: 0.7 平衡创造性和准确性
2. **Top-p**: 0.9 保证输出多样性
3. **提示词**: 使用中文,描述具体需求

---

## 附录:DSL 语法参考

```
# Audio 层级
Audio("name") {
    property = value
    Container("name") { ... }
    Sound("name", "path.wav") { ... }
}

# Attenuation
Attenuation("name") {
    curve(type="volume", points=[(0,0), (100,-96)])
}

# Event
Event("name") {
    target = "ObjectName"
    action = "Play"
}

# SwitchGroup
SwitchGroup("name") {
    Switch("option1")
    Switch("option2")
}

# StateGroup
StateGroup("name") {
    State("state1")
    State("state2")
}

# GameParameter
GameParameter("name", min=0, max=100, default=50)

# Workflow (组合)
Workflow {
    Audio("name") { ... }
    Event("name") { ... }
}
```
