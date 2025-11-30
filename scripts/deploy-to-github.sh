#!/bin/bash
# Deploy analytics HTML to GitHub Pages
#
# This script creates/updates a GitHub repository named '{current-repo}-graph'
# and deploys the knowledge graph visualizations to GitHub Pages.
#
# Prerequisites:
#   1. Git installed and configured
#   2. GitHub authentication via:
#      - GITHUB_TOKEN environment variable (Personal Access Token), OR
#      - SSH keys configured (~/.ssh/id_rsa)
#
# Usage:
#   bash scripts/deploy-to-github.sh

set -e

SOURCE_DIR="/root/knowledge-system"
# Dynamically determine repository name based on current repo
CURRENT_REPO_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null || pwd))
REPO_NAME="${CURRENT_REPO_NAME}-graph"
BRANCH="gh-pages"
DEPLOY_DIR="/tmp/${REPO_NAME}-deploy"

echo "=================================================="
echo "🚀 Deploying to GitHub Pages"
echo "Repository: ${REPO_NAME}"
echo "=================================================="

# Step 1: Detect GitHub username
echo ""
echo "📋 Step 1: Detecting GitHub username..."

# Try to get username from git config first
GIT_USER=$(git config --get user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --get user.email 2>/dev/null || echo "")

if [ -z "$GIT_USER" ]; then
    echo "❌ Error: Git user.name not configured"
    echo ""
    echo "Configure with:"
    echo "  git config --global user.name 'YourUsername'"
    echo "  git config --global user.email 'your@email.com'"
    exit 1
fi

# Extract GitHub username from git remotes or use git config name
GITHUB_USER=""
if git remote -v 2>/dev/null | grep -q "github.com"; then
    # Try to extract from existing GitHub remote
    GITHUB_USER=$(git remote -v | grep "github.com" | head -1 | sed -E 's/.*github\.com[:/]([^/]+)\/.*/\1/')
fi

# If not found in remotes, try to derive from email or use git name
if [ -z "$GITHUB_USER" ]; then
    if [[ "$GIT_EMAIL" == *"@users.noreply.github.com" ]]; then
        # Extract from GitHub noreply email format
        GITHUB_USER=$(echo "$GIT_EMAIL" | sed -E 's/.*\+([^@]+)@users\.noreply\.github\.com/\1/')
    else
        # Use git config name as fallback
        GITHUB_USER="$GIT_USER"
    fi
fi

echo "✓ GitHub Username: $GITHUB_USER"
echo "  Git Name: $GIT_USER"
echo "  Git Email: $GIT_EMAIL"

# Step 2: Check authentication method
echo ""
echo "📋 Step 2: Checking authentication..."

USE_SSH=false
USE_TOKEN=false

if [ -n "$GITHUB_TOKEN" ]; then
    echo "✓ Using GITHUB_TOKEN for authentication"
    USE_TOKEN=true
    REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
elif [ -f ~/.ssh/id_rsa ] || [ -f ~/.ssh/id_ed25519 ]; then
    echo "✓ Using SSH keys for authentication"
    USE_SSH=true
    REPO_URL="git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
else
    echo "⚠️  Warning: No authentication method found"
    echo ""
    echo "Please set up authentication:"
    echo ""
    echo "Option 1: Personal Access Token (recommended for servers)"
    echo "  1. Visit: https://github.com/settings/tokens/new"
    echo "  2. Select scopes: repo (all), workflow"
    echo "  3. Generate token and run:"
    echo "     export GITHUB_TOKEN='your_token_here'"
    echo ""
    echo "Option 2: SSH Keys"
    echo "  1. Generate key: ssh-keygen -t ed25519 -C 'your@email.com'"
    echo "  2. Add to GitHub: https://github.com/settings/keys"
    echo ""
    exit 1
fi

# Step 3: Check if HTML files exist
echo ""
echo "📋 Step 3: Checking source files..."

if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /graph first to generate visualizations"
    exit 1
fi

if [ ! -f "$SOURCE_DIR/knowledge-graph.html" ]; then
    echo "❌ Error: knowledge-graph.html not found"
    echo "Run /graph first to generate visualizations"
    exit 1
fi

echo "✓ Source files found:"
echo "  • analytics-dashboard.html"
echo "  • knowledge-graph.html"

