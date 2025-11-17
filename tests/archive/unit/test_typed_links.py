"""
Comprehensive tests for typed links and inference scripts.

Tests coverage for:
- rebuild-backlinks.py (v1.1.0)
- normalize-links.py
- add-relation.py
- materialize-inferred-links.py
"""

import json
import re
import sys
import tempfile
import shutil
import importlib.util
from pathlib import Path
from typing import Dict, List

import pytest

# Add scripts directory to path and dynamically import scripts with hyphens
SCRIPT_DIR = Path(__file__).parent.parent.parent / 'scripts' / 'knowledge-graph'
sys.path.insert(0, str(SCRIPT_DIR))

# Dynamically import rebuild-backlinks.py
def import_script(script_name):
    """Import a Python script with hyphens in the name."""
    script_path = SCRIPT_DIR / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace('-', '_'), script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

rebuild_backlinks = import_script('rebuild-backlinks.py')
extract_wikilinks = rebuild_backlinks.extract_wikilinks
extract_typed_links = rebuild_backlinks.extract_typed_links
build_backlink_graph = rebuild_backlinks.build_backlink_graph
generate_backlinks_json = rebuild_backlinks.generate_backlinks_json
scan_rems = rebuild_backlinks.scan_rems
get_concept_id = rebuild_backlinks.get_concept_id
LINK_RE = rebuild_backlinks.LINK_RE
TYPED_LINK_RE = rebuild_backlinks.TYPED_LINK_RE


class TestRegexPatterns:
    """Test regex patterns for link extraction."""
    
    def test_wikilink_regex_basic(self):
        """Test basic wikilink pattern matching."""
        text = "See [[call-option]] for more info."
        matches = LINK_RE.findall(text)
        assert len(matches) == 1
        assert matches[0] == "call-option"
    
    def test_wikilink_regex_multiple(self):
        """Test multiple wikilinks in text."""
        text = "Compare [[call-option]] with [[put-option]]."
        matches = LINK_RE.findall(text)
        assert len(matches) == 2
        assert matches[0] == "call-option"
        assert matches[1] == "put-option"
    
    def test_typed_link_regex_basic(self):
        """Test typed link pattern matching."""
        text = "- [[call-option]] {rel: prerequisite_of}"
        matches = TYPED_LINK_RE.findall(text)
        assert len(matches) == 1
        assert matches[0] == ("call-option", "prerequisite_of")
    
    def test_typed_link_regex_multiple_types(self):
        """Test multiple typed links."""
        text = """
        - [[call-option]] {rel: prerequisite_of}
        - [[put-option]] {rel: antonym}
        - [[stock]] {rel: related}
        """
        matches = TYPED_LINK_RE.findall(text)
        assert len(matches) == 3
        assert matches[0] == ("call-option", "prerequisite_of")
        assert matches[1] == ("put-option", "antonym")
        assert matches[2] == ("stock", "related")
    
    def test_typed_link_with_extra_whitespace(self):
        """Test typed links with various whitespace."""
        text = "- [[concept]]  {  rel  :  synonym  }"
        matches = TYPED_LINK_RE.findall(text)
        assert len(matches) == 1
        assert matches[0] == ("concept", "synonym")
    
    def test_typed_link_ignores_plain_wikilinks(self):
        """Test that typed regex doesn't match plain wikilinks."""
        text = "- [[plain-link]]"
        matches = TYPED_LINK_RE.findall(text)
        assert len(matches) == 0


