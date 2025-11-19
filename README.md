# Personal Knowledge System

An AI-powered personal knowledge management and spaced repetition learning system built on Claude Code.

## Overview

This system combines Socratic dialogue-based learning with scientifically-optimized spaced repetition to help you build and retain deep knowledge across multiple domains.

**Key Features:**
- **Interactive Learning**: Socratic dialogue, not passive reading
- **Smart Review**: FSRS algorithm for optimal retention (30-50% more efficient than SM-2)
- **Knowledge Graph**: RemNote-style organization with bidirectional links and typed relations
- **Multi-Domain**: Finance, Programming, Language, Science, and more
- **Multi-Format**: PDF, EPUB, PowerPoint, Word, Excel, Markdown
- **Git-Friendly**: Everything stored as Markdown for version control
- **Token-Optimized**: 73% token savings through three-party consultation architecture

## Quick Start

### 1. Initialize System

```bash
/kb-init
```

### 2. Add Learning Materials

Place your materials in the appropriate domain folder:

```
learning-materials/
├── finance/
│   └── options-trading.pdf
├── programming/
│   └── algorithms-textbook.pdf
└── language/
    └── spanish-grammar.epub
```

### 3. Start Learning

```bash
/learn learning-materials/finance/options-trading.pdf
```

The AI tutor will:
- Present passages from the material
- Ask Socratic questions to test understanding
- Extract concepts as knowledge Rems
- Track your progress automatically

### 4. Save Your Session

```bash
/save options-trading-session
```

This one command will:
- Extract concepts as ultra-minimal Rems (100-120 tokens)
- Discover typed relations via domain tutors (mandatory for core domains)
- Normalize wikilinks automatically
- Rebuild knowledge graph with typed relations
- Sync to FSRS review schedule
- Archive the conversation

### 5. Review Regularly

```bash
/review                    # Review all due concepts
/review finance            # Review finance concepts only
/review [[concept-id]]     # Review specific concept
```

### 6. Discover Relations (Optional)

For existing Rems without typed relations, use:

```bash
/discover-relations csharp-null-conditional-operator  # Single Rem
/discover-relations --domain 0611-computer-use        # All Rems in domain
```

This retrospectively discovers semantic relationships (synonyms, prerequisites, contrasts) using domain tutors.

### 7. Track Progress

```bash
/progress                  # Overall progress
/progress finance          # Domain-specific
/progress learning-materials/finance/options-trading.pdf  # Material-specific
```

## Core Commands

| Command | Description |
|---------|-------------|
| `/learn <file-path>` | Start interactive Socratic learning session |
| `/save [topic]` | Extract concepts, maintain graph, archive conversation (all-in-one) |
| `/discover-relations <rem-id\|--domain path>` | Discover typed relations for existing Rems |
| `/review [domain\|concept-id]` | Review concepts using FSRS algorithm |
| `/sync-rems` | Manually sync Rems to review schedule (auto-called by `/save`) |
| `/progress [domain\|file-path]` | View learning progress and analytics |
| `/ask <question>` | Ask any question with automatic web research |
| `/visualize [domain]` | Generate interactive knowledge graph visualization |
| `/kb-init` | Initialize or repair knowledge system |

## System Architecture

