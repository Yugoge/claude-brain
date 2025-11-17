#!/usr/bin/env python3
"""
Batch Re-extract Conversations with Chat Archiver
Re-extracts the 15 key conversations using first/last message matching
"""

import subprocess
import sys
from pathlib import Path

# Conversation extraction specs
CONVERSATIONS = [
    {
        'name': 'capital-market-pricing-paradigms-2025-10-30',
        'first': '资本市场定价本质上是不是只有两种，第一种靠curve，基于折现现金流；第二种靠vol，基于Black家族模型',
        'last': '[User approved archival]',
        'date': '2025-10-30',
    },
    # {
    #     'name': 'csharp-learning-ba-python-2025-10-28',
    #     'first': 'C#问题：我想测试在src/Common/utils/Utilities.cs文件中的一个function',
    #     'last': None,  # Need to check - conversation ends with test results
    #     'date': '2025-10-28',
    # },
    {
        'name': 'csharp-review-early-exit-2025-10-30',
        'first': '今天我想复习编程',
        'last': '明白了！继续 Rem 3/7',
        'date': '2025-10-30',
    },
    {
        'name': 'french-1453-vocabulary-2025-10-30',
        'first': '今天继续学法语1453',
        'last': '上面新建的rems有误,不符合标准格式。你重新创建',
        'date': '2025-10-30',
    },
    {
        'name': 'french-review-session-2025-10-28',
        'first': '今天我想复习一下我之前学的法语。考考我',
        'last': '🎉 **PARFAIT! Absolutely perfect!**',
        'date': '2025-10-28',
    },
    {
        'name': 'options-greeks-time-scenario-2025-10-29',
        'first': '我的朋友问了我这个问题，但是我是一个金融民工，我就是农民出身，贫农背景，我应该如何理解他说的话？这是关于Time Sce',
        'last': '[Launched analyst to clarify Greeks definitions]',
        'date': '2025-10-29',
    },
    {
        'name': 'risk-scenario-time-ladder-2025-10-28',
        'first': '> "什么是金融中计算Risk Scenario Perturbation Analysis的时候的time ladde',
        'last': '> "但是我不理解time scenario到底是怎么计算的啊？是对比不同tenor和valuation date之间不',
        'date': '2025-10-28',
    },
    {
        'name': 'vix-spx-vega-2025-10-27',
        'first': 'VIX 期权的 delta 和 SPX 期权的 vega 有什么区别和联系？它们都衡量波动率敏感度，但似乎用的是不同的希',
        'last': "I'll analyze this conversation and extract the key concepts",
        'date': '2025-10-27',
    },
    {
        'name': 'bloomberg-ovdv-2025-11-04',
        'first': "什么是Bloomberg's OVDV",
        'last': '好的结束ask',
        'date': '2025-11-04',
    },
    {
        'name': 'desire-driven-economic-growth-2025-11-02',
        'first': '我最近发现这个世界的经济其实是欲望和现实的差距驱动的。一个地区的人民欲望越强,现实越穷,创造财富的激励越强,经济增长就快',
        'last': '1. 保存 - 提取关键概念并归档',
        'date': '2025-11-02',
    },
    {
        'name': 'french-grammar-negation-2025-11-03',
        'first': '我想学法语1453，从头学起（但跳过发音和过于基础的词语部分），我在巴黎两年虽然说英语但是我还是有基础打招呼词汇基础的哈',
        'last': '好的，来做一个快速三步练习（只提问不讲解，等你作答再点评）：',
        'date': '2025-11-03',
    },
    {
        'name': 'fx-delta-currency-conventions-2025-11-03',
        'first': '在Scenario Analysis中FXDeltaBase和FXDeltaPremium的全部区别是？FX Curre',
        'last': '[AI reorganized user\'s logic into clear systematic format wi',
        'date': '2025-11-03',
    },
    {
        'name': 'fx-forward-primary-depo-rate-2025-11-03',
        'first': '什么是FX Forward中的Primary Depo Rate？',
        'last': '你说得**完全正确**!我的表述确实有误导性,感谢你的纠正。',
        'date': '2025-11-03',
    },
    {
        'name': 'nds-fx-options-payment-currency-2025-11-03',
        'first': 'interest:NDS trade的支付货币应该是Product ccy还是Primary ccy，考虑一个USD:C',
        'last': '非常好的问题！让我们来看看FX Option的情况：',
        'date': '2025-11-03',
    },
    {
        'name': 'epad-vs-jkm-2025-11-05',
        'first': 'EPAD STO Power Base AR MTH OMX和ICE JKM Fut的区别是？',
        'last': None,  # Short conversation, may not need last message filter
        'date': '2025-11-05',
    },
]

def extract_conversation(conv_spec):
    """Extract a single conversation using chat_archiver"""
    name = conv_spec['name']
    first = conv_spec['first']
    last = conv_spec['last']

    if not first:
        print(f"⚠️  Skipping {name}: No first message specified")
        return None

    print(f"\n{'='*70}")
    print(f"Extracting: {name}")
    print(f"First: {first[:60]}...")
    if last:
        print(f"Last: {last[:60]}...")

    # Build command
    cmd = ['python3', 'scripts/services/chat_archiver.py']
    cmd.extend(['--first-message', first])
    if last:
        cmd.extend(['--last-message', last])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            output_file = result.stdout.strip()
            print(f"✅ Extracted to: {output_file}")

            # Count role labels for validation
            with open(output_file, 'r') as f:
                content = f.read()

            user_count = content.count('\n### User\n')
            assistant_count = content.count('\n### Assistant\n')
            subagent_count = content.count('\n### Subagent')

            print(f"   User: {user_count}, Assistant: {assistant_count}, Subagent: {subagent_count}")

            # Basic validation
            if assistant_count < user_count * 0.5:
                print(f"   ⚠️  WARNING: Low assistant count (possible attribution issue)")

            return output_file
        else:
            print(f"❌ Failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout extracting {name}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🚀 Batch Re-extraction of 15 Conversations")
    print("="*70)

    extracted = []
    failed = []

    for conv in CONVERSATIONS:
        result = extract_conversation(conv)
        if result:
            extracted.append((conv['name'], result))
        else:
            failed.append(conv['name'])

    print(f"\n\n{'='*70}")
    print(f"📊 Summary")
    print(f"   ✅ Extracted: {len(extracted)}")
    print(f"   ❌ Failed: {len(failed)}")

    if failed:
        print(f"\nFailed conversations:")
        for name in failed:
            print(f"   - {name}")

    if extracted:
        print(f"\nExtracted files:")
        for name, path in extracted:
            print(f"   - {name} → {path}")

if __name__ == "__main__":
    main()