class TestExtractWikilinks:
    """Test extract_wikilinks function."""
    
    def test_extract_basic(self):
        """Test basic wikilink extraction."""
        content = "See [[call-option]] for details."
        links = extract_wikilinks(content)
        assert links == ["call-option"]
    
    def test_extract_deduplicates(self):
        """Test deduplication while preserving order."""
        content = "[[a]] and [[b]] and [[a]] again."
        links = extract_wikilinks(content)
        assert links == ["a", "b"]
    
    def test_extract_normalizes_case(self):
        """Test case normalization."""
        content = "[[Call-Option]] and [[CALL-OPTION]]."
        links = extract_wikilinks(content)
        assert links == ["call-option"]
    
    def test_extract_empty_content(self):
        """Test extraction from empty content."""
        links = extract_wikilinks("")
        assert links == []
    
    def test_extract_no_links(self):
        """Test content without wikilinks."""
        content = "This has no wikilinks at all."
        links = extract_wikilinks(content)
        assert links == []


class TestExtractTypedLinks:
    """Test extract_typed_links function."""
    
    def test_extract_typed_basic(self):
        """Test basic typed link extraction."""
        content = "- [[call-option]] {rel: prerequisite_of}"
        links = extract_typed_links(content)
        assert len(links) == 1
        assert links[0] == {"to": "call-option", "type": "prerequisite_of"}
    
    def test_extract_typed_multiple(self):
        """Test multiple typed links."""
        content = """
        - [[call-option]] {rel: prerequisite_of}
        - [[put-option]] {rel: antonym}
        """
        links = extract_typed_links(content)
        assert len(links) == 2
        assert links[0] == {"to": "call-option", "type": "prerequisite_of"}
        assert links[1] == {"to": "put-option", "type": "antonym"}
    
    def test_extract_typed_deduplicates(self):
        """Test deduplication of typed links."""
        content = """
        - [[a]] {rel: synonym}
        - [[a]] {rel: synonym}
        """
        links = extract_typed_links(content)
        assert len(links) == 1
    
    def test_extract_typed_case_normalization(self):
        """Test case normalization for typed links."""
        content = "- [[Call-Option]] {rel: SYNONYM}"
        links = extract_typed_links(content)
        assert links[0] == {"to": "call-option", "type": "synonym"}
    
    def test_extract_typed_empty(self):
        """Test extraction from empty content."""
        links = extract_typed_links("")
        assert links == []


class TestGetConceptId:
    """Test get_concept_id function."""
    
    def test_concept_id_from_frontmatter(self):
        """Test ID extraction from frontmatter."""
        file_path = Path("test-file.md")
        frontmatter = {"id": "custom-id"}
        concept_id = get_concept_id(file_path, frontmatter)
        assert concept_id == "custom-id"
    
    def test_concept_id_fallback_filename(self):
        """Test fallback to filename."""
        file_path = Path("call-option.md")
        frontmatter = {}
        concept_id = get_concept_id(file_path, frontmatter)
        assert concept_id == "call-option"
    
    def test_concept_id_case_normalization(self):
        """Test case normalization."""
        file_path = Path("Call-Option.md")
        frontmatter = {"id": "CUSTOM-ID"}
        concept_id = get_concept_id(file_path, frontmatter)
        assert concept_id == "custom-id"


@pytest.fixture
def temp_kb():
    """Create temporary knowledge base structure."""
    tmpdir = tempfile.mkdtemp()
    kb_dir = Path(tmpdir) / "knowledge-base"
    
    # Create structure
    finance_concepts = kb_dir / "finance" / "concepts"
    finance_concepts.mkdir(parents=True)
    
    # Create test concepts
    (finance_concepts / "call-option.md").write_text("""---
id: call-option
title: Call Option
---

# Call Option

An option to buy.

## Related Concepts
- [[put-option]] {rel: antonym}
- [[stock]] {rel: related}
""")
    
    (finance_concepts / "put-option.md").write_text("""---
id: put-option
title: Put Option
---

# Put Option

An option to sell.

## Related Concepts
- [[call-option]] {rel: antonym}
""")
    
    (finance_concepts / "stock.md").write_text("""---
id: stock
title: Stock
---

# Stock

Equity ownership.

## Related Concepts
- [[call-option]]
- [[market]]
""")
    
    # Create index directory
    (kb_dir / "_index").mkdir(parents=True)
    
    yield kb_dir
    
    # Cleanup
    shutil.rmtree(tmpdir)