```
knowledge-system/
├── .claude/                    # Claude Code configuration
│   ├── commands/               # Slash commands (/learn, /review, /ask, /save)
│   ├── agents/                 # Specialized AI tutors
│   │   ├── book-tutor/         # General learning consultant
│   │   ├── language-tutor/     # Language domain consultant
│   │   ├── finance-tutor/      # Finance domain consultant
│   │   ├── programming-tutor/  # Programming domain consultant
│   │   ├── review-master/      # Review conductor (standalone)
│   │   ├── analyst/            # Universal Q&A (standalone)
│   │   └── knowledge-indexer/  # Graph maintenance (utility)
│   ├── hooks/                  # Event-driven automation scripts
│   ├── settings.json           # Hook configuration
│   └── CLAUDE.md               # System instructions
│
├── learning-materials/         # Original learning materials + progress
│   ├── .index.json             # Material metadata index
│   ├── _templates/             # Progress file templates
│   ├── finance/                # Finance domain materials
│   ├── language/               # Language learning materials
│   └── [domain]/               # Other domain materials
│
├── knowledge-base/             # Extracted knowledge (Rem-style)
│   ├── _index/                 # Auto-generated indexes
│   │   ├── backlinks.json      # Bidirectional link index
│   │   └── graph-data.json     # Knowledge graph cache
│   ├── _taxonomy/              # Taxonomy reference files
│   │   ├── 00-generic-programmes-and-qualifications/
│   │   ├── 01-education/
│   │   ├── 02-arts-and-humanities/
│   │   ├── 03-social-sciences-journalism-and-information/
│   │   ├── 04-business-administration-and-law/
│   │   ├── 05-natural-sciences-mathematics-and-statistics/
│   │   ├── 06-information-and-communication-technologies-icts/
│   │   ├── 07-engineering-manufacturing-and-construction/
│   │   ├── 08-agriculture-forestry-fisheries-and-veterinary/
│   │   ├── 09-health-and-welfare/
│   │   └── 10-services/
│   ├── _templates/             # Rem templates
│   ├── 02-arts-and-humanities/ # Language Rems (ISCED code 02)
│   │   └── 023-languages/
│   ├── 03-social-sciences-journalism-and-information/
│   │   └── 031-social-and-behavioural-sciences/
│   ├── 04-business-administration-and-law/  # Finance Rems (ISCED code 04)
│   │   └── 041-business-and-administration/
│   └── 06-information-and-communication-technologies-icts/  # Programming Rems (ISCED code 06)
│       └── 061-ict-use/
│
├── .review/                    # FSRS review system data
│   ├── schedule.json           # FSRS scheduling data
│   ├── history.json            # Review history
│   ├── adaptive-profile.json   # Adaptive difficulty profile
│   ├── analytics-cache.json    # Pre-computed analytics
│   ├── insights.json           # Learning insights
│   ├── learning-goals.json     # Learning goals tracking
│   ├── adaptive-history/       # Historical adaptive data
│   └── backups/                # Schedule backups
│
├── chats/                      # Conversation archives
│   ├── index.json              # Searchable conversation index
│   ├── README.md               # Archive documentation
│   ├── _templates/             # Conversation templates
│   ├── 2025-10/                # Monthly archive (October)
│   └── 2025-11/                # Monthly archive (November)
│
└── scripts/                    # Utility scripts
    ├── analytics/              # Learning analytics
    ├── archival/               # Conversation archival
    ├── hooks/                  # Hook utilities
    ├── knowledge-graph/        # Graph maintenance (rebuild-backlinks.py, etc.)
    ├── learning-goals/         # Goals tracking
    ├── learning-materials/     # File parsers (extract-pdf-chunk.py, parse-epub.py)
    ├── memory/                 # MCP memory integration
    ├── migration/              # Data migration utilities
    ├── progress/               # Progress tracking
    ├── review/                 # FSRS algorithm implementation
    ├── services/               # Service utilities
    ├── utilities/              # General utilities
    ├── utils/                  # Helper functions
    ├── validation/             # Data validation
    └── visualizations/         # Knowledge graph visualization
```

## Agent Architecture

The system uses a **three-party consultation pattern** for optimal token efficiency:

1. **Consultant Agents** (Silent domain experts):
   - `language-tutor`, `finance-tutor`, `programming-tutor`, `book-tutor`
   - Provide JSON consultations to main agent
   - Never interact with user directly
   - ~73% token savings vs direct interaction

2. **Standalone Agents** (User-facing):
   - `analyst` - Universal Q&A with web research
   - `review-master` - Conducts spaced repetition sessions

3. **Utility Agents** (Background workers):
   - `knowledge-indexer` - Maintains knowledge graph structure

**See**: `docs/architecture/agent-classification.md` for details

## Hook System

The system uses **9 hooks** for automatic safety checks and maintenance:

