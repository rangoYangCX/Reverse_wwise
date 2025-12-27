# =============================================================================
# 🚀 Wwise Engineering Brain - 终极全自动训练脚本 V5.2 (显存优化版)
# =============================================================================
# 核心优化:
# 1. [智能] 自动识别 L4/A100 高显存环境，自动开启优化 Batch 模式
# 2. [极速] 训练时长控制在 3-4 小时 (L4 GPU)
# 3. [双源] 优先读取本地上传的 JSONL，无文件则自动从 HF 下载
# 4. [安全] 支持 Colab Secrets 或手动输入 Token
# 5. [稳健] OOM 自动降级 + 深度显存清理，防止崩溃
# 6. [完整] 包含训练、LoRA备份、GGUF转换、Modelfile生成、自动上传
# =============================================================================

import os
import sys
import subprocess
import json
import torch
import gc
import math
import time
from datetime import timedelta

# --- 0. 环境与依赖自检 (最优先执行) ---
print("="*60)
print("🔧 环境初始化...")
print("="*60)

# 修复 Unsloth psutil 依赖问题
try:
    import psutil
    import builtins
    builtins.psutil = psutil
except ImportError:
    subprocess.check_call("pip install psutil", shell=True)
    import psutil
    import builtins
    builtins.psutil = psutil

def install_package(pkg):
    try:
        subprocess.check_call(f"pip install {pkg}", shell=True)
    except: pass

print("📦 安装核心依赖 (Unsloth & HF)...")
install_package("unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git")
install_package("--no-deps xformers trl peft accelerate bitsandbytes huggingface_hub datasets")

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from huggingface_hub import HfApi, hf_hub_download, create_repo
from google.colab import userdata
from datasets import Dataset

# =============================================================================
# ⚙️ 用户配置区
# =============================================================================

# 1. 鉴权配置
try:
    HF_TOKEN = userdata.get('HF_TOKEN')
    print("✅ 从 Colab Secrets 读取 Token 成功")
except:
    print("⚠️ 未找到 Colab Secret")
    print("   方法1: 点击左侧 🔑 图标 → 添加 HF_TOKEN")
    print("   方法2: 手动输入 Token")
    HF_TOKEN = input("\n请输入 HuggingFace Token (留空退出): ").strip()
    if not HF_TOKEN:
        print("❌ Token 不能为空，退出")
        raise SystemExit()

os.environ["HF_TOKEN"] = HF_TOKEN

# 2. 仓库配置
HF_USER = "chengxuanyyy"
REPO_NAME = "Wwise-Engineering-Brain"
HF_MODEL_REPO = f"{HF_USER}/{REPO_NAME}"

# 3. 数据集配置
LOCAL_DATASET_NAME = "wwise_phase2_full_22k.jsonl" 
HF_DATASET_REPO = "chengxuanyyy/wwise-dsl-training-data"
HF_DATASET_FILENAME = "optimized_dataset_processed_processed.jsonl"

# 4. 模型与训练参数
BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
MAX_SEQ_LENGTH = 2048 
QUANTIZATION_METHOD = "q4_k_m"
TARGET_EPOCHS = 2

# =============================================================================
# 🏎️ 显存智能检测与 Batch Size 优化
# =============================================================================
print("\n" + "="*60)
print("🏎️ 硬件性能评估")
print("="*60)

gpu_name = torch.cuda.get_device_name(0)
total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f"🎮 检测到 GPU: {gpu_name} ({total_vram:.2f} GB VRAM)")

# 动态设定 Batch Size (安全优化版)
if total_vram > 35:  # A100 (40GB)
    BATCH_SIZE_PER_DEVICE = 8
    GRAD_ACCUM_STEPS = 4
    print("🚀 A100 环境: 激活极速模式 (Batch Size = 8)")
