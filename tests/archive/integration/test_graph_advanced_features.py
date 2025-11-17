#!/usr/bin/env python3
"""
Tests for Story 3.2: Graph Advanced Features

Tests cover:
- Task 1: Sidebar Control Panel UI
- Task 2: Domain and Tag Filtering
- Task 3: Shortest Path Highlighting
- Task 4: Orphan Detection
- Task 5: Learning Roadmap Generator
- Task 6: Temporal View
- Task 7: Layout Switching
- Task 8: Export Functionality
- Task 9: Bridge Detection
- Task 10: URL State Management
"""

import pytest
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


# Fixtures
@pytest.fixture
def advanced_html_path():
    """Path to the advanced graph visualization HTML"""
    return Path("knowledge-graph-advanced.html")


@pytest.fixture
def advanced_html_content(advanced_html_path):
    """Load advanced HTML content"""
    if not advanced_html_path.exists():
        pytest.skip(f"Advanced HTML not found: {advanced_html_path}")
    with open(advanced_html_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def soup(advanced_html_content):
    """Parse HTML with BeautifulSoup"""
    return BeautifulSoup(advanced_html_content, 'html.parser')


# Task 1: Sidebar Control Panel UI Tests
class TestSidebarControlPanel:
    """AC1, AC6, AC7: Sidebar with filters, layout switcher, and export"""

    def test_sidebar_exists(self, soup):
        """Sidebar element exists with correct ID"""
        sidebar = soup.find(id='sidebar')
        assert sidebar is not None, "Sidebar element not found"

    def test_sidebar_sections(self, soup):
        """Sidebar contains all required sections"""
        sections = ['Filters', 'Layout', 'Highlights', 'Learning', 'Temporal View', 'Export']
        for section in sections:
            heading = soup.find('h3', string=section)
            assert heading is not None, f"Section '{section}' not found"

    def test_domain_filter_checkboxes(self, soup):
        """All 8 domain filter checkboxes present"""
        checkboxes = soup.find_all('input', {'class': 'domain-filter', 'type': 'checkbox'})
        assert len(checkboxes) == 8, f"Expected 8 domain filters, found {len(checkboxes)}"

        domains = ['finance', 'programming', 'language', 'science', 'arts', 'mathematics', 'social', 'generic']
        for domain in domains:
            checkbox = soup.find('input', {'value': domain})
            assert checkbox is not None, f"Domain filter for '{domain}' not found"

    def test_layout_buttons(self, soup):
        """Layout switcher has Force/Tree/Circular buttons"""
        layout_btns = soup.find_all('button', {'class': 'layout-btn'})
        assert len(layout_btns) == 3, f"Expected 3 layout buttons, found {len(layout_btns)}"

        layouts = ['force', 'hierarchical', 'circular']
        for layout in layouts:
            btn = soup.find('button', {'data-layout': layout})
            assert btn is not None, f"Layout button for '{layout}' not found"

    def test_export_controls(self, soup):
        """Export section has format dropdown and export button"""
        export_select = soup.find('select', id='export-format')
        assert export_select is not None, "Export format dropdown not found"

        options = export_select.find_all('option')
        assert len(options) >= 3, "Export dropdown should have PNG/SVG/JSON options"

        export_btn = soup.find('button', id='export-graph')
        assert export_btn is not None, "Export button not found"

    def test_sidebar_toggle_button(self, soup):
        """Sidebar toggle button exists"""
        toggle = soup.find('button', id='sidebar-toggle')
        assert toggle is not None, "Sidebar toggle button not found"


# Task 2: Domain and Tag Filtering Tests
class TestDomainTagFiltering:
    """AC1, AC8: Multi-select domain filtering and URL persistence"""

    def test_filter_state_initialization(self, advanced_html_content):
        """Filter state tracks active domains"""
        assert 'activeFilters:' in advanced_html_content, "Filter state not initialized"
        assert 'domains:' in advanced_html_content, "Domain filter state missing"

    def test_clear_filters_button(self, soup):
        """Clear all filters button exists"""
        clear_btn = soup.find('button', id='clear-filters')
        assert clear_btn is not None, "Clear filters button not found"

    def test_filter_count_display(self, soup):
        """Filter count badge displays active filter count"""
        filter_count = soup.find('span', id='filter-count')
        assert filter_count is not None, "Filter count display not found"

    def test_apply_filters_function(self, advanced_html_content):
        """applyFilters() function filters nodes by domain"""
        assert 'function applyFilters()' in advanced_html_content, "applyFilters function not found"
        assert 'filteredNodes' in advanced_html_content, "Filter logic not implemented"


# Task 3: Shortest Path Highlighting Tests
class TestShortestPathHighlighting:
    """AC2: Path mode shows shortest path between clicked nodes"""

    def test_path_mode_button(self, soup):
        """Path mode toggle button exists"""
        path_btn = soup.find('button', id='toggle-path-mode')
        assert path_btn is not None, "Path mode button not found"

    def test_path_info_overlay(self, soup):
        """Path info overlay displays path details"""
        path_info = soup.find(id='path-info')
        assert path_info is not None, "Path info overlay not found"

        path_distance = soup.find('span', id='path-distance')
        assert path_distance is not None, "Path distance display not found"

        path_nodes = soup.find('ol', id='path-nodes')
        assert path_nodes is not None, "Path nodes list not found"

    def test_calculate_path_function(self, advanced_html_content):
        """calculatePath() uses BFS algorithm"""
        assert 'function calculatePath()' in advanced_html_content, "calculatePath function not found"
        assert 'BFS' in advanced_html_content or 'queue' in advanced_html_content, "BFS algorithm not implemented"

    def test_path_highlight_css(self, advanced_html_content):
        """CSS class for path highlighting exists"""
        assert '.path-highlight' in advanced_html_content, "path-highlight CSS class not found"

    def test_clear_path_button(self, soup):
        """Clear path button exists"""
        clear_btn = soup.find('button', id='clear-path')
        assert clear_btn is not None, "Clear path button not found"


# Task 4: Orphan Detection Tests
class TestOrphanDetection:
    """AC3: Show orphans highlights concepts with no links"""

    def test_show_orphans_button(self, soup):
        """Show orphans button exists"""
        orphans_btn = soup.find('button', id='show-orphans')
        assert orphans_btn is not None, "Show orphans button not found"

    def test_orphan_count_display(self, soup):
        """Stats display includes orphan count"""
        orphan_count = soup.find('span', id='orphan-count')
        assert orphan_count is not None, "Orphan count display not found"

    def test_orphan_css_class(self, advanced_html_content):
        """Orphan CSS class with red stroke exists"""
        assert '.node.orphan' in advanced_html_content, "orphan CSS class not found"
        # Check for red color in orphan style
        orphan_style = re.search(r'\.node\.orphan\s*{[^}]*}', advanced_html_content, re.DOTALL)
        assert orphan_style is not None, "Orphan node style not found"
        assert '#e74c3c' in orphan_style.group() or 'red' in orphan_style.group(), "Orphan red color not applied"

    def test_highlight_orphans_function(self, advanced_html_content):
        """highlightOrphans() filters nodes with degree === 0"""
        assert 'function highlightOrphans()' in advanced_html_content, "highlightOrphans function not found"
        assert 'degree === 0' in advanced_html_content or 'd.degree === 0' in advanced_html_content, \
            "Orphan detection logic not implemented"


# Task 5: Learning Roadmap Generator Tests
class TestLearningRoadmapGenerator:
    """AC4: Suggest next concepts based on mastery"""

    def test_suggest_next_button(self, soup):
        """Suggest next concepts button exists"""
        suggest_btn = soup.find('button', id='suggest-next')
        assert suggest_btn is not None, "Suggest next button not found"

    def test_recommend_css_class(self, advanced_html_content):
        """Recommended CSS class exists for highlighting"""
        assert '.recommended' in advanced_html_content, "recommended CSS class not found"

    def test_suggest_next_function(self, advanced_html_content):
        """suggestNextConcepts() function exists"""
        assert 'function suggestNextConcepts()' in advanced_html_content, "suggestNextConcepts function not found"


# Task 6: Temporal View Tests
class TestTemporalView:
    """AC5: Temporal slider shows knowledge evolution over time"""

    def test_temporal_slider(self, soup):
        """Temporal slider input exists"""
        slider = soup.find('input', {'id': 'temporal-slider', 'type': 'range'})
        assert slider is not None, "Temporal slider not found"

    def test_temporal_labels(self, soup):
        """Temporal view has start/current date labels"""
        start_label = soup.find('span', id='temporal-start')
        current_label = soup.find('span', id='temporal-current')
        assert start_label is not None, "Temporal start label not found"
        assert current_label is not None, "Temporal current label not found"

    def test_play_temporal_button(self, soup):
        """Play timeline button exists"""
        play_btn = soup.find('button', id='play-temporal')
        assert play_btn is not None, "Play temporal button not found"


# Task 7: Layout Switching Tests
class TestLayoutSwitching:
    """AC6: Layout switcher toggles between Force/Hierarchical/Circular"""

    def test_switch_layout_function(self, advanced_html_content):
        """switchLayout() function implements 3 layouts"""
        assert 'function switchLayout' in advanced_html_content, "switchLayout function not found"
        assert "'force'" in advanced_html_content, "Force layout not implemented"
        assert "'hierarchical'" in advanced_html_content, "Hierarchical layout not implemented"
        assert "'circular'" in advanced_html_content, "Circular layout not implemented"

    def test_layout_state_tracking(self, advanced_html_content):
        """State tracks current layout"""
        assert 'currentLayout:' in advanced_html_content, "currentLayout state not found"


# Task 8: Export Functionality Tests
class TestExportFunctionality:
    """AC7: Export graph as PNG/SVG/JSON"""

    def test_export_graph_function(self, advanced_html_content):
        """exportGraph() handles PNG/SVG/JSON formats"""
        assert 'function exportGraph' in advanced_html_content, "exportGraph function not found"
        assert "'png'" in advanced_html_content, "PNG export not implemented"
        assert "'svg'" in advanced_html_content, "SVG export not implemented"
        assert "'json'" in advanced_html_content, "JSON export not implemented"

    def test_share_link_button(self, soup):
        """Share link button exists"""
        share_btn = soup.find('button', id='share-link')
        assert share_btn is not None, "Share link button not found"

    def test_generate_shareable_url_function(self, advanced_html_content):
        """generateShareableURL() creates URL with query params"""
        assert 'function generateShareableURL' in advanced_html_content, "generateShareableURL function not found"
        assert 'URLSearchParams' in advanced_html_content, "URL parameter encoding not implemented"


# Task 9: Bridge Detection Tests
class TestBridgeDetection:
    """AC9: Find bridges identifies critical connector concepts"""

    def test_find_bridges_button(self, soup):
        """Find bridges button exists"""
        bridges_btn = soup.find('button', id='find-bridges')
        assert bridges_btn is not None, "Find bridges button not found"

    def test_bridge_css_class(self, advanced_html_content):
        """Bridge CSS class with yellow/gold styling exists"""
        assert '.bridge' in advanced_html_content, "bridge CSS class not found"
        bridge_style = re.search(r'\.node\.bridge\s*{[^}]*}', advanced_html_content, re.DOTALL)
        assert bridge_style is not None, "Bridge node style not found"

    def test_highlight_bridges_function(self, advanced_html_content):
        """highlightBridges() function exists"""
        assert 'function highlightBridges()' in advanced_html_content, "highlightBridges function not found"


# Task 10: URL State Management Tests
class TestURLStateManagement:
    """AC8: Filters and settings persist in URL query parameters"""

    def test_url_parameter_parsing(self, advanced_html_content):
        """Code parses URL parameters on load"""
        assert 'URLSearchParams' in advanced_html_content, "URLSearchParams not used"
        assert 'window.location.search' in advanced_html_content, "URL search parsing not implemented"

    def test_url_update_on_state_change(self, advanced_html_content):
        """URL updates when state changes"""
        assert 'generateShareableURL' in advanced_html_content, "Shareable URL generation not implemented"

    def test_restore_state_from_url(self, advanced_html_content):
        """State is restored from URL parameters"""
        assert "params.has('domains')" in advanced_html_content or "params.get('domains')" in advanced_html_content, \
            "Domain parameter restoration not implemented"
        assert "params.has('layout')" in advanced_html_content or "params.get('layout')" in advanced_html_content, \
            "Layout parameter restoration not implemented"


# Integration Tests
class TestIntegration:
    """Integration tests for combined functionality"""

    def test_clear_highlights_button(self, soup):
        """Clear highlights button resets all modes"""
        clear_btn = soup.find('button', id='clear-highlights')
        assert clear_btn is not None, "Clear highlights button not found"

    def test_toast_notification_system(self, soup):
        """Toast notification element exists"""
        toast = soup.find(id='toast')
        assert toast is not None, "Toast notification element not found"

    def test_show_toast_function(self, advanced_html_content):
        """showToast() function displays notifications"""
        assert 'function showToast' in advanced_html_content, "showToast function not found"

    def test_d3js_library_loaded(self, soup):
        """D3.js library is loaded"""
        d3_script = soup.find('script', src=re.compile(r'd3.*\.js'))
        assert d3_script is not None, "D3.js library not loaded"

    def test_responsive_design(self, advanced_html_content):
        """CSS includes mobile/responsive considerations"""
        assert 'transition:' in advanced_html_content, "CSS transitions not implemented"
        assert 'collapsed' in advanced_html_content, "Collapsible sidebar not implemented"


# Performance Tests
class TestPerformance:
    """AC10: All features work with 500+ nodes without degradation"""

    def test_debounced_search(self, advanced_html_content):
        """Search input is debounced to avoid excessive re-renders"""
        assert 'searchTimeout' in advanced_html_content, "Search debouncing not implemented"
        assert '300' in advanced_html_content, "Debounce delay not set"

    def test_efficient_filtering(self, advanced_html_content):
        """Filtering uses efficient data structures (Set)"""
        assert 'new Set' in advanced_html_content, "Set data structure not used for filtering"

    def test_simulation_alpha_control(self, advanced_html_content):
        """Simulation alpha is controlled to avoid unnecessary calculations"""
        assert 'simulation.alpha' in advanced_html_content, "Simulation alpha control not implemented"


# File Structure Tests
class TestFileStructure:
    """Validate file structure and dependencies"""

    def test_html_file_exists(self, advanced_html_path):
        """Advanced HTML file exists"""
        assert advanced_html_path.exists(), f"File not found: {advanced_html_path}"

    def test_valid_html_structure(self, soup):
        """HTML has valid structure"""
        assert soup.find('html') is not None, "No <html> tag"
        assert soup.find('head') is not None, "No <head> tag"
        assert soup.find('body') is not None, "No <body> tag"

    def test_svg_container_exists(self, soup):
        """SVG container for graph rendering exists"""
        svg = soup.find('svg', id='svg')
        assert svg is not None, "SVG element not found"

    def test_details_panel_exists(self, soup):
        """Details panel for node information exists"""
        details = soup.find(id='details-panel')
        assert details is not None, "Details panel not found"

    def test_stats_display_exists(self, soup):
        """Stats display shows graph metrics"""
        stats = soup.find(id='stats')
        assert stats is not None, "Stats display not found"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
