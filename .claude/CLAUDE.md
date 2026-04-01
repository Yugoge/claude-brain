# Knowledge System Configuration

This is a personal knowledge management and spaced repetition learning system built on Claude Code.

## System Overview

- **Purpose**: Multi-domain knowledge learning, management, and review
- **Supported Domains**: Finance, Programming, Language, Medicine, Law, Science, and more
- **Learning Method**: Socratic dialogue-based interactive teaching (not flashcards)
- **Knowledge Structure**: RemNote-style (hierarchy + bidirectional links + tags)
- **Classification**: Dual taxonomy (UNESCO ISCED + Dewey Decimal)
- **Review Algorithm**: FSRS (Free Spaced Repetition Scheduler) - 30-50% more efficient than traditional algorithms

## Directory Structure

```
knowledge-system/
├── .claude/                    # Claude Code configuration
├── learning-materials/         # Original learning materials + progress tracking
├── knowledge-base/            # Extracted knowledge (Rem-style)
├── .review/                   # Review system data (FSRS algorithm)
└── scripts/                   # Utility scripts
```

<!-- AUTO:command-list -->
- `ask.md` - Ask any question with automatic web research and comprehensive answers
- `deep-search.md` - Deep website exploration with iterative search strategy
- `diagnose-memory.md` - Diagnose MCP memory server issues
- `discover-relations.md` - Discover Relations Command
- `fact-check.md` - Analyze media bias and verify news claims using structural analysis
- `graph.md` - Graph Command
- `kb-init.md` - Initialize or reinitialize the knowledge system
- `learn.md` - Learn Command
- `maintain.md` - Run knowledge base maintenance tasks
- `memory-clear.md` - Clear all memories (nuclear option with confirmation)
- `memory-export.md` - Export memories to external file formats (JSON, Markdown)
- `memory-forget.md` - Remove specific memories by topic or name
- `memory-show.md` - Display memories in a readable format with filtering options
- `memory-status.md` - View current memory status and stored memories
- `progress.md` - View learning progress across all materials or specific domains
- `reflect-search.md` - Reflection-driven iterative search with goal evaluation
- `research-deep.md` - Multi-source deep research with 15-20 iterative searches
- `review.md` - Review Command
- `save.md` - Save Command
- `search-tree.md` - Tree search exploration with MCTS-inspired path evaluation
- `site-navigate.md` - Intelligent site navigation simulating "click-through" exploration
- `test.md` - Test Command
<!-- /AUTO:command-list -->

<!-- AUTO:agent-list -->
- `analyst.md` - Universal AI assistant for comprehensive research, analysis, and problem-solving. Use for any question that needs web research, code execution, file operations, or deep analysis. Fully replaces Claude.ai web interface with complete tool access.
- `book-tutor.md` - Learning Materials Expert Consultant - Provides JSON consultation for books, reports, papers, and documents with Socratic questioning strategies
- `classification-expert.md` - Domain classification specialist using UNESCO ISCED-F 2013 taxonomy
- `finance-tutor.md` - Quantitative Finance Domain Expert Consultant - Provides JSON consultation for calculation verification, scenario analysis, risk assessment, and market context
- `journalist.md` - Journalism & Media Analysis Expert - Provides JSON consultation for structural bias analysis, funding source verification, editorial independence assessment, and red-line testing based on issue hierarchy
- `language-tutor.md` - Language Domain Expert Consultant - Provides JSON consultation for grammar production, collocation testing, syntax construction, pronunciation practice, and CEFR-aligned Socratic strategies
- `law-tutor.md` - Legal Domain Expert Consultant - Provides JSON consultation for legal reasoning, case analysis, statutory interpretation, and jurisprudence
- `medicine-tutor.md` - Medical & Healthcare Domain Expert Consultant - Provides JSON consultation for diagnostic reasoning, treatment evaluation, medical terminology, and clinical knowledge
- `programming-tutor.md` - Programming Domain Expert Consultant - Provides JSON consultation for syntax patterns, algorithm analysis, debugging strategies, and best practices
- `review-master.md` - FSRS Review Expert Consultant - Provides JSON guidance for Socratic review questions, quality assessment, and memory optimization
- `science-tutor.md` - Science Domain Expert Consultant - Provides JSON consultation for scientific method, experimental design, hypothesis testing, and multi-disciplinary science (physics, chemistry, biology, earth science)
<!-- /AUTO:agent-list -->

