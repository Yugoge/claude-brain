#!/usr/bin/env python3
"""
Comprehensive UI/UX Testing for Deployed Knowledge Graph
Uses Playwright MCP for READ-ONLY testing of public URLs
"""

import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List

# URLs to test
DASHBOARD_URL = "https://Yugoge.github.io/knowledge-system-graph/"
GRAPH_URL = "https://Yugoge.github.io/knowledge-system-graph/graph.html"

# Viewport configurations
DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
MOBILE_VIEWPORT = {"width": 375, "height": 667}

class PlaywrightTester:
    """Orchestrates Playwright MCP tests via Claude Code MCP tools"""

    def __init__(self):
        self.results = {
            "test_timestamp": datetime.utcnow().isoformat() + "Z",
            "urls_tested": {
                "dashboard": DASHBOARD_URL,
                "graph": GRAPH_URL
            },
            "desktop_results": {},
            "mobile_results": {},
            "search_functionality": {},
            "critical_issues": [],
            "recommendations": []
        }

    def print_test_plan(self):
        """Print the comprehensive test plan"""
        print("=" * 80)
        print("COMPREHENSIVE UI/UX TEST PLAN")
        print("=" * 80)
        print(f"\n📊 Dashboard URL: {DASHBOARD_URL}")
        print(f"🕸️  Graph URL: {GRAPH_URL}")
        print("\n🖥️  Desktop Viewport: 1920x1080")
        print("📱 Mobile Viewport: 375x667 (iPhone SE)")
        print("\n" + "=" * 80)
        print("\nTEST SUITE:")
        print("\nA. Desktop Testing")
        print("   Dashboard Tests:")
        print("   - Page loads successfully")
        print("   - All charts render (5 charts total)")
        print("   - Search bar functionality")
        print("   - Keyboard navigation")
        print("   - Loading indicators")
        print("   - Chart zoom controls")
        print("   - Stats cards display")
        print("   - Console errors check")
        print("\n   Graph Tests:")
        print("   - Graph renders (216 nodes)")
        print("   - Search functionality")
        print("   - Node click → details panel")
        print("   - Details panel close button")
        print("   - Drag node behavior")
        print("   - Zoom/pan controls")
        print("   - Legend visibility")
        print("   - Node counter during search")
        print("\nB. Mobile Testing")
        print("   Dashboard Mobile:")
        print("   - Responsive layout (no horizontal scroll)")
        print("   - Charts resize properly")
        print("   - Touch zoom controls")
        print("   - Stats cards stack vertically")
        print("   - Search bar usable")
        print("   - No text overflow")
        print("\n   Graph Mobile:")
        print("   - Graph fits viewport")
        print("   - Touch gestures (pinch zoom, drag)")
        print("   - Details panel fullscreen")
        print("   - Close button tappable")
        print("   - Search accessible")
        print("   - No layout breaking")
        print("\nC. Interaction Testing")
        print("   - Search: 'french', 'equity', 'business'")
        print("   - Node counter visibility")
        print("   - Opacity changes for hidden nodes")
        print("   - Clear search restoration")
        print("\nD. Performance Testing")
        print("   - Page load time")
        print("   - JavaScript console errors")
        print("   - Animation smoothness")
        print("\nE. Accessibility Testing")
        print("   - Tab navigation")
        print("   - Focus indicators")
        print("   - ARIA labels")
        print("\n" + "=" * 80)
        print("\n⚠️  CRITICAL RULES:")
        print("   ❌ NO local file reading")
        print("   ✅ ONLY public URLs via Playwright")
        print("   ✅ READ-ONLY testing")
        print("   ✅ Screenshots for issues")
        print("\n" + "=" * 80)
        print("\n🚀 Starting Playwright MCP tests...\n")

    def save_results(self):
        """Save test results to JSON file"""
        output_path = "/root/knowledge-system/test-results-ui-ux.json"
        with open(output_path, 'w') as f:
            json.dump(self.results, indent=2, fp=f)
        print(f"\n✅ Test results saved to: {output_path}")
        return output_path

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        critical_count = len([i for i in self.results.get("critical_issues", []) if i.get("severity") == "critical"])
        high_count = len([i for i in self.results.get("critical_issues", []) if i.get("severity") == "high"])
        medium_count = len([i for i in self.results.get("critical_issues", []) if i.get("severity") == "medium"])

        print(f"\n🔴 Critical Issues: {critical_count}")
        print(f"🟠 High Priority: {high_count}")
        print(f"🟡 Medium Priority: {medium_count}")
        print(f"\n💡 Recommendations: {len(self.results.get('recommendations', []))}")
        print("\n" + "=" * 80)

def run_comprehensive_tests():
    """Main test orchestrator"""
    tester = PlaywrightTester()
    tester.print_test_plan()

    print("\n⚠️  NOTE: This script prepares the test structure.")
    print("     Actual Playwright MCP tool calls must be executed by Claude Code agent.")
    print("\n📝 Test structure ready. Agent will now execute Playwright tests.\n")

    return tester

if __name__ == "__main__":
    tester = run_comprehensive_tests()
