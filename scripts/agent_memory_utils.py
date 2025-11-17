#!/usr/bin/env python3
"""
Agent Memory Utilities - MCP Memory Server Integration

Provides reusable memory operations for all consultant agents.
Used by: analyst, book-tutor, finance-tutor, language-tutor, programming-tutor

Usage:
    from scripts.agent_memory_utils import AgentMemory

    memory = AgentMemory()
    prefs = memory.get_all_preferences()
    memory.track_struggle("concept-name", difficulty=0.8, domain="finance")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class AgentMemory:
    """Agent memory operations using MCP memory server tools."""

    def __init__(self):
        """Initialize memory client."""
        # MCP tools are called via Claude Code's MCP integration
        # This class provides a convenient Python interface
        pass

    # ==================== Query Operations ====================

    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Get user learning preferences from memory.

        Returns:
            dict: User preferences (difficulty, learning_pace, question_style, etc.)

        MCP Call:
            mcp__memory-server__search_nodes(query="user preferences")
        """
        # Agent should call: mcp__memory-server__search_nodes
        # with query="user preferences"
        # Returns: nodes containing preference observations
        pass

    def get_struggles(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get user's previous struggles with concepts.

        Args:
            domain: Optional domain filter (finance, programming, language, etc.)

        Returns:
            list: Struggle records with concept names and difficulty scores

        MCP Call:
            mcp__memory-server__search_nodes(query="struggle {domain}")
        """
        pass

    def query_context(self, topic: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query related concepts and previous learning context.

        Args:
            topic: Topic to search for
            domain: Optional domain filter

        Returns:
            list: Related concepts and context from previous sessions

        MCP Call:
            mcp__memory-server__search_nodes(query="{topic} {domain}")
        """
        pass

    def semantic_search(self, query: str, domain: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search for relevant concepts in memory.

        Args:
            query: Search query
            domain: Optional domain filter
            limit: Max results to return

        Returns:
            list: Matching concepts with relevance scores

        MCP Call:
            mcp__memory-server__search_nodes(query="{query} {domain}")
        """
        pass

    def get_related_concepts(self, concept_name: str) -> List[str]:
        """
        Get concepts related to a given concept.

        Args:
            concept_name: Concept to find relations for

        Returns:
            list: Related concept names

        MCP Call:
            mcp__memory-server__open_nodes(names=[concept_name])
            Then extract relations from returned node
        """
        pass

    # ==================== Write Operations ====================

    def track_struggle(self, concept_name: str, difficulty: float, domain: str):
        """
        Track user struggle with a concept.

        Args:
            concept_name: Concept user struggled with
            difficulty: Difficulty score (0.0-1.0)
            domain: Knowledge domain

        MCP Call:
            mcp__memory-server__add_observations(
                observations=[{
                    "entityName": concept_name,
                    "contents": [f"Review: struggled with difficulty={difficulty} on {timestamp}"]
                }]
            )
        """
        timestamp = datetime.now().isoformat()
        # Agent should call: mcp__memory-server__add_observations
        pass

    def update_preference(self, key: str, value: Any):
        """
        Update user learning preference.

        Args:
            key: Preference key (difficulty, learning_pace, question_style, etc.)
            value: New preference value

        MCP Call:
            mcp__memory-server__add_observations(
                observations=[{
                    "entityName": "user_preferences",
                    "contents": [f"{key}={value} updated on {timestamp}"]
                }]
            )
        """
        timestamp = datetime.now().isoformat()
        # Agent should call: mcp__memory-server__add_observations
        pass

    def save_concept(self, concept_name: str, domain: str, metadata: Dict[str, Any]):
        """
        Save concept to memory after learning session.

        Args:
            concept_name: Concept name
            domain: Knowledge domain
            metadata: Additional metadata (source, timestamp, material, etc.)

        MCP Call:
            mcp__memory-server__create_entities(
                entities=[{
                    "name": concept_name,
                    "entityType": domain,
                    "observations": [json.dumps(metadata)]
                }]
            )
        """
        # Agent should call: mcp__memory-server__create_entities
        pass

    def create_relationship(self, from_concept: str, to_concept: str,
                          relation_type: str, strength: float = 0.7):
        """
        Create relationship between concepts in memory.

        Args:
            from_concept: Source concept
            to_concept: Target concept
            relation_type: Relation type (related_to, prerequisite_of, etc.)
            strength: Relationship strength (0.0-1.0)

        MCP Call:
            mcp__memory-server__create_relations(
                relations=[{
                    "from": from_concept,
                    "to": to_concept,
                    "relationType": relation_type
                }]
            )
        """
        # Agent should call: mcp__memory-server__create_relations
        pass

    # ==================== Context Extraction ====================

    def extract_concepts_from_answer(self, answer: str) -> List[Dict[str, Any]]:
        """
        Extract key concepts from an answer or explanation.

        Args:
            answer: Text to extract concepts from

        Returns:
            list: Extracted concepts with metadata

        Note: This is a helper for agents. Actual implementation
        should use NLP or keyword extraction based on domain.
        """
        # Simple implementation: extract [[wikilinks]] and capitalize terms
        # Agents can override with domain-specific logic
        concepts = []
        # Extract [[concept-id]] patterns
        import re
        wikilinks = re.findall(r'\[\[([^\]]+)\]\]', answer)
        for link in wikilinks:
            concepts.append({
                "name": link,
                "domain": "unknown"  # Agent should determine domain
            })
        return concepts

    def find_related_concepts(self, concept: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Find concepts related to a given concept.

        Args:
            concept: Concept dict with 'name' and 'domain'

        Returns:
            list: Related concepts

        MCP Call:
            mcp__memory-server__search_nodes(query=concept["name"])
        """
        # Agent should call: mcp__memory-server__search_nodes
        # and extract related concepts from results
        pass

    # ==================== Memory Operations for Analyst ====================

    def add_concept_node(self, concept_name: str, domain: str, metadata: Dict[str, Any]):
        """
        Add concept node to memory graph (Analyst agent specific).

        Args:
            concept_name: Concept name
            domain: Knowledge domain
            metadata: Metadata (question, timestamp, source, summary)

        MCP Call:
            mcp__memory-server__create_entities(
                entities=[{
                    "name": concept_name,
                    "entityType": domain,
                    "observations": [
                        f"Question: {metadata.get('question', '')}",
                        f"Summary: {metadata.get('summary', '')}",
                        f"Source: {metadata.get('source', 'analyst')}",
                        f"Timestamp: {metadata.get('timestamp', datetime.now().isoformat())}"
                    ]
                }]
            )
        """
        pass


# ==================== Example Usage (for documentation) ====================

def example_analyst_usage():
    """Example: How analyst agent uses memory."""
    memory = AgentMemory()

    # Step 1: Query memory before answering
    user_question = "Explain Black-Scholes model"
    results = memory.semantic_search(user_question, domain="finance")

    if results:
        # Found previous discussion - incorporate context
        print("Based on our previous discussion of Black-Scholes...")
    else:
        # Fresh explanation
        print("Let me explain the Black-Scholes model...")

    # Step 2: Save concepts after answering
    concepts = ["Black-Scholes Model", "Option Pricing", "Stochastic Calculus"]
    for concept in concepts:
        memory.save_concept(
            concept,
            "finance",
            {
                "question": user_question,
                "timestamp": datetime.now().isoformat(),
                "source": "analyst-conversation"
            }
        )

    # Step 3: Create relationships
    memory.create_relationship(
        "Black-Scholes Model",
        "Option Greeks",
        "prerequisite_of",
        strength=0.9
    )


def example_tutor_usage():
    """Example: How domain tutors use memory."""
    memory = AgentMemory()

    # Get user preferences
    prefs = memory.get_all_preferences()
    difficulty_pref = prefs.get("difficulty", "medium")

    # Check for previous struggles
    struggles = memory.get_struggles(domain="finance")

    # Track new struggle if user has difficulty
    if user_struggling:
        memory.track_struggle("call-option-intrinsic-value", difficulty=0.8, domain="finance")

    # Update preferences based on feedback
    if user_feedback == "too hard":
        memory.update_preference("difficulty", "easy")


if __name__ == "__main__":
    print("Agent Memory Utilities - MCP Integration")
    print("This module provides memory operations for consultant agents.")
    print("\nImport in agent code:")
    print("  from scripts.agent_memory_utils import AgentMemory")
