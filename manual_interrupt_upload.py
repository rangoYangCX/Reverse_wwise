# =============================================================================
# 🛑 手动中断后 - GGUF 打包 & 上传脚本
# =============================================================================
# 使用场景:
# 1. 训练差不多了,想提前停止
# 2. 训练被意外中断
# 3. 训练完成但上传失败
#
# 使用方法:
# 1. 停止训练 (Ctrl+C 或停止按钮)
# 2. 运行此脚本
# =============================================================================

import os
import sys
import gc
import time
from datetime import datetime

print("="*60)
print("🛑 手动中断后 - GGUF 打包 & 上传")
print("="*60)

# =============================================================================
# Step 1: 查找已保存的模型
# =============================================================================
print("\n🔍 Step 1: 查找已保存的模型")
print("-"*40)

# 可能的保存位置
possible_dirs = [
    "outputs/checkpoint-3500",
    "outputs/checkpoint-3000",
    "outputs/checkpoint-2500",
    "outputs/checkpoint-2000",
    "outputs/checkpoint-1500",
    "outputs/checkpoint-1000",
    "outputs/checkpoint-500",
    "outputs/final",
    "outputs",
    "lora_adapter",
]

found_checkpoint = None
found_step = 0

for d in possible_dirs:
    if os.path.exists(d):
        # 检查是否有 adapter 文件
        adapter_config = os.path.join(d, "adapter_config.json")
        adapter_model = os.path.join(d, "adapter_model.safetensors")
        
        if os.path.exists(adapter_config):
            # 提取步数
            if "checkpoint-" in d:
                step = int(d.split("-")[-1])
            else:
                step = 0
            
            if step > found_step:
                found_step = step
                found_checkpoint = d
            elif found_checkpoint is None:
                found_checkpoint = d

if found_checkpoint:
    print(f"✅ 找到模型: {found_checkpoint}")
    if found_step > 0:
        print(f"   步数: {found_step}")
    
    # 列出文件
    files = os.listdir(found_checkpoint)
    print(f"   文件数: {len(files)}")
    for f in files[:5]:
        size = os.path.getsize(os.path.join(found_checkpoint, f)) / 1024 / 1024
        print(f"   - {f} ({size:.1f} MB)")
    if len(files) > 5:
        print(f"   ... 还有 {len(files) - 5} 个文件")
else:
    print("❌ 未找到已保存的模型!")
    print("\n可能的原因:")
    print("1. 训练未达到第一个 save_steps (500)")
    print("2. 保存目录不同")
    print("\n请检查 outputs/ 目录")
    
    if os.path.exists("outputs"):
        print("\noutputs/ 目录内容:")
        for f in os.listdir("outputs"):
            print(f"   {f}")
    
    sys.exit(1)

# =============================================================================
# Step 2: 配置
# =============================================================================
print("\n⚙️ Step 2: 配置")
print("-"*40)

# HuggingFace 配置
from google.colab import userdata

try:
    HF_TOKEN = userdata.get('HF_TOKEN')
    print("✓ Token: 从 Secrets 读取")
except:
    HF_TOKEN = input("请输入 HF Token: ").strip()
    if not HF_TOKEN:
        sys.exit("❌ Token 不能为空")

HF_MODEL_REPO = "chengxuanyyy/Wwise-Engineering-Brain"

# 检测模型大小 (7B or 14B)
adapter_config_path = os.path.join(found_checkpoint, "adapter_config.json")
import json
with open(adapter_config_path, 'r') as f:
    config = json.load(f)

base_model = config.get("base_model_name_or_path", "")
if "14B" in base_model or "14b" in base_model:
    MODEL_SIZE = "14B"
    BASE_MODEL = "Qwen/Qwen2.5-Coder-14B-Instruct"
else:
    MODEL_SIZE = "7B"
    BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"

print(f"✓ 基座模型: {BASE_MODEL}")
print(f"✓ 模型大小: {MODEL_SIZE}")
print(f"✓ 目标仓库: {HF_MODEL_REPO}")

# =============================================================================
# Step 3: 验证 HuggingFace Token
# =============================================================================
print("\n🔑 Step 3: 验证 Token")
print("-"*40)

from huggingface_hub import HfApi, list_repo_files

api = HfApi(token=HF_TOKEN)

try:
    user_info = api.whoami()
    print(f"✓ 登录用户: {user_info['name']}")
except Exception as e:
    print(f"❌ Token 无效: {e}")
    sys.exit(1)

# =============================================================================
# Step 4: 上传 LoRA Adapter
# =============================================================================
print("\n📤 Step 4: 上传 LoRA Adapter")
print("-"*40)

MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    try:
        print(f"尝试 {attempt + 1}/{MAX_RETRIES}...")
        
        api.upload_folder(
            folder_path=found_checkpoint,
            repo_id=HF_MODEL_REPO,
            commit_message=f"LoRA {MODEL_SIZE} (step {found_step})",
            token=HF_TOKEN,
        )
        
        print("✅ LoRA 上传成功!")
        break
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        if attempt < MAX_RETRIES - 1:
            print("等待 10 秒后重试...")
            time.sleep(10)
        else:
            print("⚠️ LoRA 上传失败,继续尝试 GGUF...")

# =============================================================================
# Step 5: 加载模型用于 GGUF 转换
# =============================================================================
print("\n🤖 Step 5: 加载模型")
print("-"*40)

import subprocess
subprocess.run("pip install psutil -q", shell=True, capture_output=True)
import psutil
import builtins
builtins.psutil = psutil

import torch
gc.collect()
torch.cuda.empty_cache()