| Hook | Purpose |
|------|---------|
| **SessionStart** | Log session timestamp |
| **UserPromptSubmit** | Scan for dangerous commands in user input |
| **PreToolUse (Bash)** | Block dangerous AI commands |
| **PreToolUse (Edit)** | Protect auto-generated indexes |
| **PreToolUse (Read)** | Warn about large files (>5MB) |
| **PostToolUse (Edit)** | Auto-rebuild backlinks after edits |
| **SubagentStop** | Audit trail for review sessions |
| **PreCompact** | Backup conversation index |
| **Stop/SessionEnd** | Log session completion |

**Key Automation**: Every time you edit a knowledge file, the backlinks index is automatically rebuilt. No manual maintenance needed!

**See**: `docs/architecture/hooks.md` for full documentation

## Large File Handling

The system automatically handles large files using smart chunking:

### Content-Aware Processing
- **Text-heavy PDFs** (textbooks): 5-10 pages at a time
- **Image-heavy PDFs** (picture books): 1 page at a time
- **Mixed content**: Adaptive 3-5 pages

### Size Thresholds
| Size Range | Action | Method |
|-----------|--------|---------|
| < 5 MB | ✅ Read normally | Standard `Read` tool |
| 5-20 MB | ⚠️ Warn but allow | `Read` with warning |
| > 20 MB | ⛔ Block `Read` | **MUST** use chunking |

### Zero-Pollution Single-Page Extraction

For image-heavy PDFs, the system extracts one page at a time to temporary files, reads with full visual recognition, then immediately deletes. Zero permanent file pollution.

**See**: `.claude/CLAUDE.md` for token processing guidelines

## Knowledge Graph Features

### Rem-Style Knowledge Points

Each concept is stored as a Markdown file with:
- **Hierarchical structure**: Parent → Child relationships
- **Bidirectional links**: `[[concept-a]]` ↔ `[[concept-b]]`
- **Typed relations**: synonym, antonym, prerequisite_of, etc.
- **Tags**: Domain, difficulty, topic tags
- **Dual taxonomy**: UNESCO ISCED + Dewey Decimal codes
- **Metadata**: Creation date, review history, FSRS data

### Minimal Rem Format

Rems are intentionally brief (target 100-120 tokens) to enable high-throughput reviews:
- 3-5 core memory points
- 1 personal mistake/insight
- 1-sentence usage scenario
- Related concepts with reasons
- learning_audit metadata

**See**: `docs/architecture/standards/REM_FORMAT_GUIDELINES.md`

### Typed Relations

The system supports typed concept relationships:
- **Lexical**: synonym, antonym, hypernym, hyponym, part_of
- **Conceptual**: is_a, prerequisite_of, cause_of, example_of
- **Comparative**: contrasts_with, analogous_to, related

**Discovery Methods**:
- **Automatic**: During `/save` (mandatory for programming, language, finance, science)
- **Manual**: Run `/discover-relations` on existing Rems

**See**: `docs/architecture/standards/RELATION_TYPES.md`

## Review System (FSRS)

- **Algorithm**: FSRS (Free Spaced Repetition Scheduler)
- **Efficiency**: 30-50% more efficient than traditional SM-2
- **Rating Scale**: 1-4 (1 = hard, 2 = medium, 3 = good, 4 = easy)
- **Adaptive Intervals**: Based on difficulty, stability, and retrievability
- **Conversation-based**: Not flashcards - test through Socratic dialogue

## Maintenance Scripts

The system includes automated maintenance via hooks. For manual operations:

```bash
# Rebuild bidirectional links with typed & inferred relations
python3 scripts/knowledge-graph/rebuild-backlinks.py

# Convert [[wikilinks]] to clickable file links
python3 scripts/knowledge-graph/normalize-links.py --mode replace

# Add typed relation between concepts (with auto-reciprocal)
python3 scripts/knowledge-graph/add-relation.py \
  --from call-option --to put-option --type antonym

# Materialize two-hop inferred links (preview first!)
python3 scripts/knowledge-graph/materialize-inferred-links.py --dry-run

# Reset spaced repetition schedule (NUCLEAR OPTION)
python3 scripts/review/reset-schedule.py --full-reset
```