elif total_vram > 20:  # L4 (24GB)
    BATCH_SIZE_PER_DEVICE = 4  # 安全值，避免 OOM
    GRAD_ACCUM_STEPS = 4
    print("🚀 L4 环境: Turbo 模式 (Batch Size = 4)")
elif total_vram > 14:  # T4 (16GB)
    BATCH_SIZE_PER_DEVICE = 2
    GRAD_ACCUM_STEPS = 4
    print("🛡️ T4 环境: 安全模式 (Batch Size = 2)")
else:
    BATCH_SIZE_PER_DEVICE = 1
    GRAD_ACCUM_STEPS = 8
    print("⚠️ 低显存环境: 保守模式")

EFFECTIVE_BATCH_SIZE = BATCH_SIZE_PER_DEVICE * GRAD_ACCUM_STEPS
print(f"⚡ 总有效批次 (Effective Batch Size): {EFFECTIVE_BATCH_SIZE}")

# =============================================================================
# 📊 Step 1: 智能数据加载与分析
# =============================================================================
print("\n" + "="*60)
print("📂 Step 1: 数据加载与分析")
print("="*60)

data_file_path = ""

if os.path.exists(LOCAL_DATASET_NAME):
    print(f"✅ 发现本地数据集: {LOCAL_DATASET_NAME}")
    data_file_path = LOCAL_DATASET_NAME
else:
    print(f"⚠️ 本地未找到，从 HuggingFace 下载...")
    try:
        data_file_path = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename=HF_DATASET_FILENAME,
            repo_type="dataset",
            token=HF_TOKEN
        )
        print(f"✅ 下载成功")
    except Exception as e:
        sys.exit(f"❌ 数据获取失败: {e}")

# 读取并统计
samples = []
with open(data_file_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if line.strip():
            try:
                samples.append(json.loads(line))
            except: pass

TOTAL_SAMPLES = len(samples)
print(f"📊 有效样本数: {TOTAL_SAMPLES}")

# 动态步数计算
STEPS_PER_EPOCH = math.ceil(TOTAL_SAMPLES / EFFECTIVE_BATCH_SIZE)
MAX_STEPS = int(STEPS_PER_EPOCH * TARGET_EPOCHS)

print(f"🧮 计算参数:")
print(f"   - Effective Batch Size: {EFFECTIVE_BATCH_SIZE}")
print(f"   - Steps per Epoch: {STEPS_PER_EPOCH}")
print(f"   - Target Epochs: {TARGET_EPOCHS}")
print(f"🎯 最终训练步数: {MAX_STEPS} 步")

# 预估时间
if "L4" in gpu_name:
    estimated_hours = MAX_STEPS * 4 / 3600  # L4 约 4秒/步
elif "A100" in gpu_name:
    estimated_hours = MAX_STEPS * 2 / 3600  # A100 约 2秒/步
else:
    estimated_hours = MAX_STEPS * 8 / 3600  # T4 约 8秒/步
print(f"⏱️ 预估训练时间: {estimated_hours:.1f} 小时")

# =============================================================================
# 🤖 Step 2: 加载模型
# =============================================================================
print("\n" + "="*60)
print("🤖 Step 2: 加载模型 (Unsloth Accelerated)")
print("="*60)

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=128,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

print("✅ 模型加载完成")

# =============================================================================
# 📝 Step 3: 数据格式化
# =============================================================================
print("\n" + "="*60)
print("📝 Step 3: 数据集格式化")
print("="*60)

alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs = examples["input"]
    outputs = examples["output"]
    texts = []
    for instruction, input_text, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input_text, output) + tokenizer.eos_token
        texts.append(text)
    return {"text": texts}

dataset = Dataset.from_list(samples)
dataset = dataset.map(formatting_prompts_func, batched=True)
print(f"✅ 格式化完成")

# =============================================================================
# ⚔️ Step 4: 开始训练
# =============================================================================
print("\n" + "="*60)
print("⚔️ Step 4: 开始训练")
print("="*60)