print(f"加载 {MODEL_SIZE} 模型...")
print("⏳ 这可能需要几分钟...")

from unsloth import FastLanguageModel

# 先加载基座模型
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=1024,
    dtype=None,
    load_in_4bit=True,
)

# 加载 LoRA adapter
from peft import PeftModel
print(f"加载 LoRA adapter: {found_checkpoint}")
model = PeftModel.from_pretrained(model, found_checkpoint)

print("✅ 模型加载完成")

gc.collect()
torch.cuda.empty_cache()

# =============================================================================
# Step 6: GGUF 转换
# =============================================================================
print("\n📦 Step 6: GGUF 转换")
print("-"*40)

GGUF_DIR = "model_gguf"

print(f"开始 GGUF 转换 ({MODEL_SIZE}, q4_k_m)...")
print("⏳ 这可能需要 10-20 分钟,请耐心等待...")

start_time = time.time()

try:
    # 合并 LoRA 到基座模型
    print("合并 LoRA weights...")
    model = model.merge_and_unload()
    
    gc.collect()
    torch.cuda.empty_cache()
    
    # GGUF 转换
    print("转换为 GGUF...")
    model.save_pretrained_gguf(
        GGUF_DIR,
        tokenizer,
        quantization_method="q4_k_m"
    )
    
    elapsed = time.time() - start_time
    print(f"✅ GGUF 转换完成! 耗时: {elapsed/60:.1f} 分钟")
    
    # 验证
    gguf_files = [f for f in os.listdir(GGUF_DIR) if f.endswith(".gguf")]
    if gguf_files:
        gguf_file = gguf_files[0]
        gguf_path = os.path.join(GGUF_DIR, gguf_file)
        gguf_size = os.path.getsize(gguf_path) / 1024**3
        print(f"   文件: {gguf_file}")
        print(f"   大小: {gguf_size:.2f} GB")
    else:
        print("❌ GGUF 文件未生成")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ GGUF 转换失败: {e}")
    print("\n💡 可以尝试手动转换,参考 llama.cpp")
    sys.exit(1)

# =============================================================================
# Step 7: 上传 GGUF
# =============================================================================
print("\n📤 Step 7: 上传 GGUF")
print("-"*40)

gguf_path = os.path.join(GGUF_DIR, gguf_file)
remote_name = f"wwise-brain-{MODEL_SIZE.lower()}-q4_k_m.gguf"

print(f"上传 {gguf_size:.2f} GB 文件...")
print("⏳ 大文件上传可能需要 10-30 分钟...")

for attempt in range(MAX_RETRIES):
    try:
        print(f"尝试 {attempt + 1}/{MAX_RETRIES}...")
        
        api.upload_file(
            path_or_fileobj=gguf_path,
            path_in_repo=f"gguf/{remote_name}",
            repo_id=HF_MODEL_REPO,
            token=HF_TOKEN,
        )
        
        print("✅ GGUF 上传成功!")
        break
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        if attempt < MAX_RETRIES - 1:
            print("等待 30 秒后重试...")
            time.sleep(30)
        else:
            print(f"⚠️ GGUF 上传失败,本地文件保存在: {gguf_path}")

# =============================================================================
# Step 8: 上传 Modelfile
# =============================================================================
print("\n📄 Step 8: 上传 Modelfile")
print("-"*40)

modelfile_content = f'''FROM ./{remote_name}

TEMPLATE """<|im_start|>system
{{{{ .System }}}}<|im_end|>
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
"""

SYSTEM """你是一个专业的 Wwise 音频技术专家,精通 DSL 代码生成。根据用户的需求,生成符合 Wwise 工程规范的 DSL 代码。"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''

try:
    with open("Modelfile", "w") as f:
        f.write(modelfile_content)
    
    api.upload_file(
        path_or_fileobj="Modelfile",
        path_in_repo="gguf/Modelfile",
        repo_id=HF_MODEL_REPO,
        token=HF_TOKEN,
    )
    print("✅ Modelfile 上传成功!")
    
except Exception as e:
    print(f"⚠️ Modelfile 上传失败: {e}")

# =============================================================================
# Step 9: 最终验证
# =============================================================================
print("\n✅ Step 9: 最终验证")
print("-"*40)

try:
    files = list_repo_files(HF_MODEL_REPO, token=HF_TOKEN)
    
    checks = [
        ("adapter_config.json", "adapter_config.json" in files),
        ("adapter_model.safetensors", "adapter_model.safetensors" in files),
        (f"gguf/{remote_name}", f"gguf/{remote_name}" in files),
        ("gguf/Modelfile", "gguf/Modelfile" in files),
    ]
    
    print("\n📋 文件检查:")
    all_ok = True
    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"   {status} {name}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n" + "="*60)
        print("🎉 所有文件上传成功!")
        print("="*60)
    else:
        print("\n⚠️ 部分文件缺失")
        
except Exception as e:
    print(f"❌ 验证失败: {e}")

# =============================================================================
# 完成
# =============================================================================
print(f"""
{'='*60}
📦 模型地址: https://huggingface.co/{HF_MODEL_REPO}

🚀 本地部署 (Ollama):

   # 1. 下载文件
   wget https://huggingface.co/{HF_MODEL_REPO}/resolve/main/gguf/{remote_name}
   wget https://huggingface.co/{HF_MODEL_REPO}/resolve/main/gguf/Modelfile
   
   # 2. 创建模型
   ollama create wwise-brain -f Modelfile
   
   # 3. 运行
   ollama run wwise-brain

{'='*60}
""")
