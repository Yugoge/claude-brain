#!/usr/bin/env python3
"""
Archival Module Type Definitions

Standardized data structures for all archival module APIs.
See: docs/architecture/archival-api-spec.md
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path


# ============================================================================
# Validation & Check Result Types
# ============================================================================

@dataclass
class ValidationResult:
    """
    Standard validation result structure.

    Used by: preflight_checker, pre_validator_light, workflow_orchestrator

    Attributes:
        passed: True if validation passed (no critical errors)
        errors: List of critical errors (block execution)
        warnings: List of non-critical warnings (informational)
        data: Optional additional result data
    """
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Any] = None

    @property
    def has_errors(self) -> bool:
        """Check if there are any critical errors"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


@dataclass
class DetectionResult:
    """
    Session type detection result.

    Used by: session_detector

    Attributes:
        session_type: Type of session ('learn', 'ask', or 'review')
        rems_reviewed: List of Rem IDs reviewed (for review sessions)
        confidence: Confidence score (0.0 - 1.0)
        metadata: Optional additional detection metadata
    """
    session_type: Literal['learn', 'ask', 'review']
    rems_reviewed: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    @property
    def is_review(self) -> bool:
        """Check if this is a review session"""
        return self.session_type == 'review'

    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high (>= 0.8)"""
        return self.confidence >= 0.8


# ============================================================================
# File Operation Result Types
# ============================================================================

@dataclass
class WriteResult:
    """
    File write operation result.

    Used by: file_writer

    Attributes:
        success: True if all files written successfully
        created_files: List of created file paths
        modified_files: List of modified file paths
        errors: List of error messages (if any)
    """
    success: bool
    created_files: List[Path] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        """Total number of files affected"""
        return len(self.created_files) + len(self.modified_files)


# ============================================================================
# Enrichment Result Types
# ============================================================================

@dataclass
class TypedRelation:
    """
    Typed relation between two concepts.

    Attributes:
        from_id: Source Rem ID (can be new or existing)
        to_id: Target Rem ID (must exist in knowledge base)
        relation_type: Type of relation (prerequisite_of, synonym, etc.)
        rationale: Optional explanation for the relation
    """
    from_id: str
    to_id: str
    relation_type: str
    rationale: Optional[str] = None


@dataclass
class EnrichedRem:
    """
    Enriched Rem data structure with typed relations.

    Used by: workflow_orchestrator, domain tutors

    Attributes:
        rem_id: Unique identifier (subdomain-concept-slug)
        title: Concept title
        core_points: List of key knowledge points (3-5)
        usage_scenario: 1-2 sentence usage description
        my_mistakes: User's mistakes/misconceptions
        typed_relations: List of typed relations to other Rems
        output_path: Target file path for Rem creation
    """
    rem_id: str
    title: str
    core_points: List[str]
    usage_scenario: str = ""
    my_mistakes: List[str] = field(default_factory=list)
    typed_relations: List[TypedRelation] = field(default_factory=list)
    output_path: Optional[str] = None


# ============================================================================
# Session Metadata Types
# ============================================================================

@dataclass
class SessionMetadata:
    """
    Conversation session metadata.

    Used by: save_orchestrator, save_post_processor

    Attributes:
        id: Session identifier (descriptive slug)
        title: Session title
        summary: 2-3 sentence summary
        archived_file: Path to archived conversation file
        session_type: Type of session
        domain: Primary domain (finance, programming, etc.)
        subdomain: Subdomain (derivatives, web-dev, etc.)
        isced_path: Full ISCED classification path
        agent: Agent used (main, analyst, etc.)
        tags: List of tags
    """
    id: str
    title: str
    summary: str
    archived_file: str
    session_type: Literal['learn', 'ask', 'review']
    domain: str
    subdomain: str
    isced_path: str
    agent: str = "main"
    tags: List[str] = field(default_factory=list)


# ============================================================================
# Compatibility Aliases (for migration)
# ============================================================================

# Old dict-based return values can be converted to new types:
def validation_result_from_dict(d: Dict) -> ValidationResult:
    """Convert old dict format to ValidationResult"""
    return ValidationResult(
        passed=d.get('passed', d.get('valid', False)),
        errors=d.get('errors', []),
        warnings=d.get('warnings', []),
        data=d.get('data', d.get('auto_fixes', None))
    )


def detection_result_to_tuple(result: DetectionResult) -> tuple:
    """Convert DetectionResult to old tuple format (for backward compatibility)"""
    return (result.session_type, result.rems_reviewed, result.confidence)


# ============================================================================
# Type Validation Helpers
# ============================================================================

def validate_rem_id(rem_id: str) -> bool:
    """Validate Rem ID format: subdomain-concept-slug"""
    parts = rem_id.split('-')
    return len(parts) >= 2 and all(p.islower() or p.isdigit() for p in parts)


def validate_relation_type(relation_type: str) -> bool:
    """Validate relation type is one of the allowed types"""
    VALID_TYPES = {
        'prerequisite_of',
        'synonym',
        'contrasts_with',
        'related_to',
        'example_of',
        'component_of',
        'implements',
        'uses'
    }
    return relation_type in VALID_TYPES