class TestScanRems:
    """Test scan_rems function."""
    
    def test_scan_finds_all_concepts(self, temp_kb):
        """Test scanning finds all concept files."""
        rem_files = scan_rems(temp_kb)
        assert len(rem_files) == 3
        names = {f.stem for f in rem_files}
        assert names == {"call-option", "put-option", "stock"}
    
    def test_scan_ignores_underscore_dirs(self, temp_kb):
        """Test scanning ignores _index directories."""
        rem_files = scan_rems(temp_kb)
        for f in rem_files:
            assert "_index" not in str(f)
    
    def test_scan_empty_kb(self):
        """Test scanning empty knowledge base."""
        tmpdir = tempfile.mkdtemp()
        kb_dir = Path(tmpdir)
        rem_files = scan_rems(kb_dir)
        assert rem_files == []
        shutil.rmtree(tmpdir)


class TestBuildBacklinkGraph:
    """Test build_backlink_graph function."""
    
    def test_build_basic_graph(self, temp_kb):
        """Test building basic backlink graph."""
        rem_files = scan_rems(temp_kb)
        
        # Mock logger
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, broken_links, concepts_meta = build_backlink_graph(rem_files, MockLogger())
        
        # Check concepts present
        assert "call-option" in graph
        assert "put-option" in graph
        assert "stock" in graph
        
        # Check forward links
        assert "put-option" in graph["call-option"]["links_to"]
        assert "stock" in graph["call-option"]["links_to"]
        
        # Check backward links
        assert "call-option" in graph["put-option"]["linked_from"]
        
        # Check typed links
        typed = graph["call-option"]["typed_links_to"]
        assert len(typed) > 0
        assert any(t["to"] == "put-option" and t["type"] == "antonym" for t in typed)
        
        # Check concepts metadata
        assert "call-option" in concepts_meta
        assert concepts_meta["call-option"]["title"] == "Call Option"
    
    def test_build_detects_broken_links(self, temp_kb):
        """Test detection of broken links."""
        rem_files = scan_rems(temp_kb)
        
        class MockLogger:
            def __init__(self):
                self.warnings = []
            def debug(self, msg): pass
            def warning(self, msg):
                self.warnings.append(msg)
        
        logger = MockLogger()
        graph, broken_links, _ = build_backlink_graph(rem_files, logger)
        
        # "market" is referenced but doesn't exist
        assert "market" in broken_links
        assert len(logger.warnings) > 0
    
    def test_build_inferred_links(self, temp_kb):
        """Test two-hop inferred link generation."""
        rem_files = scan_rems(temp_kb)
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, _, _ = build_backlink_graph(rem_files, MockLogger())
        
        # call-option → stock → market (if market existed)
        # Since market doesn't exist, check structure is present
        assert "inferred_links_to" in graph["call-option"]
        inferred = graph["call-option"]["inferred_links_to"]
        
        # Should be empty or valid
        for link in inferred:
            assert "to" in link
            assert "via" in link
            # Should not infer to self
            assert link["to"] != "call-option"
            # Should not duplicate direct links
            assert link["to"] not in graph["call-option"]["links_to"]


class TestGenerateBacklinksJson:
    """Test generate_backlinks_json function."""
    
    def test_generate_structure(self, temp_kb):
        """Test generated JSON structure."""
        rem_files = scan_rems(temp_kb)
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, broken_links, concepts_meta = build_backlink_graph(rem_files, MockLogger())
        output = generate_backlinks_json(graph, broken_links, concepts_meta)
        
        # Check version
        assert output["version"] == "1.1.0"
        
        # Check structure
        assert "links" in output
        assert "concepts" in output
        assert "metadata" in output
        
        # Check metadata
        meta = output["metadata"]
        assert "last_updated" in meta
        assert "total_concepts" in meta
        assert "total_links" in meta
        assert "broken_links" in meta
        
        assert meta["total_concepts"] == 3
        assert "market" in meta["broken_links"]


