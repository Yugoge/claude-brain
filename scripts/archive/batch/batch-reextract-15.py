#!/usr/bin/env python3
"""
批量重新提取15个历史对话
使用修复后的chat_archiver，使用日期+first_message+last_message双重精确匹配
"""

import sys
import json
from pathlib import Path

sys.path.append('scripts/services')
from chat_archiver import find_project_conversations, extract_and_save

# Get all JSONL files with metadata (date + file)
all_jsonl = find_project_conversations()

jsonl_by_date = {}
for jsonl_file in all_jsonl:
    try:
        with open(jsonl_file, 'r') as f:
            first_line = f.readline()
            if not first_line.strip():
                continue
            first_event = json.loads(first_line)
            timestamp = first_event.get('timestamp', '')
            if timestamp:
                date = timestamp[:10]
                if jsonl_file.stat().st_size > 10240:
                    if date not in jsonl_by_date:
                        jsonl_by_date[date] = []
                    jsonl_by_date[date].append(jsonl_file)
    except:
        continue

# 15 conversations with date + first_message + last_message (for precise dual matching)
# NOTE: These are the ACTUAL first/last user messages from JSONL (after command-args extraction)
conversations = [
    ("capital-market", "2025-10-30", "资本市场定价本质上是不是只有两种，第一种靠curve", "[User approved archival]"),
    ("vix-spx", "2025-10-27", "VIX 期权的 delta 和 SPX 期权的 vega 有什么关系", "Perfect! This conversation should be archived"),
    ("french-review", "2025-10-28", "Bonjour, Nicolas! Je suis content de te revoir", "Vous m'avez manqué"),
    ("csharp-learning", "2025-10-28", "C#问题：我想测试在src/Common/utils/Utilities", "为什么结果没有任何变化"),
    ("options-greeks", "2025-10-29", "好的，目前我给这个朋友写的修复计划是", "在BB模型中，所有的theta都是time value change吗"),
    ("csharp-review", "2025-10-30", "你确定吗，我怎么觉得我有编程的rems", "明白了！继续 Rem 3/7"),
    ("french-1453", "2025-10-30", "今天继续学法语1453", "上面新建的rems有误,不符合标准格式"),
    ("desire-driven", "2025-11-02", "比如中国,中国人就是以前很穷,但是很多有就是赚钱然后改善生活的欲望就很强啊", "1. 保存 - 提取关键概念并归档"),
    ("french-grammar", "2025-11-03", "从第 1 课重新梳理，但自动跳过发音与过基础内容", "疑问句：est-ce que / 倒装 / 语调"),
    ("fx-delta", "2025-11-03", "但是问题是目前我们的计算是无论计算Premium还是Base我的程序都会把CCYPair的两个CCY的Delta都算出来", "[User then provided complete systematic decision logic via /ultrathink command]"),
    ("fx-forward", "2025-11-03", "什么是FX Forward中的Primary Depo Rate", "我不喜欢你用的利息成本这个词,应该是USD的利息收益更高"),
    ("nds-fx", "2025-11-03", "interest:NDS trade的支付货币", "好的我懂你的意思了。那么一个FX Option USD:CNH的product ccy和settlement ccy没区别了吧"),
    ("bloomberg", "2025-11-04", "什么是Bloomberg's OVDV", "好的结束ask"),
    ("epad-jkm", "2025-11-05", "EPAD STO Power Base AR MTH OMX和ICE JKM Fut的区别是", "read ECONNRESET"),
]

print(f"🔄 使用日期+first+last双重匹配，从历史JSONL中提取15个对话\n")
print("=" * 80)

success_count = 0
failed = []

for i, (name, target_date, first_msg, last_msg) in enumerate(conversations, 1):
    print(f"\n[{i}/15] 📄 {name}")
    print(f"   日期: {target_date}")
    print(f"   First: {first_msg[:40]}...")
    print(f"   Last:  {last_msg[:40]}...")

    # Only search JSONL files from the target date
    if target_date not in jsonl_by_date:
        print(f"   ❌ 该日期没有JSONL文件")
        failed.append(name)
        continue

    found = False
    for jsonl_file in jsonl_by_date[target_date]:
        try:
            output = extract_and_save(
                jsonl_file,
                quiet=True,
                first_message=first_msg[:60],
                last_message=last_msg[:60]
            )
            if output:
                print(f"   ✅ {output.name}")
                success_count += 1
                found = True
                break
        except Exception as e:
            continue

    if not found:
        print(f"   ❌ 在{len(jsonl_by_date[target_date])}个文件中未找到匹配")
        failed.append(name)

print("\n" + "=" * 80)
print(f"📊 结果: ✅ {success_count} | ❌ {len(failed)} | 📋 总计 15")
if failed:
    print(f"\n⚠️  失败列表: {', '.join(failed)}")
print("=" * 80)
