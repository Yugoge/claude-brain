#!/usr/bin/env bash
# Fix directory merging and numbering conflicts
set -e

BASE=/root/knowledge-system/knowledge-base
TOTAL_RENAMED=0

echo "===== TASK 1: Merge 0412-finance-banking-and-insurance into 0412-finance-banking-insurance ====="

SRC="$BASE/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-and-insurance"
DST="$BASE/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance"

# Get current max number in DST
MAX_DST=$(ls "$DST" | grep -E '^[0-9]+' | sed 's/^\([0-9]*\)-.*/\1/' | sort -n | tail -1)
echo "Current max in destination: $MAX_DST"

NEXT=$((10#$MAX_DST + 1))
TASK1_COUNT=0

for f in $(ls "$SRC" | grep -v '^INDEX.md$' | grep -v '^README.md$' | sort); do
    # Extract the part after NNN-
    SUFFIX="${f#*-}"
    NEW_NUM=$(printf "%03d" $NEXT)
    NEW_NAME="${NEW_NUM}-${SUFFIX}"
    echo "  Moving: $f -> $NEW_NAME"
    mv "$SRC/$f" "$DST/$NEW_NAME"
    NEXT=$((NEXT + 1))
    TASK1_COUNT=$((TASK1_COUNT + 1))
    TOTAL_RENAMED=$((TOTAL_RENAMED + 1))
done

echo "Task 1: Moved $TASK1_COUNT files"
echo "Removing empty source directory: $SRC"
rm -rf "$SRC"
echo ""

echo "===== TASK 2: Fix numbering conflicts ====="

fix_conflicts() {
    local dir="$1"
    local fulldir="$BASE/$dir"
    echo ""
    echo "--- Processing: $dir ---"

    # Find conflicting prefixes
    CONFLICTS=$(ls "$fulldir" | grep -E '^[0-9]+' | sed 's/^\([0-9]*\)-.*/\1/' | sort | uniq -d)

    if [ -z "$CONFLICTS" ]; then
        echo "  No conflicts found."
        return
    fi

    # Get max number currently in directory
    MAX=$(ls "$fulldir" | grep -E '^[0-9]+' | sed 's/^\([0-9]*\)-.*/\1/' | sort -n | tail -1)
    NEXT=$((10#$MAX + 1))
    DIR_COUNT=0

    for prefix in $CONFLICTS; do
        # Get all files with this prefix, sorted alphabetically
        FILES=$(ls "$fulldir" | grep -E "^${prefix}-" | sort)
        echo "  Conflict prefix $prefix:"
        FIRST=1
        for f in $FILES; do
            if [ $FIRST -eq 1 ]; then
                echo "    Keep: $f"
                FIRST=0
            else
                SUFFIX="${f#*-}"
                NEW_NUM=$(printf "%03d" $NEXT)
                NEW_NAME="${NEW_NUM}-${SUFFIX}"
                echo "    Rename: $f -> $NEW_NAME"
                mv "$fulldir/$f" "$fulldir/$NEW_NAME"
                NEXT=$((NEXT + 1))
                DIR_COUNT=$((DIR_COUNT + 1))
                TOTAL_RENAMED=$((TOTAL_RENAMED + 1))
            fi
        done
    done

    echo "  Renamed $DIR_COUNT files in this directory"
}

fix_conflicts "02-arts-and-humanities/023-languages/0231-language-acquisition"
fix_conflicts "02-arts-and-humanities/023-languages/0232-literature-and-linguistics"
fix_conflicts "03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0312-political-sciences-and-civics"
fix_conflicts "04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance"
fix_conflicts "04-business-administration-and-law/041-business-and-administration/0413-management-and-administration"
fix_conflicts "06-information-and-communication-technologies/061-information-and-communication-technologies/0612-database-and-network-design-and-administration"
fix_conflicts "06-information-and-communication-technologies/061-information-and-communication-technologies/0613-software-and-applications-development-and-analysis"

echo ""
echo "===== SUMMARY ====="
echo "Total files renamed/moved: $TOTAL_RENAMED"
