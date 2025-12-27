# 📝 NeuroWwise 更新日志

## [V5.1] - 2024-12-27

### ✨ 新增
- 训练脚本整合为单文件 `train_unsloth_v51.py`
- 智能 GPU 检测,自动优化 Batch Size
- 动态计算训练步数,无需手动配置
- 训练时间预估功能

### 🔧 优化
- L4 GPU: Batch Size 8→4,避免 OOM
- 基座模型改为 Qwen2.5-Coder-7B-Instruct
- 学习率调整为 1e-4(更稳定)
- Epochs 改为 2(防止过拟合)

### 📊 性能
- L4 训练时间: 5-6h → 3-4h
- 训练步数: ~5500 → ~2750

---

## [V2.1] - 2024-12-27

### 🔧 修复
- 修复 Unsloth psutil 依赖缺失问题
- 修复 Colab triton 版本冲突
- 添加训练后显存清理机制

### ✨ 改进
- 训练脚本改用 Colab Secrets 存储 Token (安全)
- 自动统计数据集样本数,动态计算训练步数
- Modelfile 自动匹配实际 GGUF 文件名

---

## [V2.0] - 2024-12-26

### ✨ 新增
- DSL 解析器 V7.3: 支持 Attenuation 曲线语法
- XML 转译器 V3.4: 支持 Attenuation 曲线点位提取
- DSL 验证器 V2.0: 完全适配 DSL Parser V7.0

### 🔧 修复
- 修复嵌套 Container 解析问题
- 修复 Workflow 类型识别问题

### 📊 数据
- 数据集扩充至 20,182 样本
- Workflow 样本占比提升至 15%
- GameParameter 样本优化至 10%

---

## [V1.1] - 2024-12-25

### ✨ 新增
- 样本裂变器 V1.1: 支持多种增强策略
- 指令生成器 V1.1: 多样化指令模板

### 🔧 修复
- 修复 Event 样本格式问题
- 修复 SwitchGroup/StateGroup 混淆问题

---

## [V1.0] - 2024-12-24

### 🎉 初始版本

- DSL 解析器 V7.0
- DSL 验证器 V1.0
- XML to DSL 转译器 V3.0
- 指令生成器 V1.0
- 样本裂变器 V1.0
- 数据集优化器 V1.0
- 数据集分析器 V1.0
- HuggingFace 上传器 V1.0
- Colab 训练脚本 V1.0

---

## 路线图

### V2.2 (计划中)
- [ ] 支持 WAAPI 实时验证
- [ ] 添加 Web UI 界面
- [ ] 支持增量训练

### V3.0 (未来)
- [ ] 多模态支持 (音频预览)
- [ ] Wwise 插件集成
- [ ] 在线推理服务