All scripts support:
- `--dry-run` - Preview changes without writing
- `--verbose` - Detailed debug output
- `--help` - Full usage documentation

**See**: `docs/archive/guides/REBUILD_UTILITIES.md`

## Universal Q&A System

```bash
/ask "Explain quantum computing"
```

The **analyst** agent will:
- 🔍 Search the web automatically
- 📚 Check your existing knowledge base
- 💻 Execute code if needed
- 📖 Cite all sources

After `/ask` or `/learn`, use `/save` to extract concepts and archive the conversation.

## Visualization

```bash
/visualize              # Full knowledge graph (all domains)
/visualize finance      # Finance concepts only
```

**Features**:
- 🎨 D3.js force-directed graph with domain-colored nodes
- 🔍 Interactive: zoom, pan, drag, click for details
- 🔗 Hover to highlight connected concepts
- 🔎 Search to filter and focus
- 📊 Auto-detected clusters
- 📈 Node size = review count

Opens `knowledge-graph.html` in your browser.

## Troubleshooting

### "Context limit exceeded"
- Materials are chunked automatically
- Continue with `/learn` command to resume

### "Broken links detected"
- Run `python3 scripts/knowledge-graph/rebuild-backlinks.py`
- Check `knowledge-base/_index/backlinks.json`

### "No concepts due for review"
- Check `.review/schedule.json`
- View next review date with `/progress`

### "Agent not found"
- Verify agents exist in `.claude/agents/`
- Run `/kb-init` to repair

## Best Practices

### Learning
- **Daily consistency**: 30-60 minutes daily beats irregular long sessions
- **Active engagement**: Answer questions thoughtfully, don't rush
- **Make connections**: Link new concepts to existing knowledge
- **Review regularly**: Follow FSRS schedule for optimal retention

### Organization
- **One domain per material**: Place files in appropriate domain folder
- **Descriptive filenames**: Use clear, searchable names
- **Tag generously**: Tags help discover related concepts
- **Link proactively**: Create `[[links]]` during learning for better recall

### Review
- **Be honest**: Ratings must be accurate for FSRS to work
- **Don't cram**: Spaced repetition is more effective than massing
- **Apply knowledge**: Think about real-world applications
- **Note weak spots**: Concepts with low ratings need extra attention

## Git Workflow

### Initial Setup
```bash
git remote add origin <your-github-repo>
git push -u origin main
```

### Regular Commits
```bash
# After learning sessions
git add .
git commit -m "Learning session: options-trading - 5 concepts"
git push

# After review sessions
git add .review/
git commit -m "Review session: 10 concepts"
git push
```

### Sync Across Devices
```bash
git pull   # Before starting work
git push   # After sessions
```

## Documentation

### For Users
- **[README.md](./README.md)** - This file (quick start and overview)
- **[.claude/CLAUDE.md](./.claude/CLAUDE.md)** - System instructions and guidelines

### For Developers
- **[docs/README.md](./docs/README.md)** - Complete system documentation index
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Architecture overview and design
- **[docs/architecture/](./docs/architecture/)** - Detailed architecture documentation
- **[docs/architecture/standards/](./docs/architecture/standards/)** - Standards and conventions

### Archives
- **[docs/archive/](./docs/archive/)** - Historical documentation and deprecated features
- **[docs/archive/deprecated/](./docs/archive/deprecated/)** - Phase 2 baseline documentation

## Contributing

This is a personal knowledge system template. Customize to your needs:

1. Add new domains to taxonomy
2. Create specialized agents for your fields
3. Modify progress tracking granularity
4. Adjust FSRS parameters for your learning style

## License

MIT License - Use freely for personal learning

## Credits

Built with Claude Code by Anthropic

Inspired by SuperMemo, RemNote, and Zettelkasten methodology

---

Happy learning! 🎓
