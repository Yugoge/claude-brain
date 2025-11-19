# Knowledge System Configuration

This is a personal knowledge management and spaced repetition learning system built on Claude Code.

## System Overview

- **Purpose**: Multi-domain knowledge learning, management, and review
- **Supported Domains**: Finance, Programming, Language, Science, and more
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

## Core Commands

- `/learn <file-path>` - Start interactive Socratic learning from a material
- **`/save [topic]`** - **One-stop-shop**: Extract concepts as ultra-minimal Rems + discover typed relations + maintain graph + auto-sync to FSRS
- `/discover-relations <rem-id | --domain path>` - Discover typed relations for existing Rems using domain tutors
- `/review [topic]` - Review knowledge using FSRS algorithm (1-4 rating scale)
- `/sync-rems` - Manually sync all Rems to review schedule (auto-called by `/save`)
- `/progress [topic]` - View learning progress
- `/kb-init` - Initialize knowledge system

## Agents

- **book-tutor**: Socratic teaching for books/reports
- **language-tutor**: Language learning specialist
- **finance-tutor**: Finance domain specialist
- **programming-tutor**: Programming domain specialist
- **review-master**: Review conductor
- **knowledge-indexer**: Knowledge graph maintainer
- **analyst**: Universal AI assistant for research and problem-solving

**Agent Architecture**: The system uses three types of agents:
1. **Consultant Agents** (language-tutor, finance-tutor, programming-tutor, book-tutor) - Domain expert consultants providing JSON consultations
2. **Standalone Agents** (analyst, review-master) - User-facing interactive agents
3. **Utility Agents** (knowledge-indexer) - Background workers for system maintenance

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
**FORBIDDEN**: NEVER write inline Python code using `python3 -c "..."` or heredocs.

**All functionality is already implemented in scripts**:
- ✅ ALWAYS use scripts from `scripts/` directory
- ✅ ALWAYS import properly: `sys.path.append('scripts')`
- ❌ NEVER write inline Python calculations
- ❌ NEVER create temporary Python files
- ❌ NEVER use `python3 -c` for logic

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
  - See `docs/architecture/hooks.md` for complete documentation
- **Chats index**: `chats/index.json` tracks archived conversations with `metadata` aggregates
  - See `docs/architecture/conversation-index.md` for schema details
- **Rebuild utilities**:
  - `source venv/bin/activate && python scripts/knowledge-graph/rebuild-backlinks.py` - Rebuild bidirectional links