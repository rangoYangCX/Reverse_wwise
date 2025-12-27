#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【上传数据集到 HuggingFace】
使用方法：
    python upload_dataset_to_hf.py final_training_ascii.jsonl
"""

import os
import sys
from huggingface_hub import HfApi, create_repo

# ----- 配置 -----
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    print("请设置环境变量 HF_TOKEN 或手动输入")
    # 仅本地测试时临时手动输入，不要提交
    # HF_TOKEN = input("Token: ")
HF_DATASET_REPO = "chengxuanyyy/wwise-dsl-training-data"

def main():
    if len(sys.argv) < 2:
        print("用法: python upload_dataset_to_hf.py <文件路径>")
        print("示例: python upload_dataset_to_hf.py final_training_ascii.jsonl")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    file_name = os.path.basename(file_path)
    
    print("=" * 50)
    print("📤 上传数据集到 HuggingFace")
    print("=" * 50)
    print(f"   文件: {file_name}")
    print(f"   大小: {file_size:.1f} MB")
    print(f"   目标: {HF_DATASET_REPO}")
    print("=" * 50)
    
    api = HfApi(token=HF_TOKEN)
    
    # 创建仓库（如果不存在）
    try:
        create_repo(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=HF_TOKEN,
            exist_ok=True
        )
        print(f"✅ 仓库已就绪: {HF_DATASET_REPO}")
    except Exception as e:
        print(f"⚠️ 创建仓库: {e}")
    
    # 上传文件
    print(f"\n📤 上传中...")
    try:
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=file_name,
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=HF_TOKEN,
        )
        print(f"\n✅ 上传成功!")
        print(f"   URL: https://huggingface.co/datasets/{HF_DATASET_REPO}")
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
