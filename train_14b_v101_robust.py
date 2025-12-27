# =============================================================================
# 🔥 V10.1 - Qwen2.5-Coder-14B (健壮版 - 确保上传成功)
# =============================================================================
# 修复:
# 1. LoRA 先保存本地再上传
# 2. GGUF 转换前清理显存
# 3. 上传带验证和重试
# 4. 详细错误日志
# =============================================================================

import os
import sys

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import subprocess
subprocess.run("pip install psutil -q", shell=True, capture_output=True)
import psutil
import builtins
builtins.psutil = psutil

import json
import gc
import math
import time
from datetime import timedelta
import torch

gc.collect()
torch.cuda.empty_cache()

from unsloth import FastLanguageModel
from unsloth import is_bfloat16_supported
from trl import SFTTrainer
from transformers import TrainingArguments
from huggingface_hub import hf_hub_download, HfApi, upload_folder
from google.colab import userdata
from datasets import Dataset

print("="*60)
print("🔥 V10.1 - Qwen2.5-Coder-14B (健壮版)")
print("="*60)

# GPU
gpu_name = torch.cuda.get_device_name(0)
total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f"🎮 GPU: {gpu_name} ({total_vram:.1f} GB)")

if total_vram < 35:
    print("⚠️ 14B 模型需要 40GB 显存")
    sys.exit(1)

# =============================================================================
# 配置
# =============================================================================
BASE_MODEL = "Qwen/Qwen2.5-Coder-14B-Instruct"

BATCH_SIZE = 2
GRAD_ACCUM = 8
MAX_SEQ = 1024
LORA_R = 64
LORA_ALPHA = 128
TARGET_EPOCHS = 3

print(f"\n⚙️ 14B 配置:")
print(f"   模型: {BASE_MODEL}")
print(f"   Batch: {BATCH_SIZE} × {GRAD_ACCUM} = {BATCH_SIZE * GRAD_ACCUM}")

# Token
try:
    HF_TOKEN = userdata.get('HF_TOKEN')
    print("   Token: ✓ (从 Secrets 读取)")
except:
    HF_TOKEN = input("HF Token: ").strip()
    if not HF_TOKEN: sys.exit("❌")

os.environ["HF_TOKEN"] = HF_TOKEN
HF_MODEL_REPO = "chengxuanyyy/Wwise-Engineering-Brain"

# 验证 Token
print("\n🔑 验证 HuggingFace Token...")
api = HfApi(token=HF_TOKEN)
try:
    user_info = api.whoami()
    print(f"   ✓ 登录用户: {user_info['name']}")
except Exception as e:
    print(f"   ❌ Token 无效: {e}")
    sys.exit(1)

# 数据
print("\n📂 数据加载")
data_path = hf_hub_download(
    repo_id="chengxuanyyy/wwise-dsl-training-data",
    filename="optimized_dataset_processed_processed.jsonl",
    repo_type="dataset", token=HF_TOKEN
)

