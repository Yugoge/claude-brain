#!/usr/bin/env python3
"""
Publish Analytics to GitHub Pages

Copies analytics-dashboard.html and knowledge-graph.html to docs/ directory
for GitHub Pages deployment.

Usage:
    python scripts/analytics/publish-to-github-pages.py
"""

import shutil
from pathlib import Path
import sys


def main():
    # Define paths
    root = Path(__file__).parent.parent.parent
    docs_dir = root / 'docs'

    # Ensure docs directory exists
    docs_dir.mkdir(exist_ok=True)

    # Files to publish
    files_to_copy = [
        ('analytics-dashboard.html', 'Analytics Dashboard'),
        ('knowledge-graph.html', 'Knowledge Graph Visualization')
    ]

    print("📤 Publishing to GitHub Pages...\n", file=sys.stderr)

    success_count = 0
    for filename, description in files_to_copy:
        src = root / filename
        dst = docs_dir / filename

        if not src.exists():
            print(f"⚠️  {description} not found: {filename}", file=sys.stderr)
            print(f"   Skipping...", file=sys.stderr)
            continue

        try:
            shutil.copy2(src, dst)
            size_kb = dst.stat().st_size / 1024
            print(f"✅ Copied {description}", file=sys.stderr)
            print(f"   {src} → {dst}", file=sys.stderr)
            print(f"   Size: {size_kb:.1f} KB", file=sys.stderr)
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to copy {filename}: {e}", file=sys.stderr)

    print(f"\n📊 Summary:", file=sys.stderr)
    print(f"   {success_count}/{len(files_to_copy)} files published to docs/", file=sys.stderr)

    if success_count > 0:
        print(f"\n🚀 Next steps:", file=sys.stderr)
        print(f"   1. Commit changes: git add docs/ && git commit -m 'Update dashboards'", file=sys.stderr)
        print(f"   2. Push to GitHub: git push", file=sys.stderr)
        print(f"   3. Enable GitHub Pages in repo settings (Settings → Pages → Source: docs/)", file=sys.stderr)
        print(f"   4. Access at: https://<username>.github.io/<repo>/", file=sys.stderr)

    return 0 if success_count == len(files_to_copy) else 1


if __name__ == '__main__':
    sys.exit(main())
