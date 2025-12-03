#!/usr/bin/env python3
"""
Static Analysis UI/UX Testing for Deployed Knowledge Graph
Analyzes HTML/CSS/JS structure without browser rendering
"""

import json
import re
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# URLs to test
DASHBOARD_URL = "https://Yugoge.github.io/knowledge-system-graph/"
GRAPH_URL = "https://Yugoge.github.io/knowledge-system-graph/graph.html"

class StaticUITester:
    """Analyzes deployed HTML/CSS/JS for UI/UX issues"""

    def __init__(self):
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "urls_tested": {
                "dashboard": DASHBOARD_URL,
                "graph": GRAPH_URL
            },
            "desktop_results": {
                "dashboard": {},
                "graph": {}
            },
            "mobile_results": {
                "dashboard": {},
                "graph": {}
            },
            "search_functionality": {},
            "critical_issues": [],
            "recommendations": []
        }

    def fetch_page(self, url: str) -> str:
        """Fetch page content via curl"""
        print(f"📥 Fetching: {url}")
        try:
            result = subprocess.run(
                ["curl", "-sL", "-H", "User-Agent: Mozilla/5.0", url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"   ✅ Fetched {len(result.stdout)} bytes")
                return result.stdout
            else:
                print(f"   ❌ Fetch failed: {result.stderr}")
                return ""
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return ""

    def analyze_dashboard(self, html: str):
        """Analyze dashboard HTML structure"""
        print("\n🔍 Analyzing Dashboard Structure...")

        issues = []
        checks = {
            "page_loads": False,
            "charts_render": "0/5",
            "search_works": False,
            "console_errors": [],
            "load_time_ms": 0,
            "issues": []
        }

        # Check if page loaded
        if len(html) > 1000:
            checks["page_loads"] = True
            print("   ✅ Page content fetched (>1KB)")
        else:
            checks["page_loads"] = False
            issues.append({
                "severity": "critical",
                "component": "dashboard-page",
                "description": "Page content too small or failed to load",
                "viewport": "both"
            })
            print("   ❌ Page content too small")

        # Check for Chart.js
        if "chart.js" in html.lower() or "chartjs" in html.lower():
            print("   ✅ Chart.js library detected")
        else:
            issues.append({
                "severity": "critical",
                "component": "dashboard-charts",
                "description": "Chart.js library not found in page",
                "viewport": "both"
            })
            print("   ❌ Chart.js library not found")

        # Count canvas elements (for charts)
        canvas_count = html.count("<canvas")
        checks["charts_render"] = f"{canvas_count}/5"
        print(f"   📊 Found {canvas_count} canvas elements (expected 5)")
        if canvas_count < 5:
            issues.append({
                "severity": "high",
                "component": "dashboard-charts",
                "description": f"Only {canvas_count} canvas elements found (expected 5 charts)",
                "viewport": "both"
            })

        # Check for search functionality
        if 'type="search"' in html or 'id="search"' in html or 'class="search"' in html:
            checks["search_works"] = True
            print("   ✅ Search input detected")
        else:
            checks["search_works"] = False
            issues.append({
                "severity": "medium",
                "component": "dashboard-search",
                "description": "No search input found",
                "viewport": "both"
            })
            print("   ⚠️  No search input found")

        # Check for responsive meta tags
        if '<meta name="viewport"' in html:
            print("   ✅ Viewport meta tag present (mobile-friendly)")
        else:
            issues.append({
                "severity": "high",
                "component": "dashboard-mobile",
                "description": "Missing viewport meta tag - poor mobile support",
                "viewport": "mobile"
            })
            print("   ❌ Missing viewport meta tag")

        # Check for accessibility
        aria_count = html.count("aria-")
        print(f"   ♿ Found {aria_count} ARIA attributes")
        if aria_count < 5:
            issues.append({
                "severity": "medium",
                "component": "dashboard-accessibility",
                "description": "Insufficient ARIA labels for accessibility",
                "viewport": "both"
            })

        checks["issues"] = [i["description"] for i in issues]
        self.results["desktop_results"]["dashboard"] = checks
        self.results["mobile_results"]["dashboard"] = {
            "responsive": '<meta name="viewport"' in html,
            "horizontal_scroll": False,  # Can't test without browser
            "touch_controls": "aria-" in html,
            "issues": [i["description"] for i in issues if i["viewport"] in ["mobile", "both"]]
        }

        return issues

    def analyze_graph(self, html: str):
        """Analyze graph HTML structure"""
        print("\n🔍 Analyzing Graph Structure...")

        issues = []
        checks = {
            "graph_renders": False,
            "node_count": 0,
            "search_works": False,
            "search_counter_visible": False,
            "details_panel": False,
            "console_errors": [],
            "issues": []
        }

        # Check if page loaded
        if len(html) > 1000:
            checks["graph_renders"] = True
            print("   ✅ Page content fetched (>1KB)")
        else:
            checks["graph_renders"] = False
            issues.append({
                "severity": "critical",
                "component": "graph-page",
                "description": "Page content too small or failed to load",
                "viewport": "both"
            })
            print("   ❌ Page content too small")

        # Check for D3.js or Force Graph
        if "d3.js" in html.lower() or "d3.min.js" in html.lower():
            print("   ✅ D3.js library detected")
        elif "force-graph" in html.lower():
            print("   ✅ Force-graph library detected")
        else:
            issues.append({
                "severity": "critical",
                "component": "graph-rendering",
                "description": "No graph library (D3.js/force-graph) detected",
                "viewport": "both"
            })
            print("   ❌ No graph library detected")

        # Check for SVG or Canvas (graph container)
        if "<svg" in html or "<canvas" in html:
            print("   ✅ Graph container (SVG/Canvas) detected")
        else:
            issues.append({
                "severity": "high",
                "component": "graph-container",
                "description": "No SVG or Canvas element found for graph rendering",
                "viewport": "both"
            })
            print("   ❌ No graph container found")

        # Check for search functionality
        if 'type="search"' in html or 'id="search"' in html or 'placeholder="Search' in html:
            checks["search_works"] = True
            print("   ✅ Search input detected")
        else:
            checks["search_works"] = False
            issues.append({
                "severity": "high",
                "component": "graph-search",
                "description": "No search input found",
                "viewport": "both"
            })
            print("   ⚠️  No search input found")

        # Check for node counter
        if "showing" in html.lower() and ("nodes" in html.lower() or "of" in html.lower()):
            checks["search_counter_visible"] = True
            print("   ✅ Node counter text detected")
        else:
            checks["search_counter_visible"] = False
            print("   ⚠️  Node counter not detected in HTML")

        # Check for details panel
        if "detail" in html.lower() and ("panel" in html.lower() or "modal" in html.lower()):
            checks["details_panel"] = True
            print("   ✅ Details panel detected")
        else:
            checks["details_panel"] = False
            issues.append({
                "severity": "medium",
                "component": "graph-details",
                "description": "Details panel structure not found",
                "viewport": "both"
            })
            print("   ⚠️  Details panel not found")

        # Check for close button
        if "close" in html.lower() or "×" in html:
            print("   ✅ Close button detected")
        else:
            issues.append({
                "severity": "medium",
                "component": "graph-close-button",
                "description": "No close button found for details panel",
                "viewport": "both"
            })
            print("   ⚠️  Close button not found")

        # Check for viewport meta
        if '<meta name="viewport"' in html:
            print("   ✅ Viewport meta tag present (mobile-friendly)")
        else:
            issues.append({
                "severity": "high",
                "component": "graph-mobile",
                "description": "Missing viewport meta tag - poor mobile support",
                "viewport": "mobile"
            })
            print("   ❌ Missing viewport meta tag")

        # Estimate node count from data
        node_matches = re.findall(r'"id":\s*"([^"]+)"', html)
        if node_matches:
            checks["node_count"] = len(node_matches)
            print(f"   📊 Estimated {len(node_matches)} nodes in data")
        else:
            print("   ⚠️  Could not extract node count from HTML")

        checks["issues"] = [i["description"] for i in issues]
        self.results["desktop_results"]["graph"] = checks
        self.results["mobile_results"]["graph"] = {
            "fits_viewport": '<meta name="viewport"' in html,
            "touch_gestures": False,  # Can't test without browser
            "details_fullscreen": checks["details_panel"],
            "issues": [i["description"] for i in issues if i["viewport"] in ["mobile", "both"]]
        }

        return issues

    def generate_search_tests(self):
        """Generate search functionality tests (simulated)"""
        print("\n🔍 Search Functionality Analysis...")
        print("   ⚠️  Cannot test search without browser - marking as manual test needed")

        self.results["search_functionality"] = {
            "test_french": {
                "nodes_found": "manual_test_required",
                "counter_visible": "manual_test_required",
                "opacity_works": "manual_test_required"
            },
            "test_equity": {
                "nodes_found": "manual_test_required",
                "counter_visible": "manual_test_required",
                "opacity_works": "manual_test_required"
            },
            "test_business": {
                "nodes_found": "manual_test_required",
                "counter_visible": "manual_test_required",
                "opacity_works": "manual_test_required"
            }
        }

    def generate_recommendations(self):
        """Generate improvement recommendations"""
        print("\n💡 Generating Recommendations...")

        recommendations = []

        # Critical issues first
        critical_issues = [i for i in self.results["critical_issues"] if i["severity"] == "critical"]
        if critical_issues:
            recommendations.append({
                "priority": "high",
                "improvement": f"Fix {len(critical_issues)} critical issues preventing core functionality",
                "effort": "2-4 hours"
            })

        # Mobile optimization
        mobile_issues = [i for i in self.results["critical_issues"] if i["viewport"] in ["mobile", "both"]]
        if len(mobile_issues) > 2:
            recommendations.append({
                "priority": "high",
                "improvement": "Add responsive design improvements for mobile devices",
                "effort": "4-6 hours"
            })

        # Accessibility
        aria_issues = [i for i in self.results["critical_issues"] if "accessibility" in i["component"]]
        if aria_issues:
            recommendations.append({
                "priority": "medium",
                "improvement": "Enhance accessibility with proper ARIA labels and keyboard navigation",
                "effort": "2-3 hours"
            })

        # Browser testing
        recommendations.append({
            "priority": "high",
            "improvement": "Conduct live browser testing (Playwright/Puppeteer) to validate interactive features",
            "effort": "1-2 hours"
        })

        self.results["recommendations"] = recommendations
        for rec in recommendations:
            print(f"   {rec['priority'].upper()}: {rec['improvement']} ({rec['effort']})")

    def run_tests(self):
        """Execute all tests"""
        print("=" * 80)
        print("STATIC UI/UX ANALYSIS")
        print("=" * 80)

        # Fetch pages
        dashboard_html = self.fetch_page(DASHBOARD_URL)
        graph_html = self.fetch_page(GRAPH_URL)

        # Analyze dashboard
        dashboard_issues = self.analyze_dashboard(dashboard_html)
        self.results["critical_issues"].extend(dashboard_issues)

        # Analyze graph
        graph_issues = self.analyze_graph(graph_html)
        self.results["critical_issues"].extend(graph_issues)

        # Search tests (simulated)
        self.generate_search_tests()

        # Generate recommendations
        self.generate_recommendations()

        # Save results
        output_path = Path("/root/knowledge-system/test-results-ui-ux.json")
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        critical_count = len([i for i in self.results["critical_issues"] if i["severity"] == "critical"])
        high_count = len([i for i in self.results["critical_issues"] if i["severity"] == "high"])
        medium_count = len([i for i in self.results["critical_issues"] if i["severity"] == "medium"])

        print(f"\n🔴 Critical Issues: {critical_count}")
        print(f"🟠 High Priority: {high_count}")
        print(f"🟡 Medium Priority: {medium_count}")
        print(f"\n💡 Recommendations: {len(self.results['recommendations'])}")
        print(f"\n✅ Test results saved to: {output_path}")
        print("\n" + "=" * 80)

        return output_path

if __name__ == "__main__":
    tester = StaticUITester()
    tester.run_tests()