samples = []
with open(data_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try: samples.append(json.loads(line))
            except: pass

TOTAL = len(samples)
EFF_BATCH = BATCH_SIZE * GRAD_ACCUM
STEPS = math.ceil(TOTAL / EFF_BATCH) * TARGET_EPOCHS
print(f"✅ 样本: {TOTAL}, 步数: {STEPS}")

# =============================================================================
# 模型
# =============================================================================
print("\n🤖 加载 14B 模型...")

gc.collect()
torch.cuda.empty_cache()

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_ALPHA,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

print("✅ 模型加载完成")

# =============================================================================
# 数据格式化
# =============================================================================
print("\n📝 数据格式化")

TEMPLATE = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

formatted = [{"text": TEMPLATE.format(s.get("instruction",""), s.get("input",""), s.get("output","")) + tokenizer.eos_token} for s in samples]
dataset = Dataset.from_list(formatted)

# =============================================================================
# 训练
# =============================================================================
print("\n⚔️ 训练")

training_args = TrainingArguments(
    output_dir="outputs",
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    warmup_steps=50,
    num_train_epochs=TARGET_EPOCHS,
    learning_rate=1e-4,
    fp16=not is_bfloat16_supported(),
    bf16=is_bfloat16_supported(),
    logging_steps=20,
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="cosine",
    seed=42,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ,
    dataset_num_proc=4,
    packing=False,
    args=training_args,
)

print(f"\n🔥 开始训练! Steps: {STEPS}")

start = time.time()
trainer.train()
train_time = str(timedelta(seconds=int(time.time() - start)))

print(f"\n✅ 训练完成! 耗时: {train_time}")

# =============================================================================
# 💾 Step 1: 保存 LoRA 到本地
# =============================================================================
print("\n" + "="*60)
print("💾 Step 1: 保存 LoRA Adapter")
print("="*60)

LORA_DIR = "lora_adapter"

# 清理
del trainer
gc.collect()
torch.cuda.empty_cache()

# 保存 LoRA
print("保存 LoRA adapter 到本地...")
model.save_pretrained(LORA_DIR)
tokenizer.save_pretrained(LORA_DIR)

# 验证文件
lora_files = os.listdir(LORA_DIR)
print(f"✓ 保存了 {len(lora_files)} 个文件:")
for f in lora_files:
    size = os.path.getsize(os.path.join(LORA_DIR, f)) / 1024 / 1024
    print(f"   {f}: {size:.1f} MB")

# 检查关键文件
required_files = ["adapter_config.json", "adapter_model.safetensors"]
missing = [f for f in required_files if f not in lora_files]
if missing:
    print(f"⚠️ 缺少文件: {missing}")
else:
    print("✓ 关键文件完整")

# =============================================================================
# 💾 Step 2: 上传 LoRA 到 HuggingFace
# =============================================================================
print("\n" + "="*60)
print("💾 Step 2: 上传 LoRA 到 HuggingFace")
print("="*60)

MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    try:
        print(f"尝试 {attempt + 1}/{MAX_RETRIES}...")
        
        # 使用 upload_folder 上传整个目录
        api.upload_folder(
            folder_path=LORA_DIR,
            repo_id=HF_MODEL_REPO,
            commit_message=f"14B LoRA V10.1 ({train_time})",
            token=HF_TOKEN,
        )
        
        print("✅ LoRA 上传成功!")
        break
        
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        if attempt < MAX_RETRIES - 1:
            print("等待 10 秒后重试...")
            time.sleep(10)
        else:
            print("⚠️ LoRA 上传失败,但继续执行 GGUF 转换")

# =============================================================================
# 📦 Step 3: GGUF 转换
# =============================================================================
print("\n" + "="*60)
print("📦 Step 3: GGUF 转换 (14B 需要较长时间)")
print("="*60)

GGUF_DIR = "model_gguf"

# 清理显存给 GGUF 转换
print("清理显存...")
gc.collect()
torch.cuda.empty_cache()

used = torch.cuda.memory_allocated(0) / 1024**3
print(f"当前显存: {used:.1f} GB")

# GGUF 转换
gguf_success = False
try:
    print("\n开始 GGUF 转换 (q4_k_m)...")
    print("⏳ 这可能需要 10-20 分钟,请耐心等待...")
    
    model.save_pretrained_gguf(
        GGUF_DIR, 
        tokenizer, 
        quantization_method="q4_k_m"
    )
    
    # 验证 GGUF 文件
    if os.path.exists(GGUF_DIR):
        gguf_files = [f for f in os.listdir(GGUF_DIR) if f.endswith(".gguf")]
        if gguf_files:
            gguf_file = gguf_files[0]
            gguf_path = os.path.join(GGUF_DIR, gguf_file)
            gguf_size = os.path.getsize(gguf_path) / 1024 / 1024 / 1024
            print(f"✅ GGUF 转换成功!")
            print(f"   文件: {gguf_file}")
            print(f"   大小: {gguf_size:.2f} GB")
            gguf_success = True
        else:
            print("❌ GGUF 目录存在但没有 .gguf 文件")
    else:
        print("❌ GGUF 目录不存在")
        
except Exception as e:
    print(f"❌ GGUF 转换失败: {e}")
    print("\n💡 提示: 可以稍后手动转换")
    print("   1. 下载 LoRA: git clone https://huggingface.co/" + HF_MODEL_REPO)
    print("   2. 合并模型: python merge_lora.py")
    print("   3. 转换 GGUF: python llama.cpp/convert.py")

# =============================================================================
# 📤 Step 4: 上传 GGUF
# =============================================================================
if gguf_success:
    print("\n" + "="*60)
    print("📤 Step 4: 上传 GGUF 到 HuggingFace")
    print("="*60)
    
    gguf_path = os.path.join(GGUF_DIR, gguf_file)
    remote_path = f"gguf/wwise-brain-14b-q4_k_m.gguf"
    
    print(f"上传 {gguf_size:.2f} GB 文件...")
    print("⏳ 大文件上传可能需要 10-30 分钟...")
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"尝试 {attempt + 1}/{MAX_RETRIES}...")
            
            api.upload_file(
                path_or_fileobj=gguf_path,
                path_in_repo=remote_path,
                repo_id=HF_MODEL_REPO,
                token=HF_TOKEN,
            )
            
            print("✅ GGUF 上传成功!")
            break
            
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            if attempt < MAX_RETRIES - 1:
                print("等待 30 秒后重试...")
                time.sleep(30)
            else:
                print("⚠️ GGUF 上传失败")
                print(f"   本地文件保存在: {gguf_path}")
                print("   你可以手动上传到 HuggingFace")
    
    # 上传 Modelfile
    print("\n上传 Modelfile...")
    try:
        modelfile_content = '''FROM ./wwise-brain-14b-q4_k_m.gguf

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

SYSTEM """你是一个专业的 Wwise 音频技术专家,精通 DSL 代码生成。根据用户的需求,生成符合 Wwise 工程规范的 DSL 代码。"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''
        
        modelfile_path = "Modelfile"
        with open(modelfile_path, "w") as f:
            f.write(modelfile_content)
        
        api.upload_file(
            path_or_fileobj=modelfile_path,
            path_in_repo="gguf/Modelfile",
            repo_id=HF_MODEL_REPO,
            token=HF_TOKEN,
        )
        print("✅ Modelfile 上传成功!")
        
    except Exception as e:
        print(f"⚠️ Modelfile 上传失败: {e}")

# =============================================================================
# ✅ 最终验证
# =============================================================================
print("\n" + "="*60)
print("✅ 最终验证")
print("="*60)

try:
    from huggingface_hub import list_repo_files
    
    files = list_repo_files(HF_MODEL_REPO, token=HF_TOKEN)
    
    print(f"\n📦 {HF_MODEL_REPO} 文件列表:")
    
    # 分类显示
    lora_files_remote = [f for f in files if not f.startswith("gguf/")]
    gguf_files_remote = [f for f in files if f.startswith("gguf/")]
    
    print("\n🔧 LoRA 文件:")
    for f in lora_files_remote[:10]:
        print(f"   {f}")
    if len(lora_files_remote) > 10:
        print(f"   ... 还有 {len(lora_files_remote) - 10} 个文件")
    
    print("\n📦 GGUF 文件:")
    for f in gguf_files_remote:
        print(f"   {f}")
    
    # 检查关键文件
    print("\n🔍 关键文件检查:")
    checks = [
        ("adapter_config.json", "adapter_config.json" in files),
        ("adapter_model.safetensors", "adapter_model.safetensors" in files),
        ("GGUF 模型", any("gguf" in f.lower() and f.endswith(".gguf") for f in files)),
        ("Modelfile", "gguf/Modelfile" in files),
    ]
    
    all_ok = True
    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"   {status} {name}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n🎉 所有文件上传成功!")
    else:
        print("\n⚠️ 部分文件缺失,请检查")
        
except Exception as e:
    print(f"⚠️ 验证失败: {e}")

# =============================================================================
# 🎉 完成
# =============================================================================
print("\n" + "="*60)
print("🎉 训练完成!")
print("="*60)

print(f"""
📊 训练统计:
   模型: Qwen2.5-Coder-14B
   数据: {TOTAL} 样本
   步数: {STEPS}
   时间: {train_time}

📦 模型地址:
   https://huggingface.co/{HF_MODEL_REPO}

🚀 使用方法:

1. Ollama (本地部署):
   # 下载 GGUF
   wget https://huggingface.co/{HF_MODEL_REPO}/resolve/main/gguf/wwise-brain-14b-q4_k_m.gguf
   
   # 下载 Modelfile
   wget https://huggingface.co/{HF_MODEL_REPO}/resolve/main/gguf/Modelfile
   
   # 创建 Ollama 模型
   ollama create wwise-brain-14b -f Modelfile
   
   # 运行
   ollama run wwise-brain-14b

2. Python (使用 LoRA):
   from unsloth import FastLanguageModel
   model, tokenizer = FastLanguageModel.from_pretrained("{HF_MODEL_REPO}")
""")

print("="*60)
