#!/usr/bin/env python3
"""
提取15个完整历史对话 - 使用精确的session ID和消息匹配
避免污染：只搜索11月6日之前的JSONL文件
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 15个对话的精确定位信息
# 格式: (名称, 第一句关键词用于查找JSONL, 第一句完整, 最后一句)
conversations = [
    # October conversations
    ("vix-spx-vega", "2025-10-27", "VIX 期权的 delta", None),
    ("french-review", "2025-10-28", "今天我想复习一下我之前学的法语", None),
    ("csharp-learning", "2025-10-28", "C#问题：我想测试", None),
    ("risk-scenario", "2025-10-28", "什么是金融中计算Risk Scenario", None),
    ("options-greeks", "2025-10-29", "我的朋友问了我这个问题", None),
    ("csharp-review", "2025-10-30", "今天我想复习编程", None),
    ("french-1453", "2025-10-30", "今天继续学法语1453", None),
    ("capital-market", "2025-10-30", "资本市场定价本质上是不是只有两种", None),

    # November conversations
    ("desire-driven", "2025-11-02", "我最近发现这个世界的经济其实是欲望", None),
    ("french-grammar", "2025-11-03", "我想学法语1453，从头学起", None),
    ("fx-forward", "2025-11-03", "什么是FX Forward中的Primary Depo Rate", None),
    ("fx-delta", "2025-11-03", "在Scenario Analysis中FXDeltaBase", None),
    ("nds-fx", "2025-11-03", "interest:NDS trade的支付货币", None),
    ("bloomberg", "2025-11-04", "什么是Bloomberg's OVDV", None),
    ("epad-jkm", "2025-11-05", "EPAD STO Power Base", None),
]

def find_jsonl_for_date(date_str):
    """Find all JSONL files modified on specific date"""
    cmd = f"find ~/.claude/projects/-root-knowledge-system/ -name '*.jsonl' -newermt '{date_str} 00:00' ! -newermt '{date_str} 23:59' -type f"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [Path(f) for f in result.stdout.strip().split('\n') if f]

def find_session_with_text(jsonl_files, search_text):
    """Find JSONL file containing specific text"""
    for jsonl in jsonl_files:
        try:
            with open(jsonl, 'r', encoding='utf-8') as f:
                content = f.read(50000)  # Read first 50KB
                if search_text in content:
                    return jsonl.stem  # Return session ID
        except:
            continue
    return None

def extract_with_archiver(session_id, first_msg, last_msg=None):
    """Use chat_archiver to extract conversation"""
    cmd = [
        'python3', 'scripts/services/chat_archiver.py',
        '--session-id', session_id,
        '--first-message', first_msg
    ]
    if last_msg:
        cmd.extend(['--last-message', last_msg])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        output_file = result.stdout.strip().split('\n')[-1]  # Last line is file path
        return output_file
    return None

def main():
    print("🔄 自动提取15个完整历史对话")
    print("=" * 80)

    success = []
    failed = []

    for name, date, first_key, last_msg in conversations:
        print(f"\n📝 {name} ({date})")
        print(f"   搜索: {first_key[:30]}...")

        # Find JSONL files from that date
        jsonl_files = find_jsonl_for_date(date)
        if not jsonl_files:
            print(f"   ❌ 该日期无JSONL文件")
            failed.append(name)
            continue

        print(f"   找到 {len(jsonl_files)} 个JSONL文件")

        # Find session containing this conversation
        session_id = find_session_with_text(jsonl_files, first_key)
        if not session_id:
            print(f"   ❌ 未找到包含该对话的JSONL")
            failed.append(name)
            continue

        print(f"   ✓ Session: {session_id}")

        # Extract with chat_archiver
        output = extract_with_archiver(session_id, first_key, last_msg)
        if output:
            print(f"   ✅ 提取成功: {output}")
            success.append((name, output))
        else:
            print(f"   ❌ 提取失败")
            failed.append(name)

    print("\n" + "=" * 80)
    print(f"📊 结果: ✅ {len(success)}/15 成功")

    if success:
        print("\n成功提取的对话:")
        for name, path in success:
            print(f"  - {name}: {path}")

    if failed:
        print(f"\n失败的对话: {', '.join(failed)}")

if __name__ == "__main__":
    main()