class TestNormalizeLinksScript:
    """Test normalize-links.py script functions."""
    
    def test_normalize_imports(self):
        """Test that normalize-links script imports correctly."""
        normalize_links = import_script('normalize-links.py')
        assert normalize_links.WIKILINK_RE is not None
        assert callable(normalize_links.build_concept_index)
        assert callable(normalize_links.convert_content)
    
    def test_normalize_build_index(self, temp_kb):
        """Test building concept index."""
        normalize_links = import_script('normalize-links.py')
        old_kb = normalize_links.KB_DIR
        normalize_links.KB_DIR = temp_kb
        
        try:
            index = normalize_links.build_concept_index()
            assert "call-option" in index
            assert "put-option" in index
            
            title, path = index["call-option"]
            assert title == "Call Option"
            assert path.exists()
        finally:
            normalize_links.KB_DIR = old_kb
    
    def test_normalize_convert_content(self, temp_kb):
        """Test content conversion."""
        normalize_links = import_script('normalize-links.py')
        old_kb = normalize_links.KB_DIR
        normalize_links.KB_DIR = temp_kb
        
        try:
            index = normalize_links.build_concept_index()
            
            # Test content with wikilink
            content = """---
title: Test
---

See [[call-option]] for details.
"""
            current_file = temp_kb / "finance" / "concepts" / "test.md"
            
            result = normalize_links.convert_content(content, current_file, index, "replace")
            
            # Should convert to markdown link
            assert "[[call-option]]" not in result
            assert "[Call Option]" in result
            assert ".md)" in result
        finally:
            normalize_links.KB_DIR = old_kb


class TestAddRelationScript:
    """Test add-relation.py script functions."""
    
    def test_add_relation_imports(self):
        """Test that add-relation script imports correctly."""
        add_relation = import_script('add-relation.py')
        assert callable(add_relation.build_index)
        assert callable(add_relation.ensure_related_section)
        assert callable(add_relation.add_line_if_missing)
        assert "synonym" in add_relation.SYMMETRIC_TYPES
        assert "is_a" in add_relation.INVERSE_MAP
        assert add_relation.INVERSE_MAP["is_a"] == "has_subtype"
    
    def test_add_relation_ensure_section(self):
        """Test ensuring Related Concepts section exists."""
        add_relation = import_script('add-relation.py')
        
        # Content without section
        content = """---
title: Test
---

# Test

Some content.
"""
        result, insert_idx = add_relation.ensure_related_section(content)
        assert "## Related Concepts" in result
        assert insert_idx > 0
        
        # Content with existing section
        content_with_section = """---
title: Test
---

# Test

## Related Concepts
"""
        result2, insert_idx2 = add_relation.ensure_related_section(content_with_section)
        assert result2 == content_with_section
        assert insert_idx2 > 0
    
    def test_add_relation_add_line(self):
        """Test adding relation line."""
        add_relation = import_script('add-relation.py')
        
        content = """---
title: Test
---

# Test

## Related Concepts
- [[existing]] {rel: related}
"""
        # Add new line
        result = add_relation.add_line_if_missing(content, "new-concept", "synonym")
        assert "[[new-concept]] {rel: synonym}" in result
        
        # Don't duplicate existing
        result2 = add_relation.add_line_if_missing(result, "new-concept", "synonym")
        assert result2 == result


class TestMaterializeInferredLinksScript:
    """Test materialize-inferred-links.py script functions."""
    
    def test_materialize_imports(self):
        """Test that materialize script imports correctly."""
        materialize = import_script('materialize-inferred-links.py')
        assert callable(materialize.add_line_if_missing)
    
    def test_materialize_add_inferred_line(self):
        """Test adding inferred link line."""
        materialize = import_script('materialize-inferred-links.py')
        
        content = """---
title: Test
---

# Test

## Related Concepts
- [[direct]] {rel: related}
"""
        # Add inferred link
        result = materialize.add_line_if_missing(content, "inferred-concept", "via-concept")
        assert "[[inferred-concept]] {rel: inferred, via: via-concept}" in result
        
        # Don't add if direct link exists
        result2 = materialize.add_line_if_missing(content, "direct", "via-x")
        assert result2 == content


