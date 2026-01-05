#!/bin/bash
# Auto-generated script to re-extract all 15 conversations
set -e

TOTAL=15
SUCCESS=0
FAILED=()

echo "▶️  [1/15] VIX Delta SPX Vega..."
if bash scripts/reextract_one_conversation.sh "vix-spx-vega-2025-10-27"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-27)"
else
    FAILED+=("vix-spx-vega-2025-10-27")
    echo "❌ Failed"
fi

echo "▶️  [2/15] C# Learning..."
if bash scripts/reextract_one_conversation.sh "csharp-learning-ba-python-2025-10-28"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-28)"
else
    FAILED+=("csharp-learning-ba-python-2025-10-28")
    echo "❌ Failed"
fi

echo "▶️  [3/15] French Review..."
if bash scripts/reextract_one_conversation.sh "french-review-session-2025-10-28"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-28)"
else
    FAILED+=("french-review-session-2025-10-28")
    echo "❌ Failed"
fi

echo "▶️  [4/15] Risk Scenario..."
if bash scripts/reextract_one_conversation.sh "risk-scenario-time-ladder-2025-10-28"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-28)"
else
    FAILED+=("risk-scenario-time-ladder-2025-10-28")
    echo "❌ Failed"
fi

echo "▶️  [5/15] Options Greeks..."
if bash scripts/reextract_one_conversation.sh "options-greeks-time-scenario-2025-10-29"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-29)"
else
    FAILED+=("options-greeks-time-scenario-2025-10-29")
    echo "❌ Failed"
fi

echo "▶️  [6/15] C# Review..."
if bash scripts/reextract_one_conversation.sh "csharp-review-early-exit-2025-10-30"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-30)"
else
    FAILED+=("csharp-review-early-exit-2025-10-30")
    echo "❌ Failed"
fi

echo "▶️  [7/15] Capital Market Pricing..."
if bash scripts/reextract_one_conversation.sh "capital-market-pricing-paradigms-2025-10-30"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-30)"
else
    FAILED+=("capital-market-pricing-paradigms-2025-10-30")
    echo "❌ Failed"
fi

echo "▶️  [8/15] French 1453 Vocabulary..."
if bash scripts/reextract_one_conversation.sh "french-1453-vocab-20251030"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-10-30)"
else
    FAILED+=("french-1453-vocab-20251030")
    echo "❌ Failed"
fi

echo "▶️  [9/15] Economic Growth..."
if bash scripts/reextract_one_conversation.sh "desire-driven-growth-2025-11-02"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-02)"
else
    FAILED+=("desire-driven-growth-2025-11-02")
    echo "❌ Failed"
fi

echo "▶️  [10/15] French Grammar..."
if bash scripts/reextract_one_conversation.sh "french-grammar-session-2025-11-03"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-03)"
else
    FAILED+=("french-grammar-session-2025-11-03")
    echo "❌ Failed"
fi

echo "▶️  [11/15] FX Delta..."
if bash scripts/reextract_one_conversation.sh "fx-delta-currency-conventions-2025-11-03"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-03)"
else
    FAILED+=("fx-delta-currency-conventions-2025-11-03")
    echo "❌ Failed"
fi

echo "▶️  [12/15] FX Forward..."
if bash scripts/reextract_one_conversation.sh "fx-forward-primary-depo-rate-2025-11-03"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-03)"
else
    FAILED+=("fx-forward-primary-depo-rate-2025-11-03")
    echo "❌ Failed"
fi

echo "▶️  [13/15] NDS FX Options..."
if bash scripts/reextract_one_conversation.sh "nds-fx-options-payment-currency-2025-11-03"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-03)"
else
    FAILED+=("nds-fx-options-payment-currency-2025-11-03")
    echo "❌ Failed"
fi

echo "▶️  [14/15] Bloomberg OVDV..."
if bash scripts/reextract_one_conversation.sh "bloomberg-ovdv-conversation-2025-11-04"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-04)"
else
    FAILED+=("bloomberg-ovdv-conversation-2025-11-04")
    echo "❌ Failed"
fi

echo "▶️  [15/15] EPAD JKM..."
if bash scripts/reextract_one_conversation.sh "epad-jkm-energy-derivatives-2025-11-05"; then
    SUCCESS=$((SUCCESS + 1))
    echo "✅ Done (2025-11-05)"
else
    FAILED+=("epad-jkm-energy-derivatives-2025-11-05")
    echo "❌ Failed"
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary: $SUCCESS/$TOTAL successful"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed: ${FAILED[@]}"
fi
