#!/bin/bash
# Re-extract a single conversation using chat_archiver
# Usage: ./reextract_one_conversation.sh <conv_id>

set -e

CONV_ID="$1"
INDEX_FILE="chats/index.json"

if [ -z "$CONV_ID" ]; then
    echo "Usage: $0 <conversation_id>"
    exit 1
fi

# Extract metadata from index.json
TITLE=$(jq -r ".conversations[\"$CONV_ID\"].title" "$INDEX_FILE")
DATE=$(jq -r ".conversations[\"$CONV_ID\"].date" "$INDEX_FILE")
FILE=$(jq -r ".conversations[\"$CONV_ID\"].file" "$INDEX_FILE")

if [ "$TITLE" = "null" ]; then
    echo "❌ Conversation ID not found: $CONV_ID"
    exit 1
fi

echo "📖 Re-extracting: $TITLE"
echo "   Date: $DATE"
echo "   Target: $FILE"
echo

# Search for keywords in JSONL sessions
KEYWORDS=$(echo "$TITLE" | awk '{print $1, $2, $3}' | tr '[:upper:]' '[:lower:]')

# Find sessions modified around that date
TARGET_DATE=$(date -d "$DATE" +%s)
PROJECT_DIR="$HOME/.claude/projects/-root-knowledge-system"

echo "🔍 Searching sessions around $DATE..."

BEST_SESSION=""
BEST_SCORE=0

for session in "$PROJECT_DIR"/*.jsonl; do
    # Check if session modified within 7 days of target
    SESSION_TIME=$(stat -c %Y "$session")
    DAYS_DIFF=$(( (TARGET_DATE - SESSION_TIME) / 86400 ))
    DAYS_DIFF=${DAYS_DIFF#-}  # Absolute value

    if [ $DAYS_DIFF -le 7 ]; then
        # Count keyword matches (simple grep)
        SCORE=$(grep -oi "$KEYWORDS" "$session" 2>/dev/null | wc -l)

        if [ $SCORE -gt $BEST_SCORE ]; then
            BEST_SCORE=$SCORE
            BEST_SESSION="$session"
        fi
    fi
done

if [ -z "$BEST_SESSION" ]; then
    echo "❌ No matching session found"
    exit 1
fi

SESSION_ID=$(basename "$BEST_SESSION" .jsonl)
echo "✅ Found session: $SESSION_ID (score: $BEST_SCORE)"

# Extract using chat_archiver (full session, no range)
source venv/bin/activate && python scripts/services/chat_archiver.py --session-id "$SESSION_ID" 2>&1 | grep -v "^$"

# Find the extracted file (most recent .md)
EXTRACTED=$(ls -t chats/2025-*/*.md 2>/dev/null | head -1)

if [ -z "$EXTRACTED" ]; then
    echo "❌ Extraction failed - no file created"
    exit 1
fi

# Move to correct location
TARGET_PATH="$FILE"
mkdir -p "$(dirname "$TARGET_PATH")"
mv "$EXTRACTED" "$TARGET_PATH"

echo "✅ Extracted to: $TARGET_PATH"
