#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[交互式 HuggingFace 数据集上传工具]
功能：
1. 自动检测 HF_TOKEN，支持手动输入
2. 自动扫描当前目录下的 .jsonl 文件供选择
3. 支持自定义目标仓库
"""

import os
import sys
import glob
import time
from getpass import getpass
from huggingface_hub import HfApi, create_repo

# 默认配置
DEFAULT_REPO = "chengxuanyyy/wwise-dsl-training-data"

def clear_screen():
    # 简单的清屏，适配不同系统
    os.system('cls' if os.name == 'nt' else 'clear')

def get_hf_token():
    print("\n" + "="*50)
    print("🔑 步骤 1/3: 身份验证 (HuggingFace Token)")
    print("="*50)
    
    # 1. 尝试从环境变量获取
    token = os.getenv("HF_TOKEN")
    if token:
        print(f"✅ 检测到环境变量 HF_TOKEN (长度: {len(token)})")
        use_env = input("   是否使用该 Token? [Y/n]: ").strip().lower()
        if use_env in ['', 'y', 'yes']:
            return token
    
    # 2. 手动输入
    print("\n👉 请输入你的 HuggingFace Write Token")
    print("   (获取地址: https://huggingface.co/settings/tokens)")
    
    while True:
        # 使用 getpass 隐藏输入内容，保护 Token 不被旁人看到
        # 注意：在某些 Colab 环境 getpass 可能不显示输入框，如果遇到问题改用 input()
        try:
            user_token = getpass("   Token (输入时不显示): ").strip()
        except:
            user_token = input("   Token: ").strip()
            
        if user_token.startswith("hf_"):
            return user_token
        else:
            print("   ❌ Token 格式看似不正确 (通常以 'hf_' 开头)，请重试。")

def select_file():
    print("\n" + "="*50)
    print("📂 步骤 2/3: 选择数据集文件")
    print("="*50)
    
    # 扫描当前目录下的 jsonl 文件
    files = glob.glob("*.jsonl")
    # 按修改时间排序，最新的在前面
    files.sort(key=os.path.getmtime, reverse=True)
    
    if not files:
        print("⚠️  当前目录下没有找到 .jsonl 文件。")
        manual_path = input("👉 请手动输入文件路径: ").strip()
        if os.path.exists(manual_path):
            return manual_path
        else:
            print("❌ 文件不存在，程序退出。")
            sys.exit(1)
            
    print("在当前目录下发现以下文件：")
    for idx, f in enumerate(files):
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"   [{idx + 1}] {f}  ({size_mb:.2f} MB)")
    
    print(f"   [0] 手动输入其他路径")
    
    while True:
        choice = input("\n👉 请输入序号选择文件 (默认 1): ").strip()
        if choice == '':
            return files[0] # 默认选第一个（最新的）
        
        if choice.isdigit():
            idx = int(choice)
            if idx == 0:
                manual_path = input("   请输入文件路径: ").strip()
                if os.path.exists(manual_path):
                    return manual_path
                else:
                    print("   ❌ 文件不存在，请重试。")
                    continue
            elif 1 <= idx <= len(files):
                return files[idx - 1]
        
        print("   ❌ 输入无效，请输入列表中的序号。")

def confirm_repo():
    print("\n" + "="*50)
    print("☁️  步骤 3/3: 确认目标仓库")
    print("="*50)
    
    print(f"默认目标仓库: \033[1;36m{DEFAULT_REPO}\033[0m")
    change = input("👉 按 Enter 确认上传，或输入新的仓库 ID (格式 user/repo): ").strip()
    
    if change:
        return change
    return DEFAULT_REPO

def main():
    print("""
    ################################################
    #      Wwise 工程大脑 - 数据集上传助手 v2.0    #
    ################################################
    """)
    
    # 1. 获取 Token
    token = get_hf_token()
    
    # 2. 选择文件
    file_path = select_file()
    
    # 3. 确认仓库
    repo_id = confirm_repo()
    
    # 4. 执行上传
    print("\n" + "="*50)
    print("🚀 开始上传...")
    print("="*50)
    print(f"   文件: {os.path.basename(file_path)}")
    print(f"   目标: https://huggingface.co/datasets/{repo_id}")
    
    try:
        api = HfApi(token=token)
        
        # 确保仓库存在
        print("   ...检查/创建仓库中...")
        create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            exist_ok=True,
            private=True # 默认创建为私有仓库，安全第一
        )
        
        # 上传
        print("   ...正在传输数据 (请勿关闭)...")
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=os.path.basename(file_path),
            repo_id=repo_id,
            repo_type="dataset"
        )
        
        print("\n✅ 上传成功！")
        print(f"🔗 数据集地址: https://huggingface.co/datasets/{repo_id}/viewer")
        
    except Exception as e:
        print(f"\n❌ 上传失败: {str(e)}")
        print("   提示: 请检查 Token 权限是否包含 'write'，或者网络连接是否正常。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作。")