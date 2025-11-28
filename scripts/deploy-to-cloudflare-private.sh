#!/bin/bash
# Deploy analytics HTML to Cloudflare Pages using PRIVATE repository
# with safe branch strategy
#
# Strategy: Create a separate 'gh-pages' branch with ONLY HTML files
#
# Prerequisites:
#   1. Cloudflare account
#   2. Connect your PRIVATE knowledge-system repo to Cloudflare Pages
#   3. Configure to deploy from 'gh-pages' branch
#
# Usage:
#   bash scripts/deploy-to-cloudflare-private.sh

set -e

SOURCE_DIR="/root/knowledge-system"
BRANCH_NAME="gh-pages"

echo "=================================================="
echo "🚀 Deploying to Cloudflare Pages (Private Repo)"
echo "=================================================="

# Check if HTML files exist
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /save first to generate analytics"
    exit 1
fi

cd "$SOURCE_DIR"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

echo "📋 Preparing deployment branch..."

# Save current branch
CURRENT_BRANCH=$(git branch --show-current)

# Check if gh-pages branch exists
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
    echo "  Switching to existing $BRANCH_NAME branch..."
    git checkout $BRANCH_NAME
else
    echo "  Creating new $BRANCH_NAME branch (orphan)..."
    git checkout --orphan $BRANCH_NAME

    # Remove all files from index
    git rm -rf . 2>/dev/null || true
fi

# Copy only HTML files
echo "📋 Copying HTML files..."
git checkout $CURRENT_BRANCH -- analytics-dashboard.html knowledge-graph.html

# Rename for web hosting
mv analytics-dashboard.html index.html 2>/dev/null || true

echo "✓ Files prepared:"
echo "  • index.html (dashboard)"
echo "  • knowledge-graph.html (graph)"

# Create .gitignore to prevent accidental commits
cat > .gitignore <<EOF
# Only allow HTML files in this branch
*
!*.html
!.gitignore
EOF

echo ""
echo "📝 Creating commit..."
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
git add index.html knowledge-graph.html .gitignore
git commit -m "Update analytics - $TIMESTAMP" || echo "No changes to commit"

echo ""
echo "📤 Pushing to remote..."
git push origin $BRANCH_NAME --force

# Return to original branch
echo ""
echo "🔄 Returning to $CURRENT_BRANCH branch..."
git checkout $CURRENT_BRANCH

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "First time setup (if not done):"
echo "1. Go to https://pages.cloudflare.com/"
echo "2. Create a project → Connect to Git"
echo "3. Select your repository: knowledge-system"
echo "4. Build settings:"
echo "   - Production branch: gh-pages"
echo "   - Build command: (leave empty)"
echo "   - Build output directory: /"
echo "5. Save and Deploy"
echo ""
echo "Your analytics will be available at:"
echo "  Dashboard: https://knowledge-system.pages.dev/"
echo "  Graph:     https://knowledge-system.pages.dev/knowledge-graph.html"
echo ""
echo "=================================================="
