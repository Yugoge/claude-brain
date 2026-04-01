#!/usr/bin/env python3
"""
Agent Memory Utilities - Auto-Memory File Integration

Provides reusable memory operations for all consultant agents.
Uses Claude Code's built-in auto-memory system at /root/.claude/projects/-root/memory/

Usage:
    from scripts.agent_memory_utils import AgentMemory

    memory = AgentMemory()
    prefs = memory.get_all_preferences()
    memory.track_struggle("concept-name", difficulty=0.8, domain="finance")

Migration Note:
    Previously used MCP memory-server tools. Now uses auto-memory files
    at /root/.claude/projects/-root/memory/ via Read/Write/Edit tools.
    Auto-memory is always available (no MCP dependency, works in subprocesses).
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


# Auto-memory directory
MEMORY_DIR = Path("/root/.claude/projects/-root/memory")
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"


class AgentMemory:
    """Agent memory operations using auto-memory files.

    Auto-memory files are stored at /root/.claude/projects/-root/memory/
    Primary file: MEMORY.md (auto-loaded by Claude Code)
    Additional topic files: learning.md, patterns.md, etc.

    Agents interact with memory by:
    - Reading: Use Read tool on memory files
    - Searching: Use Grep tool to search memory directory
    - Writing: Use Write/Edit tools to append/modify memory files
    """

    def __init__(self):
        """Initialize memory client."""
        self.memory_dir = MEMORY_DIR
        self.memory_file = MEMORY_FILE

    # ==================== Query Operations ====================

    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Get user learning preferences from memory.

        Returns:
            dict: User preferences (difficulty, learning_pace, question_style, etc.)

        Auto-Memory:
            Read /root/.claude/projects/-root/memory/MEMORY.md
            Search for sections containing preference-related entries
        """
        # Agent should use Read tool on memory files
        # and parse preference-related sections
        pass

    def get_struggles(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get user's previous struggles with concepts.

        Args:
            domain: Optional domain filter (finance, programming, language, etc.)

        Returns:
            list: Struggle records with concept names and difficulty scores

        Auto-Memory:
            Use Grep tool to search for "struggle" or "quality=1" or "quality=2"
            in /root/.claude/projects/-root/memory/ files
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

        Auto-Memory:
            Use Grep tool to search for "{topic}" in memory files
        """
        pass

    def semantic_search(self, query: str, domain: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant concepts in memory files.

        Args:
            query: Search query
            domain: Optional domain filter
            limit: Max results to return

        Returns:
            list: Matching concepts with relevance scores

        Auto-Memory:
            Use Grep tool to search for "{query}" in memory directory
        """
        pass

    def get_related_concepts(self, concept_name: str) -> List[str]:
        """
        Get concepts related to a given concept.

        Args:
            concept_name: Concept to find relations for

        Returns:
            list: Related concept names

        Auto-Memory:
            Use Grep tool to search for "{concept_name}" in memory files
            Parse surrounding context for related concepts
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

        Auto-Memory:
            Use Edit tool to append to memory file:
            "Review: struggled with {concept_name}, difficulty={difficulty} on {timestamp}"
        """
        timestamp = datetime.now().isoformat()
        # Agent should use Edit tool to append to memory file
        pass

    def update_preference(self, key: str, value: Any):
        """
        Update user learning preference.

        Args:
            key: Preference key (difficulty, learning_pace, question_style, etc.)
            value: New preference value

        Auto-Memory:
            Use Edit tool to update preference entry in memory file
        """
        timestamp = datetime.now().isoformat()
        # Agent should use Edit tool to update memory file
        pass

    def save_concept(self, concept_name: str, domain: str, metadata: Dict[str, Any]):
        """
        Save concept to memory after learning session.

        Args:
            concept_name: Concept name
            domain: Knowledge domain
            metadata: Additional metadata (source, timestamp, material, etc.)

        Auto-Memory:
            Use Edit tool to append concept entry to memory file
        """
        # Agent should use Edit tool to append to memory file
        pass

    def create_relationship(self, from_concept: str, to_concept: str,
                          relation_type: str, strength: float = 0.7):
        """
        Record relationship between concepts in memory.

        Args:
            from_concept: Source concept
            to_concept: Target concept
            relation_type: Relation type (related_to, prerequisite_of, etc.)
            strength: Relationship strength (0.0-1.0)

        Auto-Memory:
            Use Edit tool to append relationship entry to memory file
        """
        # Agent should use Edit tool to append to memory file
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

        Auto-Memory:
            Use Grep tool to search for concept name in memory files
        """
        # Agent should use Grep tool on memory directory
        pass

    # ==================== Memory Operations for Analyst ====================

    def add_concept_node(self, concept_name: str, domain: str, metadata: Dict[str, Any]):
        """
        Add concept node to memory (Analyst agent specific).

        Args:
            concept_name: Concept name
            domain: Knowledge domain
            metadata: Metadata (question, timestamp, source, summary)

        Auto-Memory:
            Use Edit tool to append concept entry to memory file with:
            - Question context
            - Summary
            - Source
            - Timestamp
        """
        pass


# ==================== Example Usage (for documentation) ====================

def example_analyst_usage():
    """Example: How analyst agent uses memory with auto-memory files."""
    memory = AgentMemory()

    # Step 1: Query memory before answering
    # Agent uses Grep tool to search memory files
    user_question = "Explain Black-Scholes model"
    results = memory.semantic_search(user_question, domain="finance")

    if results:
        # Found previous discussion - incorporate context
        print("Based on our previous discussion of Black-Scholes...")
    else:
        # Fresh explanation
        print("Let me explain the Black-Scholes model...")

    # Step 2: Save concepts after answering
    # Agent uses Edit tool to append to memory files
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

    # Step 3: Record relationships
    # Agent uses Edit tool to append to memory files
    memory.create_relationship(
        "Black-Scholes Model",
        "Option Greeks",
        "prerequisite_of",
        strength=0.9
    )


def example_tutor_usage():
    """Example: How domain tutors use memory with auto-memory files."""
    memory = AgentMemory()

    # Get user preferences (Read tool on memory files)
    prefs = memory.get_all_preferences()
    difficulty_pref = prefs.get("difficulty", "medium")

    # Check for previous struggles (Grep tool on memory files)
    struggles = memory.get_struggles(domain="finance")

    # Track new struggle if user has difficulty (Edit tool on memory files)
    # if user_struggling:
    #     memory.track_struggle("call-option-intrinsic-value", difficulty=0.8, domain="finance")

    # Update preferences based on feedback (Edit tool on memory files)
    # if user_feedback == "too hard":
    #     memory.update_preference("difficulty", "easy")


if __name__ == "__main__":
    print("Agent Memory Utilities - Auto-Memory Integration")
    print("This module provides memory operations for consultant agents.")
    print(f"Memory directory: {MEMORY_DIR}")
    print(f"Primary memory file: {MEMORY_FILE}")
    print("\nImport in agent code:")
    print("  from scripts.agent_memory_utils import AgentMemory")
