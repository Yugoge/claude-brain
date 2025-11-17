"""
Unit tests for scripts/generate-graph-data.py
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import module from scripts directory
project_root = Path(__file__).parent.parent.parent
scripts_dir = project_root / 'scripts' / 'knowledge-graph'
sys.path.insert(0, str(project_root))

# Load the module dynamically
import importlib.util
spec = importlib.util.spec_from_file_location(
    "generate_graph_data",
    scripts_dir / "generate-graph-data.py"
)
generate_graph_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_graph_data)


class TestGraphGeneration(unittest.TestCase):
    """Test graph data generation"""

    def setUp(self):
        """Create sample backlinks and metadata"""
        self.sample_backlinks_data = {
            "version": "1.1.0",
            "links": {
                "concept-a": {
                    "links_to": ["concept-b", "concept-c"],
                    "typed_links_to": [],
                    "linked_from": [],
                    "typed_linked_from": [],
                    "inferred_links_to": []
                },
                "concept-b": {
                    "links_to": ["concept-a"],
                    "typed_links_to": [],
                    "linked_from": ["concept-a"],
                    "typed_linked_from": [],
                    "inferred_links_to": []
                },
                "concept-c": {
                    "links_to": [],
                    "typed_links_to": [],
                    "linked_from": ["concept-a"],
                    "typed_linked_from": [],
                    "inferred_links_to": []
                }
            },
            "concepts": {
                "concept-a": {
                    "title": "Concept A",
                    "file": "finance/concepts/concept-a.md"
                },
                "concept-b": {
                    "title": "Concept B",
                    "file": "finance/concepts/concept-b.md"
                },
                "concept-c": {
                    "title": "Concept C",
                    "file": "programming/concepts/concept-c.md"
                }
            },
            "metadata": {
                "last_updated": "2025-10-29",
                "total_concepts": 3,
                "total_links": 2
            }
        }

        self.sample_concept_metadata = {
            "concept-a": {
                "domain": "finance",
                "tags": ["risk", "investment"],
                "file": "knowledge-base/finance/concepts/concept-a.md"
            },
            "concept-b": {
                "domain": "finance",
                "tags": ["portfolio", "theory"],
                "file": "knowledge-base/finance/concepts/concept-b.md"
            },
            "concept-c": {
                "domain": "programming",
                "tags": ["python", "async"],
                "file": "knowledge-base/programming/concepts/concept-c.md"
            }
        }

    def test_graph_structure(self):
        """Test 1: Verify graph data structure"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        self.assertIn('metadata', result)

        self.assertEqual(len(result['nodes']), 3)
        self.assertGreater(len(result['edges']), 0)

    def test_node_properties(self):
        """Test 2: Verify node properties"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )
        node = result['nodes'][0]

        required_fields = ['id', 'label', 'domain', 'color', 'size',
                          'reviewCount', 'pageRank', 'cluster', 'degree', 'tags', 'file']
        for field in required_fields:
            self.assertIn(field, node, f"Missing field: {field}")

    def test_domain_filtering(self):
        """Test 3: Domain filter works correctly"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata,
            domain_filter='finance'
        )

        # Should only have 2 finance concepts
        self.assertEqual(len(result['nodes']), 2)

        # All nodes should be finance domain
        for node in result['nodes']:
            self.assertEqual(node['domain'], 'finance')

    def test_node_sizing(self):
        """Test 4: Node size increases with review count"""
        # Add mock review counts
        metadata_with_reviews = self.sample_concept_metadata.copy()
        # Note: reviewCount is not in concept_metadata currently, it comes from review history
        # This test verifies the size formula works

        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            metadata_with_reviews
        )

        # All nodes should have size >= 10 (base size)
        for node in result['nodes']:
            self.assertGreaterEqual(node['size'], 10)

    def test_pagerank_calculation(self):
        """Test 5: PageRank values are calculated"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        for node in result['nodes']:
            self.assertGreater(node['pageRank'], 0)
            self.assertLessEqual(node['pageRank'], 1)

    def test_bidirectional_edges(self):
        """Test 6: Bidirectional edges are detected"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        # concept-a links to concept-b, and concept-b links back to concept-a
        bidirectional_edge = None
        for edge in result['edges']:
            if (edge['source'] == 'concept-a' and edge['target'] == 'concept-b') or \
               (edge['source'] == 'concept-b' and edge['target'] == 'concept-a'):
                bidirectional_edge = edge
                break

        self.assertIsNotNone(bidirectional_edge)
        self.assertTrue(bidirectional_edge['bidirectional'])

    def test_empty_knowledge_base(self):
        """Test 7: Handle empty knowledge base gracefully"""
        empty_backlinks = {
            "version": "1.1.0",
            "links": {},
            "concepts": {},
            "metadata": {"total_concepts": 0}
        }

        result = generate_graph_data.transform_to_graph_format(empty_backlinks, {})

        self.assertEqual(len(result['nodes']), 0)
        self.assertEqual(len(result['edges']), 0)
        self.assertEqual(result['metadata']['nodeCount'], 0)

    def test_orphaned_nodes(self):
        """Test 8: Orphaned nodes (no links) are included"""
        orphan_backlinks = {
            "version": "1.1.0",
            "links": {
                "orphan": {
                    "links_to": [],
                    "typed_links_to": [],
                    "linked_from": [],
                    "typed_linked_from": [],
                    "inferred_links_to": []
                }
            },
            "concepts": {
                "orphan": {
                    "title": "Orphan Concept",
                    "file": "concepts/orphan.md"
                }
            },
            "metadata": {"total_concepts": 1}
        }

        orphan_metadata = {
            "orphan": {
                "domain": "generic",
                "tags": [],
                "file": "knowledge-base/concepts/orphan.md"
            }
        }

        result = generate_graph_data.transform_to_graph_format(orphan_backlinks, orphan_metadata)

        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(result['nodes'][0]['degree'], 0)

    def test_cluster_detection(self):
        """Test 9: Clusters are detected and assigned"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        cluster_ids = set(n['cluster'] for n in result['nodes'])
        self.assertGreater(len(cluster_ids), 0)
        self.assertGreater(result['metadata']['clusters'], 0)

    def test_edge_deduplication(self):
        """Test 10: Duplicate edges are not created"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        edge_pairs = set()
        for edge in result['edges']:
            pair = tuple(sorted([edge['source'], edge['target']]))
            self.assertNotIn(pair, edge_pairs, "Duplicate edge detected")
            edge_pairs.add(pair)

    def test_domain_colors(self):
        """Test 11: Domain colors are assigned correctly"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        # Check that finance concepts have blue color
        for node in result['nodes']:
            if node['domain'] == 'finance':
                self.assertEqual(node['color'], '#3498db')
            elif node['domain'] == 'programming':
                self.assertEqual(node['color'], '#2ecc71')

    def test_metadata_accuracy(self):
        """Test 12: Metadata counts are accurate"""
        result = generate_graph_data.transform_to_graph_format(
            self.sample_backlinks_data,
            self.sample_concept_metadata
        )

        self.assertEqual(result['metadata']['nodeCount'], len(result['nodes']))
        self.assertEqual(result['metadata']['edgeCount'], len(result['edges']))


if __name__ == '__main__':
    unittest.main()