# Step 4: Check if repository exists
echo ""
echo "📋 Step 4: Checking if repository exists..."

REPO_EXISTS=false
if [ "$USE_TOKEN" = true ]; then
    # Check via GitHub API
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${GITHUB_USER}/${REPO_NAME}")

    if [ "$HTTP_CODE" = "200" ]; then
        REPO_EXISTS=true
    fi
else
    # Check via git ls-remote (works with SSH)
    if git ls-remote "$REPO_URL" &>/dev/null; then
        REPO_EXISTS=true
    fi
fi

if [ "$REPO_EXISTS" = true ]; then
    echo "✓ Repository exists: ${GITHUB_USER}/${REPO_NAME}"
else
    echo "⚠️  Repository does not exist: ${GITHUB_USER}/${REPO_NAME}"

    # Create repository using GitHub API
    if [ "$USE_TOKEN" = true ]; then
        echo "  Creating repository via GitHub API..."

        CREATE_RESPONSE=$(curl -s -X POST \
            -H "Authorization: token ${GITHUB_TOKEN}" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/user/repos" \
            -d "{\"name\":\"${REPO_NAME}\",\"description\":\"Knowledge Graph Visualizations - Auto-generated by ${CURRENT_REPO_NAME}\",\"public\":true,\"auto_init\":false}")

        if echo "$CREATE_RESPONSE" | grep -q '"full_name"'; then
            echo "✓ Repository created successfully"
            REPO_EXISTS=true
            sleep 2  # Wait for GitHub to process
        else
            echo "❌ Failed to create repository"
            echo "$CREATE_RESPONSE"
            exit 1
        fi
    else
        # Try to use GitHub CLI if available
        if command -v gh &> /dev/null; then
            echo "  Checking GitHub CLI authentication..."
            if gh auth status &>/dev/null; then
                echo "  Creating repository via GitHub CLI..."

                if gh repo create "${REPO_NAME}" --public --description "Knowledge Graph Visualizations - Auto-generated by ${CURRENT_REPO_NAME}" 2>/dev/null; then
                    echo "✓ Repository created successfully via GitHub CLI"
                    REPO_EXISTS=true
                    sleep 2  # Wait for GitHub to process
                else
                    # Repo might already exist or creation failed
                    if gh repo view "${GITHUB_USER}/${REPO_NAME}" &>/dev/null; then
                        echo "✓ Repository already exists"
                        REPO_EXISTS=true
                    else
                        echo "❌ Failed to create repository via GitHub CLI"
                        echo ""
                        echo "Please create the repository manually:"
                        echo "  1. Visit: https://github.com/new"
                        echo "  2. Repository name: ${REPO_NAME}"
                        echo "  3. Make it public"
                        echo "  4. Do NOT initialize with README"
                        echo "  5. Run this script again"
                        echo ""
                        exit 1
                    fi
                fi
            else
                echo "⚠️  GitHub CLI not authenticated. Run: gh auth login"
                echo ""
                echo "Please create the repository manually:"
                echo "  1. Visit: https://github.com/new"
                echo "  2. Repository name: ${REPO_NAME}"
                echo "  3. Make it public"
                echo "  4. Do NOT initialize with README"
                echo "  5. Run this script again"
                echo ""
                exit 1
            fi
        else
            echo "⚠️  GitHub CLI not installed. Install with:"
            echo "     - macOS: brew install gh"
            echo "     - Linux: See https://cli.github.com/manual/installation"
            echo ""
            echo "Please create the repository manually:"
            echo "  1. Visit: https://github.com/new"
            echo "  2. Repository name: ${REPO_NAME}"
            echo "  3. Make it public"
            echo "  4. Do NOT initialize with README"
            echo "  5. Run this script again"
            echo ""
            exit 1
        fi
    fi
fi

# Step 5: Prepare deployment directory
echo ""
echo "📋 Step 5: Preparing deployment..."

rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Initialize git repo
git init
git checkout -b "$BRANCH"

# Copy HTML files
cp "$SOURCE_DIR/analytics-dashboard.html" index.html
cp "$SOURCE_DIR/knowledge-graph.html" graph.html

# Create .nojekyll to disable Jekyll processing
touch .nojekyll

# Create README
cat > README.md << EOF
# Knowledge Graph Visualizations

This repository contains auto-generated visualizations from the ${CURRENT_REPO_NAME}.

**Live Pages:**
- [Analytics Dashboard](https://${GITHUB_USER}.github.io/${REPO_NAME}/)
- [Knowledge Graph](https://${GITHUB_USER}.github.io/${REPO_NAME}/graph.html)

**Source Repository:** [${CURRENT_REPO_NAME}](https://github.com/${GITHUB_USER}/${CURRENT_REPO_NAME})

Last updated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

echo "✓ Files prepared:"
echo "  • index.html (analytics dashboard)"
echo "  • graph.html (knowledge graph)"
echo "  • .nojekyll (disable Jekyll)"
echo "  • README.md (documentation)"

# Step 6: Commit and push
echo ""
echo "📋 Step 6: Deploying to GitHub Pages..."

git add -A
git commit -m "Deploy knowledge graph visualizations

Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Nodes: $(grep -o '"nodeCount":[0-9]*' index.html | grep -o '[0-9]*' || echo 'N/A')
Concepts: $(grep -o '"total_concepts":[0-9]*' index.html | grep -o '[0-9]*' || echo 'N/A')

🤖 Auto-generated by ${CURRENT_REPO_NAME}
"

# Set remote
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# Push to gh-pages branch (force push for clean history)
echo "  Pushing to ${BRANCH} branch..."
git push -f origin "$BRANCH"

echo "✓ Pushed to GitHub"

# Step 7: Enable GitHub Pages (if using token)
if [ "$USE_TOKEN" = true ]; then
    echo ""
    echo "📋 Step 7: Configuring GitHub Pages..."

    # Enable GitHub Pages via API
    PAGES_RESPONSE=$(curl -s -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/${GITHUB_USER}/${REPO_NAME}/pages" \
        -d "{\"source\":{\"branch\":\"${BRANCH}\",\"path\":\"/\"}}")

    # Check if already enabled (409 conflict means it exists)
    if echo "$PAGES_RESPONSE" | grep -q '"html_url"' || echo "$PAGES_RESPONSE" | grep -q 'already exists'; then
        echo "✓ GitHub Pages enabled"
    else
        echo "⚠️  Could not auto-enable GitHub Pages (may already be enabled)"
        echo "  Manual check: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/pages"
    fi
else
    # Try to enable GitHub Pages using gh CLI if available
    echo ""
    echo "📋 Step 7: GitHub Pages configuration..."

    if command -v gh &> /dev/null && gh auth status &>/dev/null; then
        echo "  Attempting to enable GitHub Pages via GitHub CLI..."

        # GitHub CLI doesn't have direct pages command, but we can use API via gh
        PAGES_RESPONSE=$(gh api -X POST "/repos/${GITHUB_USER}/${REPO_NAME}/pages" \
            -f branch="${BRANCH}" \
            -f path="/" 2>&1 || true)

        if echo "$PAGES_RESPONSE" | grep -q '"html_url"' || echo "$PAGES_RESPONSE" | grep -q 'already enabled'; then
            echo "✓ GitHub Pages enabled via GitHub CLI"
        else
            echo "⚠️  Could not auto-enable GitHub Pages (may already be enabled)"
            echo "  Manual check: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/pages"
        fi
    else
        echo "⚠️  Using SSH - please manually enable GitHub Pages:"
        echo "  1. Visit: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/pages"
        echo "  2. Source: Deploy from branch"
        echo "  3. Branch: ${BRANCH}"
        echo "  4. Folder: / (root)"
        echo "  5. Save"
    fi
fi

# Step 8: Cleanup
echo ""
echo "📋 Step 8: Cleaning up..."
cd /
rm -rf "$DEPLOY_DIR"
echo "✓ Temporary files removed"

# Final message
echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "🌐 Your visualizations will be live at:"
echo "  Dashboard: https://${GITHUB_USER}.github.io/${REPO_NAME}/"
echo "  Graph:     https://${GITHUB_USER}.github.io/${REPO_NAME}/graph.html"
echo ""
echo "⏱️  Note: GitHub Pages may take 1-2 minutes to build"
echo "📁 Repository: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "=================================================="