**Agent Architecture**: The system uses consultant agents only:
- **Consultant Agents** (language-tutor, finance-tutor, programming-tutor, book-tutor, medicine-tutor, law-tutor, science-tutor, review-master, analyst) - Domain expert consultants providing JSON consultations to main agent

**Key Point**: All learning/review interactions are conducted by the **main agent**. Consultant agents provide silent JSON guidance behind the scenes. Claude Code architecture does not support subagents directly interacting with users.

**For agent design decisions**, see `docs/architecture/agent-classification.md`

## Learning Flow

1. User adds material to `learning-materials/`
2. Use `/learn` to start interactive Socratic learning session
3. AI extracts content incrementally (context-aware chunking)
4. AI asks Socratic questions based on content
5. User responses are evaluated and learning progress tracked
6. At session end, user runs `/save` which:
   - Extracts concepts from conversation as ultra-minimal Rems (100-120 tokens)
   - **Discovers typed relations via domain tutors (mandatory for core domains)**
   - Normalizes wikilinks (`[[id]]` → `[Title](path.md)`)
   - Rebuilds backlinks index with typed relations
   - Optionally materializes inferred links (with preview)
   - **Automatically syncs new Rems to FSRS review schedule**
   - Saves conversation archive for future reference
7. FSRS algorithm schedules reviews based on difficulty, stability, and retrievability
8. Hook reminds user when reviews are due

## Important Notes

- Large files are processed incrementally to manage context limits
- Each learning material has a `.progress.md` file tracking position
- Knowledge points are added incrementally (learn as you go)
- All content stored as Markdown for Git-friendly versioning
- Bidirectional links maintained automatically in `backlinks.json`


## Script Usage Requirements

**MANDATORY**: You MUST use existing scripts for ALL operations.
**FORBIDDEN**: NEVER write inline Python code using `source venv/bin/activate && python3 -c "..."` or heredocs.

**All functionality is already implemented in scripts**:
- ✅ ALWAYS use scripts from `scripts/` directory
- ✅ ALWAYS import properly: `sys.path.append('scripts')`
- ❌ NEVER write inline Python calculations
- ❌ NEVER create temporary Python files
- ❌ NEVER use `source venv/bin/activate && python3 -c` for logic

**Violation of this rule is considered a CRITICAL ERROR.**

**For precise script locations**, see `docs/reference/script-locations.md` for complete mapping.

See individual command files for complete implementation examples with proper imports.

## Token Awareness & File Processing

**Complete documentation**: `docs/guides/TOKEN_PROCESSING.md`

### Quick Rules

**NEVER:**
- ❌ Use Read tool on PDF files (use `extract-pdf-chunk.py`)
- ❌ Read large files without token estimation first
- ❌ Assume file size alone indicates safety

**ALWAYS:**
- ✅ Run `source venv/bin/activate && python scripts/estimate_tokens.py <file>` before reading PDFs
- ✅ Compress PDFs >10MB before learning
- ✅ Use `extract-pdf-chunk.py` for ALL PDF reading

**See `docs/guides/TOKEN_PROCESSING.md` for complete 4-phase workflow, compression presets, and error handling.**

## Hooks & Indexes

- **Hooks**: `.claude/settings.json` provides safety checks and automation
  - **NEW**: Review gating - Enforces mini review session (1 rem) before input commands
    - **Triggers**: `/learn`, `/ask`, `/fact-check` (configurable via env)
    - **Purpose**: Maintain input-output balance, prevent knowledge accumulation without consolidation
    - **Workflow**: Hook → Select random due rem → Main agent conducts review → Update FSRS → Execute command
    - **Configuration**: Environment variables (`REVIEW_GATE_ENABLED`, `REVIEW_GATE_COMMANDS`)
    - **Rationale**: `/save` is output task, no gating needed
  - See `docs/architecture/hooks.md` for complete documentation
- **Chats index**: `chats/index.json` tracks archived conversations with `metadata` aggregates
  - See `docs/architecture/conversation-index.md` for schema details
- **Rebuild utilities**:
  - `source venv/bin/activate && python scripts/knowledge-graph/rebuild-backlinks.py` - Rebuild bidirectional links