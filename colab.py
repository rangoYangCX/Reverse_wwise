# -*- coding: utf-8 -*-
"""
MMO Engineering Brain - Ultimate One-Click Script
集成：数据清洗工厂 + 资深设计师重写 + 模型训练 + HF自动交付
"""

import os
import sys
import subprocess
import json
import torch
import shutil
import gc
import random
import re
import unicodedata
import numpy as np

# --- 🛠️ 0. 核心修复：注入 psutil (必须在所有 import 之前) ---
try:
    import psutil
    import builtins
    builtins.psutil = psutil
    print("✅ 环境自检：psutil 注入成功。")
except ImportError:
    print("⚠️ 环境自检：正在预装 psutil...")
    subprocess.check_call("pip install psutil", shell=True)
    import psutil
    import builtins
    builtins.psutil = psutil

def clean_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

# --- 1. 用户配置区 ---
RAW_DATA_FILE = "wwise_training_data_v7.jsonl" # 你的原始上传文件
CLEAN_DATA_FILE = "final_train_data.jsonl"    # 清洗生成的目标文件
HF_TOKEN = "HF_TOKEN"
HF_REPO_NAME = "chengxuanyyy/Wwise-Engineering-Brain"
QUANTIZATION_METHOD = "q4_k_m"

# --- 2. 数据工厂：清洗与重写模块 ---
# (这里集成了之前的 generate_action_data.py 逻辑)

DESIGNER_PHRASES = {
    "footstep_system_setup": [
        "搭建一套标准的主角脚步声逻辑，根节点叫 {name}，记得把定位(Positioning)覆盖打开。",
        "给主角整一套脚步声架构 {name}，挂在 {parent} 下面。衰减要设好，走 OutputBus 路由。",
        "初始化主角的脚步系统 {name}。技术要求：开启 OverridePositioning，并关联到材质 Switch Group。"
    ],
    "footstep_material_switch": [
        "现在处理 {material} 材质的脚步声逻辑。在 {parent} 下建个 SwitchContainer 叫 {name}。",
        "新增一种地表材质：{material}。创建对应的容器 {name}，别忘了把 Switch Group 连上。",
        "配置 {material} 材质的 Switch 逻辑，容器命名为 {name}，信号走 HostPlayerSkill 总线。"
    ],
    "footstep_sfx_assets": [
        "导入一批 {material} 的脚步声素材 {name}，要那种{adjective}的感觉。",
        "填充 {parent} 容器的内容，创建一组随机脚步声 {name}。听感要{adjective}一点。",
        "把美术给的 {material} 脚步声 {name} 导进去，放到 {parent} 下面，做成 Random 容器。"
    ],
    "default": [
        "创建 {type} 对象 {name}，父级是 {parent}。",
        "在 {parent} 节点下新增 {name}。",
        "实现 {name} 的逻辑配置，类型为 {type}。"
    ]
    # ... (为了脚本简洁，这里保留核心话术，模型会自动举一反三)
}
ADJECTIVES = ["湿漉漉", "清脆", "厚重", "沉闷", "尖锐", "有弹性", "拖沓", "利落", "带金属感"]

def nuclear_clean_text(text):
    """核弹级清洗：去除全角字符和乱码"""
    if not text: return ""
    char_map = {
        '“': '"', '”': '"', '‘': "'", '’': "'", '：': ':', '（': '(', '）': ')', 
        '，': ',', '；': ';', '　': ' ', '。': '.', '、': ',', '？': '?', '！': '!', '【': '[', '】': ']'
    }
    for k, v in char_map.items(): text = text.replace(k, v)
    text = unicodedata.normalize('NFKC', text)
    pattern = re.compile(r'[^\u0009\u000A\u000D\u0020-\u007E\u4E00-\u9FFF]')
    return pattern.sub('', text).strip()

def analyze_wwise_code(code_str):
    """简化的意图分析器"""
    lines = code_str.split('\n')
    first_line = lines[0]
    match = re.search(r'CREATE\s+(\w+)\s+"([^"]+)"\s+UNDER\s+"([^"]+)"', first_line)
    params = {}
    if match:
        obj_type, obj_name, parent_name = match.groups()
        params = {"type": obj_type, "name": obj_name, "parent": parent_name, "adjective": random.choice(ADJECTIVES)}
    else:
        return "default", {"name": "Unknown", "type": "Unknown", "parent": "Unknown"}
    
    name_lower = params["name"].lower()
    if "footstep" in name_lower:
        if params["type"] == "ActorMixer": return "footstep_system_setup", params
        if params["type"] == "SwitchContainer": 
            params["material"] = "某种"
            return "footstep_material_switch", params
        if params["type"] in ["Sound", "RandomSequenceContainer"]: 
            params["material"] = "通用"
            return "footstep_sfx_assets", params
    return "default", params