# 训练前显存清理
gc.collect()
torch.cuda.empty_cache()
free_mem = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()) / 1024**3
print(f"📊 当前可用显存: {free_mem:.2f} GB")

# OOM 自动降级机制
def try_train(batch_size, grad_accum):
    """尝试训练，OOM 时返回 False"""
    global trainer
    try:
        training_args = TrainingArguments(
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum,
            warmup_steps=50,
            max_steps=MAX_STEPS,
            learning_rate=1e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=20,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir="outputs",
            report_to="none",
            save_strategy="steps",
            save_steps=500,
            save_total_limit=2,
        )
        training_args.dataset_num_proc = 2

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LENGTH,
            dataset_num_proc=2,
            packing=False,
            args=training_args,
        )
        
        trainer.train()
        return True
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n⚠️ OOM! Batch Size {batch_size} 太大")
            del trainer
            gc.collect()
            torch.cuda.empty_cache()
            return False
        raise e

# 尝试训练，OOM 时自动降级
start_time = time.time()
train_success = False

# 降级顺序: 原始 -> 减半 -> 最小
batch_configs = [
    (BATCH_SIZE_PER_DEVICE, GRAD_ACCUM_STEPS),
    (max(1, BATCH_SIZE_PER_DEVICE // 2), GRAD_ACCUM_STEPS * 2),
    (1, 8),
]

for bs, ga in batch_configs:
    print(f"\n🎯 尝试: Batch Size = {bs}, Grad Accum = {ga}")
    if try_train(bs, ga):
        train_success = True
        BATCH_SIZE_PER_DEVICE = bs  # 更新实际使用的值
        GRAD_ACCUM_STEPS = ga
        break
    print("   重试中...")

if not train_success:
    print("❌ 所有配置都 OOM，请使用更大显存的 GPU")
    sys.exit(1)

train_time = str(timedelta(seconds=int(time.time() - start_time)))
print(f"\n✅ 训练完成! 总耗时: {train_time}")

# 显存清理
print("🧹 清理显存...")
del trainer
gc.collect()
torch.cuda.empty_cache()

# =============================================================================
# 💾 Step 5: 导出与交付
# =============================================================================
print("\n" + "="*60)
print("💾 Step 5: 成果导出与 GGUF 转换")
print("="*60)

# 深度清理显存 (GGUF 转换需要大量内存)
print("🧹 深度清理显存 (为 GGUF 转换腾出空间)...")
del model
gc.collect()
torch.cuda.empty_cache()
time.sleep(3)  # 等待显存完全释放

free_mem = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()) / 1024**3
print(f"📊 清理后可用显存: {free_mem:.2f} GB")

# 重新加载模型用于导出
print("🔄 重新加载模型...")
model, tokenizer = FastLanguageModel.from_pretrained(
    "outputs",  # 从训练 checkpoint 加载
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=True,
)

# 1. 上传 LoRA Adapter
print("☁️ 同步 LoRA Adapter...")
try:
    model.push_to_hub(HF_MODEL_REPO, token=HF_TOKEN, commit_message=f"LoRA (Steps: {MAX_STEPS}, Samples: {TOTAL_SAMPLES})")
    tokenizer.push_to_hub(HF_MODEL_REPO, token=HF_TOKEN)
    print("   ✓ LoRA 上传成功")
except Exception as e:
    print(f"   ⚠️ LoRA 上传警告: {e}")

# 2. 转换 GGUF
print(f"📦 执行 GGUF 转换 ({QUANTIZATION_METHOD})...")
try:
    output_dir = "model_gguf"
    model.save_pretrained_gguf(output_dir, tokenizer, quantization_method=QUANTIZATION_METHOD)
    
    gguf_files = [f for f in os.listdir(output_dir) if f.endswith(".gguf")]
    
    if gguf_files:
        local_path = os.path.join(output_dir, gguf_files[0])
        remote_filename = f"wwise-brain-v2-{QUANTIZATION_METHOD}.gguf"
        
        print(f"🚀 上传模型: {remote_filename}")
        api = HfApi(token=HF_TOKEN)
        
        try:
            api.create_repo(repo_id=HF_MODEL_REPO, exist_ok=True)
        except: pass

        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=f"gguf/{remote_filename}",
            repo_id=HF_MODEL_REPO,
            token=HF_TOKEN
        )
        print("   ✓ GGUF 上传成功")
        
        # 3. 生成 Modelfile
        print("📝 生成 Modelfile...")
        modelfile_content = f'''FROM ./{remote_filename}

TEMPLATE """<|im_start|>system
{{{{ .System }}}}<|im_end|>
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
"""

SYSTEM """你是一个专业的 Wwise 音频技术专家，精通 DSL 代码生成。"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''
        with open("Modelfile", "w", encoding="utf-8") as f:
            f.write(modelfile_content)
            
        api.upload_file(
            path_or_fileobj="Modelfile",
            path_in_repo="gguf/Modelfile",
            repo_id=HF_MODEL_REPO,
            token=HF_TOKEN
        )
        print("   ✓ Modelfile 上传成功")
        
        # 4. 生成 README
        print("📄 更新 README...")
        readme_content = f"""---
license: apache-2.0
base_model: {BASE_MODEL}
tags:
  - wwise
  - audio
  - game-dev
  - dsl
  - unsloth
---

# 🎧 Wwise Engineering Brain V2.0

专为 **游戏音频工程** 设计的垂直领域大模型。

## 📊 训练信息

| 指标 | 值 |
|------|-----|
| 基座模型 | {BASE_MODEL} |
| 训练样本 | {TOTAL_SAMPLES} |
| 训练步数 | {MAX_STEPS} |
| 训练时间 | {train_time} |
| LoRA Rank | 64 |
| 量化格式 | {QUANTIZATION_METHOD} |

## 🚀 快速开始 (Ollama)

```bash
# 下载模型
huggingface-cli download {HF_MODEL_REPO} gguf/{remote_filename} --local-dir ./
huggingface-cli download {HF_MODEL_REPO} gguf/Modelfile --local-dir ./

# 创建并运行
ollama create wwise-brain -f Modelfile
ollama run wwise-brain
```

## ✅ 能力范围

- 创建 Audio 层级结构 (Container/Sound)
- 配置 Attenuation 衰减曲线
- 设置 GameParameter RTPC 参数
- 创建 SwitchGroup/StateGroup
- 生成 Event 及完整工作流

## 📁 文件说明

- `gguf/{remote_filename}`: 量化模型 (~4.5GB)
- `gguf/Modelfile`: Ollama 配置文件
- 其他文件: LoRA adapter

---

*Trained with Unsloth + NeuroWwise Pipeline*
"""
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        api.upload_file(
            path_or_fileobj="README.md",
            path_in_repo="README.md",
            repo_id=HF_MODEL_REPO,
            token=HF_TOKEN
        )
        print("   ✓ README 上传成功")

    else:
        print("❌ GGUF 生成失败")

except Exception as e:
    print(f"❌ 导出流程出错: {e}")

# =============================================================================
# 🎉 完成
# =============================================================================
print("\n" + "="*60)
print("🎉 全流程完成!")
print("="*60)
print(f"""
📊 训练统计:
   样本数: {TOTAL_SAMPLES}
   训练步数: {MAX_STEPS}
   训练时间: {train_time}

📦 模型地址:
   https://huggingface.co/{HF_MODEL_REPO}

🚀 本地使用:
   huggingface-cli download {HF_MODEL_REPO} gguf/wwise-brain-v2-{QUANTIZATION_METHOD}.gguf --local-dir ./
   huggingface-cli download {HF_MODEL_REPO} gguf/Modelfile --local-dir ./
   ollama create wwise-brain -f Modelfile
   ollama run wwise-brain
""")
print("="*60)