class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_full_workflow(self, temp_kb):
        """Test complete workflow: rebuild → normalize → materialize."""
        # Step 1: Rebuild backlinks
        rem_files = scan_rems(temp_kb)
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, broken_links, concepts_meta = build_backlink_graph(rem_files, MockLogger())
        output = generate_backlinks_json(graph, broken_links, concepts_meta)
        
        # Write index
        index_file = temp_kb / "_index" / "backlinks.json"
        index_file.write_text(json.dumps(output, indent=2))
        
        # Verify index
        assert index_file.exists()
        data = json.loads(index_file.read_text())
        assert data["version"] == "1.1.0"
        assert len(data["links"]) == 3
        
        # Step 2: Test that concepts have typed links
        assert "typed_links_to" in data["links"]["call-option"]
        assert "typed_linked_from" in data["links"]["put-option"]
        
        # Step 3: Test that inferred links are calculated
        assert "inferred_links_to" in data["links"]["call-option"]


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_knowledge_base(self):
        """Test handling of empty knowledge base."""
        tmpdir = tempfile.mkdtemp()
        kb_dir = Path(tmpdir)
        kb_dir.mkdir(exist_ok=True)
        
        rem_files = scan_rems(kb_dir)
        assert rem_files == []
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, broken_links, concepts_meta = build_backlink_graph([], MockLogger())
        assert graph == {}
        assert broken_links == set()
        
        shutil.rmtree(tmpdir)
    
    def test_malformed_typed_relation(self):
        """Test handling of malformed {rel: ...} syntax."""
        content = """
        - [[a]] {rel}
        - [[b]] {rel:}
        - [[c]] {rel: }
        - [[d]] { : type}
        """
        links = extract_typed_links(content)
        # Should not crash, may extract none
        assert isinstance(links, list)
    
    def test_circular_references(self):
        """Test handling of circular references."""
        tmpdir = tempfile.mkdtemp()
        kb_dir = Path(tmpdir) / "kb"
        concepts = kb_dir / "domain" / "concepts"
        concepts.mkdir(parents=True)
        
        # A → B → A (circular)
        (concepts / "a.md").write_text("""---
id: a
---
- [[b]]
""")
        (concepts / "b.md").write_text("""---
id: b
---
- [[a]]
""")
        
        rem_files = scan_rems(kb_dir)
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        # Should not crash
        graph, _, _ = build_backlink_graph(rem_files, MockLogger())
        
        assert "a" in graph
        assert "b" in graph
        
        # Inferred links should not create self-loops
        for concept_id, data in graph.items():
            inferred = data.get("inferred_links_to", [])
            for link in inferred:
                assert link["to"] != concept_id
        
        shutil.rmtree(tmpdir)
    
    def test_concept_with_no_links(self):
        """Test concept with no outgoing links."""
        tmpdir = tempfile.mkdtemp()
        kb_dir = Path(tmpdir) / "kb"
        concepts = kb_dir / "domain" / "concepts"
        concepts.mkdir(parents=True)
        
        (concepts / "isolated.md").write_text("""---
id: isolated
title: Isolated Concept
---

# Isolated

No links to anything.
""")
        
        rem_files = scan_rems(kb_dir)
        
        class MockLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        graph, _, concepts_meta = build_backlink_graph(rem_files, MockLogger())
        
        assert "isolated" in graph
        assert graph["isolated"]["links_to"] == []
        assert graph["isolated"]["linked_from"] == []
        assert graph["isolated"]["typed_links_to"] == []
        assert graph["isolated"]["inferred_links_to"] == []
        
        assert "isolated" in concepts_meta
        assert concepts_meta["isolated"]["title"] == "Isolated Concept"
        
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