def prepare_data():
    print(f"\n🏭 启动数据工厂：正在清洗并重写 {RAW_DATA_FILE}...")
    if not os.path.exists(RAW_DATA_FILE):
        sys.exit(f"❌ 错误：找不到 {RAW_DATA_FILE}，请先上传！")
    
    count = 0
    with open(CLEAN_DATA_FILE, 'w', encoding='utf-8') as outfile:
        with open(RAW_DATA_FILE, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in infile:
                line = nuclear_clean_text(line)
                if not line: continue
                try:
                    data = json.loads(line)
                    code_output = data.get("output", "")
                    if not code_output: continue
                    
                    # 生成资深话术
                    intent, params = analyze_wwise_code(code_output)
                    templates = DESIGNER_PHRASES.get(intent, DESIGNER_PHRASES["default"])
                    new_instruction = random.choice(templates).format(**params)
                    
                    # 再次清洗生成的内容，确保万无一失
                    data["instruction"] = nuclear_clean_text(new_instruction)
                    data["input"] = nuclear_clean_text(f"工程上下文: {intent} | 对象: {data.get('meta', {}).get('root_type', 'Object')}")
                    
                    outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                    count += 1
                except Exception:
                    continue
    print(f"✅ 数据准备完成！已生成 {count} 条高质量训练数据 -> {CLEAN_DATA_FILE}")

# --- 3. 环境与训练配置 ---
print("="*50)
print("🚀 启动 MMO 工程大脑 - 终极训练流水线")
print("="*50)

# 执行数据准备
prepare_data()
clean_memory()

# 安装依赖
def install_package(command):
    try:
        subprocess.check_call(command, shell=True)
    except Exception:
        pass

print("\n📦 正在配置训练环境...")
install_package("pip install psutil huggingface_hub")
install_package("pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"")
install_package("pip install unsloth_zoo") # 显式安装 zoo 防止报错
install_package("pip install --no-deps xformers trl peft accelerate bitsandbytes")

try:
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from unsloth import is_bfloat16_supported
    from datasets import Dataset
    from huggingface_hub import HfApi
except ImportError:
    sys.exit("❌ 依赖安装失败，请重启运行时。")

# 加载模型
model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
max_seq_length = 2048

print(f"\n🚀 加载基座模型: {model_name}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = model_name,
    max_seq_length = max_seq_length,
    dtype = None,
    load_in_4bit = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# 准备 Alpaca 格式
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input, output) + tokenizer.eos_token
        texts.append(text)
    return { "text" : texts, }

# 加载清洗后的数据
dataset = Dataset.from_json(CLEAN_DATA_FILE)
dataset = dataset.map(formatting_prompts_func, batched = True)

# --- 4. 训练执行 (参数已针对 6000条+ 数据优化) ---
print("\n⚔️ 训练开始...")

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 20,          # 增加预热
        max_steps = 1500,           # 关键调整：提升到 1500 步以适应大量数据
        learning_rate = 1e-4,       # 关键调整：降低学习率，防止过拟合
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 5,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "cosine", # 使用余弦退火策略
        seed = 3407,
        output_dir = "outputs",
        report_to = "none",
    ),
)

trainer.train()

# --- 5. 交付流水线 ---
print("\n" + "="*50)
print("🏁 训练完成，启动自动化交付...")
print("="*50)

# 上传 LoRA
try:
    print(f"☁️ 同步 LoRA 至 HF: {HF_REPO_NAME}...")
    model.push_to_hub(HF_REPO_NAME, token = HF_TOKEN)
    tokenizer.push_to_hub(HF_REPO_NAME, token = HF_TOKEN)
except Exception as e:
    print(f"⚠️ LoRA 上传警告: {e}")

# 转换并上传 GGUF
print(f"\n📦 执行 GGUF 转换 ({QUANTIZATION_METHOD})...")
clean_memory()
try:
    output_dir = "model_gguf"
    model.save_pretrained_gguf(output_dir, tokenizer, quantization_method = QUANTIZATION_METHOD)
    
    gguf_files = [f for f in os.listdir(output_dir) if f.endswith(".gguf")]
    if gguf_files:
        local_gguf_path = os.path.join(output_dir, gguf_files[0])
        print(f"🎯 文件生成: {local_gguf_path}")
        
        print(f"🚀 上传大文件到 Hugging Face...")
        api = HfApi()
        api.upload_file(
            path_or_fileobj=local_gguf_path,
            path_in_repo=gguf_files[0],
            repo_id=HF_REPO_NAME,
            token=HF_TOKEN
        )
        print("✅ GGUF 上传成功！")
        print(f"🔗 下载地址: https://huggingface.co/{HF_REPO_NAME}/tree/main")
    else:
        print("❌ 未生成 GGUF 文件。")
except Exception as e:
    print(f"❌ 交付错误: {e}")

print("\n🎉 大师级训练流程结束。")