# Scripts Directory Organization

This directory contains all scripts for the Knowledge System, organized by functional area.

## Directory Structure

```
scripts/
├── analytics/                # Learning analytics
├── archival/                 # Conversation archival system
├── hooks/                    # Hook scripts
├── knowledge-graph/          # Knowledge graph maintenance
├── learning-goals/           # Learning goals tracking
├── learning-materials/       # PDF and material processing
├── memory/                   # MCP memory operations
├── migration/                # Data migration utilities
├── progress/                 # Progress tracking
├── review/                   # FSRS review system
├── services/                 # Service utilities
├── utilities/                # General utilities
├── utils/                    # Helper functions
├── validation/               # Validation and checking
└── visualizations/           # HTML dashboards
```

## Categories

### Analytics (`analytics/`)
Performance tracking, telemetry, insights generation, and dashboards.

### Archival (`archival/`)
Conversation archival, concept extraction, and session management. Used by `/save` command.

### Hooks (`hooks/`)
Git hooks and event-triggered scripts for system automation.

### Knowledge Graph (`knowledge-graph/`)
Graph generation, backlinks, and relationship management.

### Learning Goals (`learning-goals/`)
Goal tracking and management.

### Learning Materials (`learning-materials/`)
PDF processing, compression, token estimation, and content extraction.

### Memory (`memory/`)
MCP memory server integration and unified memory system.

### Migration (`migration/`)
Data migration utilities for schema and format changes.

### Progress (`progress/`)
Progress tracking, calculation, formatting, and recommendations.

### Review System (`review/`)
FSRS algorithm implementation and review scheduling.

### Services (`services/`)
Service management and utilities.

### Utilities (`utilities/`)
General purpose scripts for maintenance and operations.

### Utils (`utils/`)
Helper functions and shared utilities.

### Validation (`validation/`)
Data validation, schema checking, and requirement verification.

### Visualizations (`visualizations/`)
HTML dashboards for analytics and knowledge graph visualization.

## Import Path Updates

When importing from scripts in Python code, use:

```python
import sys
sys.path.append('scripts/category')  # e.g., 'scripts/review'
```

Or for cross-category imports:
```python
sys.path.extend(['scripts/review', 'scripts/analytics'])
```