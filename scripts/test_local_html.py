#!/usr/bin/env python3
"""
Comprehensive UI/UX Testing for Knowledge Graph (Local HTML Analysis)
Analyzes deployed HTML files to identify UI/UX issues
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from html.parser import HTMLParser

class HTMLAnalyzer(HTMLParser):
    """Parse HTML to extract structure and elements"""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.meta_tags = []
        self.scripts = []
        self.canvases = []
        self.inputs = []
        self.aria_count = 0
        self.in_script = False
        self.script_content = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.tags.append((tag, attrs_dict))

        if tag == "meta":
            self.meta_tags.append(attrs_dict)
        elif tag == "script":
            self.in_script = True
            self.scripts.append(attrs_dict)
        elif tag == "canvas":
            self.canvases.append(attrs_dict)
        elif tag == "input":
            self.inputs.append(attrs_dict)

        # Count ARIA attributes
        for key, val in attrs:
            if key.startswith("aria-"):
                self.aria_count += 1

    def handle_data(self, data):
        if self.in_script:
            self.script_content += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

class UIUXTester:
    """Comprehensive UI/UX testing for deployed knowledge graph"""

    def __init__(self):
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "files_tested": {
                "dashboard": "/root/knowledge-system/analytics-dashboard.html",
                "graph": "/root/knowledge-system/knowledge-graph.html"
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

    def read_file(self, path: str) -> str:
        """Read HTML file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error reading {path}: {e}")
            return ""

    def analyze_dashboard(self, html: str, file_path: str):
        """Comprehensive dashboard analysis"""
        print("\n" + "="*80)
        print("DASHBOARD ANALYSIS")
        print("="*80)

        parser = HTMLAnalyzer()
        parser.feed(html)

        issues = []
        checks = {
            "page_loads": True,
            "charts_render": "0/5",
            "search_works": False,
            "console_errors": [],
            "load_time_ms": 0,
            "issues": []
        }

        # File size check
        file_size = len(html)
        print(f"📄 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        if file_size < 5000:
            issues.append({
                "severity": "critical",
                "component": "dashboard-page",
                "description": f"File size too small ({file_size} bytes) - may be incomplete",
                "viewport": "both"
            })
            checks["page_loads"] = False

        # Check for Chart.js
        chartjs_found = any("chart" in str(script).lower() for script in parser.scripts)
        if chartjs_found or "chart.js" in html.lower() or "chartjs" in html.lower():
            print("✅ Chart.js library detected")
        else:
            issues.append({
                "severity": "critical",
                "component": "dashboard-charts",
                "description": "Chart.js library not found - charts won't render",
                "viewport": "both"
            })
            print("❌ Chart.js library NOT found")

        # Count canvas elements
        canvas_count = len(parser.canvases)
        checks["charts_render"] = f"{canvas_count}/5"
        print(f"📊 Canvas elements: {canvas_count}/5 expected")
        if canvas_count < 5:
            issues.append({
                "severity": "high",
                "component": "dashboard-charts",
                "description": f"Only {canvas_count} canvas elements found (expected 5 charts)",
                "viewport": "both"
            })

        # Check for search input
        search_inputs = [inp for inp in parser.inputs if
                        inp.get("type") == "search" or
                        "search" in inp.get("id", "").lower() or
                        "search" in inp.get("class", "").lower() or
                        "search" in inp.get("placeholder", "").lower()]

        if search_inputs:
            checks["search_works"] = True
            print(f"✅ Search input found: {len(search_inputs)} element(s)")
        else:
            checks["search_works"] = False
            issues.append({
                "severity": "medium",
                "component": "dashboard-search",
                "description": "No search input element found",
                "viewport": "both"
            })
            print("⚠️  No search input found")

        # Check viewport meta tag
        viewport_meta = [m for m in parser.meta_tags if m.get("name") == "viewport"]
        if viewport_meta:
            print(f"✅ Viewport meta tag: {viewport_meta[0].get('content', 'N/A')}")
        else:
            issues.append({
                "severity": "high",
                "component": "dashboard-mobile",
                "description": "Missing viewport meta tag - poor mobile experience",
                "viewport": "mobile"
            })
            print("❌ Missing viewport meta tag")

        # ARIA attributes
        print(f"♿ ARIA attributes: {parser.aria_count}")
        if parser.aria_count < 5:
            issues.append({
                "severity": "medium",
                "component": "dashboard-accessibility",
                "description": f"Low ARIA attribute count ({parser.aria_count}) - accessibility concerns",
                "viewport": "both"
            })

        # Check for responsive CSS
        if "@media" in html or "responsive" in html.lower():
            print("✅ Responsive CSS detected")
        else:
            issues.append({
                "severity": "high",
                "component": "dashboard-responsive",
                "description": "No responsive CSS (@media queries) found",
                "viewport": "mobile"
            })
            print("⚠️  No @media queries found")

        # Check for loading indicators
        if "loading" in html.lower() or "spinner" in html.lower():
            print("✅ Loading indicators present")
        else:
            print("⚠️  No loading indicators found")

        # Check for Chart.js chart types
        chart_types = []
        for chart_type in ["bar", "line", "pie", "doughnut", "radar", "scatter"]:
            if chart_type.lower() in html.lower():
                chart_types.append(chart_type)
        print(f"📈 Chart types detected: {', '.join(chart_types) if chart_types else 'None'}")

        checks["issues"] = [i["description"] for i in issues]
        self.results["desktop_results"]["dashboard"] = checks
        self.results["mobile_results"]["dashboard"] = {
            "responsive": len(viewport_meta) > 0,
            "horizontal_scroll": "@media" not in html,  # Inverted - no media = likely scroll
            "touch_controls": parser.aria_count > 0,
            "issues": [i["description"] for i in issues if i["viewport"] in ["mobile", "both"]]
        }

        return issues

    def analyze_graph(self, html: str, file_path: str):
        """Comprehensive graph analysis"""
        print("\n" + "="*80)
        print("GRAPH ANALYSIS")
        print("="*80)

        parser = HTMLAnalyzer()
        parser.feed(html)

        issues = []
        checks = {
            "graph_renders": True,
            "node_count": 0,
            "search_works": False,
            "search_counter_visible": False,
            "details_panel": False,
            "console_errors": [],
            "issues": []
        }

        # File size check
        file_size = len(html)
        print(f"📄 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        if file_size < 10000:
            issues.append({
                "severity": "critical",
                "component": "graph-page",
                "description": f"File size too small ({file_size} bytes) - may be incomplete",
                "viewport": "both"
            })
            checks["graph_renders"] = False

        # Check for graph libraries
        graph_libs = {
            "d3.js": "d3" in html.lower() or "d3.min.js" in html.lower(),
            "force-graph": "force-graph" in html.lower() or "forcegraph" in html.lower(),
            "three.js": "three" in html.lower() or "three.min.js" in html.lower()
        }

        detected_libs = [lib for lib, found in graph_libs.items() if found]
        if detected_libs:
            print(f"✅ Graph libraries: {', '.join(detected_libs)}")
        else:
            issues.append({
                "severity": "critical",
                "component": "graph-rendering",
                "description": "No graph library (D3.js/force-graph/three.js) detected",
                "viewport": "both"
            })
            print("❌ No graph libraries found")
            checks["graph_renders"] = False

        # Check for SVG/Canvas containers
        has_svg = any(tag == "svg" for tag, _ in parser.tags)
        has_canvas = len(parser.canvases) > 0

        if has_svg or has_canvas:
            container_type = "SVG" if has_svg else "Canvas"
            print(f"✅ Graph container: {container_type} ({len(parser.canvases)} canvas elements)")
        else:
            issues.append({
                "severity": "high",
                "component": "graph-container",
                "description": "No SVG or Canvas element found for graph rendering",
                "viewport": "both"
            })
            print("❌ No graph container (SVG/Canvas) found")

        # Check for search input
        search_inputs = [inp for inp in parser.inputs if
                        inp.get("type") == "search" or
                        "search" in inp.get("id", "").lower() or
                        "search" in inp.get("placeholder", "").lower()]

        if search_inputs:
            checks["search_works"] = True
            print(f"✅ Search input found: {search_inputs[0].get('placeholder', 'N/A')}")
        else:
            checks["search_works"] = False
            issues.append({
                "severity": "high",
                "component": "graph-search",
                "description": "No search input element found",
                "viewport": "both"
            })
            print("❌ No search input found")

        # Check for node counter
        if re.search(r"showing.*\d+.*of.*\d+", html.lower()) or \
           "node-count" in html.lower() or "nodeCount" in html:
            checks["search_counter_visible"] = True
            print("✅ Node counter element detected")
        else:
            checks["search_counter_visible"] = False
            print("⚠️  Node counter not clearly visible in HTML")

        # Check for details panel
        details_indicators = ["detail", "panel", "modal", "info", "sidebar"]
        has_details = any(indicator in html.lower() for indicator in details_indicators)

        if has_details:
            checks["details_panel"] = True
            print("✅ Details panel structure detected")
        else:
            checks["details_panel"] = False
            issues.append({
                "severity": "medium",
                "component": "graph-details",
                "description": "Details panel structure not clearly identified",
                "viewport": "both"
            })
            print("⚠️  Details panel not clearly identified")

        # Check for close button
        if "close" in html.lower() or "×" in html or "&times;" in html:
            print("✅ Close button detected")
        else:
            issues.append({
                "severity": "medium",
                "component": "graph-close-button",
                "description": "No close button found (×, 'close' text)",
                "viewport": "both"
            })
            print("⚠️  Close button not found")

        # Check viewport meta
        viewport_meta = [m for m in parser.meta_tags if m.get("name") == "viewport"]
        if viewport_meta:
            print(f"✅ Viewport meta tag: {viewport_meta[0].get('content', 'N/A')}")
        else:
            issues.append({
                "severity": "high",
                "component": "graph-mobile",
                "description": "Missing viewport meta tag - poor mobile experience",
                "viewport": "mobile"
            })
            print("❌ Missing viewport meta tag")

        # Extract node count from embedded data
        node_matches = re.findall(r'"id"\s*:\s*"([^"]+)"', html)
        if node_matches:
            checks["node_count"] = len(set(node_matches))  # Unique IDs only
            print(f"📊 Estimated nodes: {checks['node_count']} (from embedded data)")
        else:
            print("⚠️  Could not extract node count from HTML")

        # Check for zoom/pan controls
        if "zoom" in html.lower() or "pan" in html.lower() or "drag" in html.lower():
            print("✅ Zoom/pan controls detected in code")
        else:
            print("⚠️  No explicit zoom/pan controls found")

        # Check for legend
        if "legend" in html.lower():
            print("✅ Legend element detected")
        else:
            print("⚠️  No legend element found")

        # ARIA attributes
        print(f"♿ ARIA attributes: {parser.aria_count}")
        if parser.aria_count < 3:
            issues.append({
                "severity": "medium",
                "component": "graph-accessibility",
                "description": f"Low ARIA attribute count ({parser.aria_count}) - accessibility concerns",
                "viewport": "both"
            })

        checks["issues"] = [i["description"] for i in issues]
        self.results["desktop_results"]["graph"] = checks
        self.results["mobile_results"]["graph"] = {
            "fits_viewport": len(viewport_meta) > 0,
            "touch_gestures": "touch" in html.lower() or "pointer" in html.lower(),
            "details_fullscreen": checks["details_panel"],
            "issues": [i["description"] for i in issues if i["viewport"] in ["mobile", "both"]]
        }

        return issues

    def analyze_search_functionality(self, dashboard_html: str, graph_html: str):
        """Analyze search functionality implementation"""
        print("\n" + "="*80)
        print("SEARCH FUNCTIONALITY ANALYSIS")
        print("="*80)

        # Dashboard search
        dashboard_search = {
            "implementation": "oninput" in dashboard_html or "addEventListener" in dashboard_html,
            "filter_logic": "filter" in dashboard_html.lower(),
            "case_insensitive": "tolowercase" in dashboard_html.lower() or "touppercase" in dashboard_html.lower()
        }

        # Graph search
        graph_search = {
            "implementation": "oninput" in graph_html or "addEventListener" in graph_html,
            "node_filtering": "opacity" in graph_html.lower() or "visible" in graph_html.lower() or "hidden" in graph_html.lower(),
            "counter_update": "showing" in graph_html.lower() or "nodecount" in graph_html.lower(),
            "case_insensitive": "tolowercase" in graph_html.lower() or "touppercase" in graph_html.lower()
        }

        print("\n📊 Dashboard Search:")
        for key, val in dashboard_search.items():
            status = "✅" if val else "❌"
            print(f"   {status} {key}: {val}")

        print("\n🕸️  Graph Search:")
        for key, val in graph_search.items():
            status = "✅" if val else "❌"
            print(f"   {status} {key}: {val}")

        self.results["search_functionality"] = {
            "dashboard": dashboard_search,
            "graph": graph_search,
            "test_keywords": {
                "french": "Manual browser test required",
                "equity": "Manual browser test required",
                "business": "Manual browser test required"
            }
        }

    def generate_recommendations(self):
        """Generate actionable recommendations"""
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)

        recommendations = []

        # Critical issues
        critical_count = len([i for i in self.results["critical_issues"] if i["severity"] == "critical"])
        if critical_count > 0:
            recommendations.append({
                "priority": "high",
                "improvement": f"Fix {critical_count} critical issue(s) preventing core functionality",
                "effort": "2-4 hours",
                "details": [i["description"] for i in self.results["critical_issues"] if i["severity"] == "critical"]
            })

        # Mobile optimization
        mobile_issues = [i for i in self.results["critical_issues"] if i["viewport"] in ["mobile", "both"]]
        if len(mobile_issues) > 2:
            recommendations.append({
                "priority": "high",
                "improvement": "Improve mobile responsiveness (viewport meta, @media queries, touch targets)",
                "effort": "3-5 hours",
                "details": [i["description"] for i in mobile_issues]
            })

        # Accessibility
        aria_issues = [i for i in self.results["critical_issues"] if "accessibility" in i["component"]]
        if aria_issues:
            recommendations.append({
                "priority": "medium",
                "improvement": "Enhance accessibility (ARIA labels, keyboard navigation, screen reader support)",
                "effort": "2-3 hours",
                "details": [i["description"] for i in aria_issues]
            })

        # Search functionality
        search_issues = [i for i in self.results["critical_issues"] if "search" in i["component"]]
        if search_issues:
            recommendations.append({
                "priority": "high",
                "improvement": "Implement or fix search functionality",
                "effort": "2-4 hours",
                "details": [i["description"] for i in search_issues]
            })

        # Browser testing
        recommendations.append({
            "priority": "high",
            "improvement": "Conduct live browser testing (Playwright/Puppeteer) to validate:",
            "effort": "1-2 hours",
            "details": [
                "Search functionality with real keywords (french, equity, business)",
                "Node click → details panel interaction",
                "Drag and zoom behavior",
                "Touch gestures on mobile",
                "Chart rendering and zoom controls",
                "Performance metrics (load time, FPS)"
            ]
        })

        # Performance optimization
        if any(len(html) > 500000 for html in [
            self.read_file(self.results["files_tested"]["dashboard"]),
            self.read_file(self.results["files_tested"]["graph"])
        ]):
            recommendations.append({
                "priority": "medium",
                "improvement": "Optimize file size (minify JS/CSS, compress inline data)",
                "effort": "1-2 hours",
                "details": ["Large file sizes may impact load time on slow connections"]
            })

        self.results["recommendations"] = recommendations

        for rec in recommendations:
            print(f"\n🔹 {rec['priority'].upper()}: {rec['improvement']}")
            print(f"   Effort: {rec['effort']}")
            if rec.get("details"):
                print("   Details:")
                for detail in rec["details"][:3]:  # Show first 3
                    print(f"     • {detail}")
                if len(rec["details"]) > 3:
                    print(f"     • ... and {len(rec['details']) - 3} more")

    def run_tests(self):
        """Execute comprehensive UI/UX tests"""
        print("="*80)
        print("COMPREHENSIVE UI/UX TESTING - LOCAL HTML ANALYSIS")
        print("="*80)
        print(f"\nTest timestamp: {self.results['test_timestamp']}")
        print(f"Dashboard: {self.results['files_tested']['dashboard']}")
        print(f"Graph: {self.results['files_tested']['graph']}")

        # Read files
        dashboard_html = self.read_file(self.results["files_tested"]["dashboard"])
        graph_html = self.read_file(self.results["files_tested"]["graph"])

        # Analyze dashboard
        dashboard_issues = self.analyze_dashboard(dashboard_html, self.results["files_tested"]["dashboard"])
        self.results["critical_issues"].extend(dashboard_issues)

        # Analyze graph
        graph_issues = self.analyze_graph(graph_html, self.results["files_tested"]["graph"])
        self.results["critical_issues"].extend(graph_issues)

        # Analyze search
        self.analyze_search_functionality(dashboard_html, graph_html)

        # Generate recommendations
        self.generate_recommendations()

        # Save results
        output_path = Path("/root/knowledge-system/test-results-ui-ux.json")
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        critical_count = len([i for i in self.results["critical_issues"] if i["severity"] == "critical"])
        high_count = len([i for i in self.results["critical_issues"] if i["severity"] == "high"])
        medium_count = len([i for i in self.results["critical_issues"] if i["severity"] == "medium"])

        print(f"\n🔴 Critical Issues: {critical_count}")
        print(f"🟠 High Priority: {high_count}")
        print(f"🟡 Medium Priority: {medium_count}")
        print(f"\n💡 Recommendations: {len(self.results['recommendations'])}")
        print(f"\n✅ Full results saved to: {output_path}")

        # Overall assessment
        if critical_count == 0 and high_count <= 2:
            print("\n🎉 OVERALL: Good - Ready for deployment with minor improvements")
        elif critical_count == 0 and high_count <= 5:
            print("\n⚠️  OVERALL: Fair - Some high priority issues should be addressed")
        elif critical_count <= 2:
            print("\n❌ OVERALL: Needs work - Critical issues must be fixed before deployment")
        else:
            print("\n🚨 OVERALL: Not ready - Multiple critical issues blocking deployment")

        print("="*80)

        return output_path

if __name__ == "__main__":
    tester = UIUXTester()
    output_path = tester.run_tests()
    print(f"\n📊 View full report: cat {output_path}")
