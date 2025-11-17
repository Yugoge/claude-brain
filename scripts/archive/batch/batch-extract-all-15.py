#!/usr/bin/env python3
"""
批量提取所有15个历史对话
使用找到的正确JSONL文件和精确的first_message匹配
"""

import sys
import json
from pathlib import Path

sys.path.append('scripts/services')
from chat_archiver import find_project_conversations, extract_and_save

# Map of conversations to their JSONL files and first messages
# Based on actual search results
conversations = [
    # Found via /ask command pattern search
    ("capital-market", "38f755bb-f2e9-4128-8f24-91a3ce4a64d8.jsonl", "资本市场定价本质上是不是只有两种"),
    ("fx-forward", "6140ad5d-bbd0-44b4-92f6-eea4d91af575.jsonl", "什么是FX Forward中的Primary Depo Rate"),

    # Found via direct text search
    ("french-review", "eca447d0-58e6-4bed-b927-d13115b9e25b.jsonl", "今天我想复习一下我之前学的法语"),
    ("csharp-learning", "f8c02eb8-6fd6-4e72-a719-012039bd2782.jsonl", "C#问题：我想测试在src/Common/utils/Utilities"),
    ("options-greeks", "eca447d0-58e6-4bed-b927-d13115b9e25b.jsonl", "我的朋友问了我这个问题，但是我是一个金融民工"),
    ("csharp-review", "eca447d0-58e6-4bed-b927-d13115b9e25b.jsonl", "今天我想复习编程"),
    ("french-1453", "f3f40e12-7844-429e-b4f1-0fff019ec029.jsonl", "今天继续学法语1453"),
    ("desire-driven", "50304d08-39be-4e3d-a553-3544ee626843.jsonl", "我最近发现这个世界的经济其实是欲望和现实的差距驱动"),
    ("french-grammar", "47b05895-b7a1-425c-b8be-fb16e2f9db3f.jsonl", "我想学法语1453，从头学起"),
    ("fx-delta", "f8c02eb8-6fd6-4e72-a719-012039bd2782.jsonl", "在Scenario Analysis中FXDeltaBase和FXDeltaPremium"),
    ("nds-fx", "f8c02eb8-6fd6-4e72-a719-012039bd2782.jsonl", "interest:NDS trade的支付货币"),
    ("epad-jkm", "6697afa1-b240-4682-93bb-cc64e8181b82.jsonl", "EPAD STO Power Base AR MTH OMX"),

    # Found via keyword search
    ("vix-spx", "e2a42542-fa00-4355-9e2d-723014791669.jsonl", "VIX 期权的 delta 和 SPX 期权的 vega"),
    ("bloomberg", "a3458a9e-5660-45dd-806d-f9b3d10d4465.jsonl", "什么是Bloomberg's OVDV"),
]

# Find remaining JSONL files
all_jsonl = find_project_conversations()
jsonl_dict = {jf.name: jf for jf in all_jsonl}

print("🔄 批量提取15个历史对话\n")
print("=" * 80)

# First, try to find missing ones
for name, jsonl_name, first_msg in conversations:
    if jsonl_name is None:
        print(f"\n🔍 Searching for {name}: '{first_msg[:40]}...'")
        found = False
        for jsonl_file in all_jsonl:
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if first_msg in content and jsonl_file.name != '5b640c2f-39ff-49ee-8c66-1f06cec1a0c1.jsonl':
                    print(f"  ✅ Found in: {jsonl_file.name}")
                    # Update the tuple (immutable, so need to recreate list)
                    idx = conversations.index((name, jsonl_name, first_msg))
                    conversations[idx] = (name, jsonl_file.name, first_msg)
                    found = True
                    break
            except:
                continue
        if not found:
            print(f"  ❌ Not found")

# Extract conversations
print("\n" + "=" * 80)
print("📂 Extracting conversations to chats/\n")

success_count = 0
failed = []

for i, (name, jsonl_name, first_msg) in enumerate(conversations, 1):
    print(f"[{i}/15] 📄 {name}")

    if jsonl_name is None:
        print(f"   ⚠️  No JSONL file found")
        failed.append(name)
        continue

    if jsonl_name not in jsonl_dict:
        print(f"   ❌ JSONL file not found: {jsonl_name}")
        failed.append(name)
        continue

    jsonl_file = jsonl_dict[jsonl_name]
    print(f"   Source: {jsonl_name}")
    print(f"   First: {first_msg[:40]}...")

    try:
        output = extract_and_save(
            jsonl_file,
            quiet=True,
            first_message=first_msg[:80]
        )
        if output:
            print(f"   ✅ Saved: {output.name}")
            success_count += 1
        else:
            print(f"   ❌ No matching conversation found")
            failed.append(name)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        failed.append(name)

print("\n" + "=" * 80)
print(f"📊 Results: ✅ {success_count} | ❌ {len(failed)} | 📋 Total 15")
if failed:
    print(f"\n⚠️  Failed: {', '.join(failed)}")
print("=" * 80)