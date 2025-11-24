# Personal Knowledge System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.com/code)
[![FSRS Algorithm](https://img.shields.io/badge/Review-FSRS-green)](https://github.com/open-spaced-repetition/fsrs4anki)

An AI-powered personal knowledge management and spaced repetition learning system built on Claude Code. Combines Socratic dialogue-based learning with scientifically-optimized spaced repetition for deep knowledge retention across multiple domains.

## ✨ Key Features

- **Interactive Learning**: Socratic dialogue, not passive reading
- **Smart Review**: FSRS algorithm for optimal retention (30-50% more efficient than traditional SM-2)
- **Knowledge Graph**: RemNote-style organization with bidirectional links and typed relations
- **Multi-Domain**: Finance, Programming, Language, Medicine, Law, Science, and more
- **Multi-Format**: PDF, EPUB, PowerPoint, Word, Excel, Markdown
- **Git-Friendly**: Everything stored as Markdown for version control
- **Token-Optimized**: 73% token savings through three-party consultation architecture

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Claude Code (Desktop or CLI)
- Git

### Installation

1. **Clone the repository**:
```bash
git clone <your-fork-url>
cd knowledge-system
```

2. **Set up Python environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Initialize the system**:
```bash
/kb-init
```

### Basic Workflow

```bash
# 1. Add learning material to appropriate domain folder
learning-materials/finance/options-trading.pdf

# 2. Start learning session
/learn learning-materials/finance/options-trading.pdf

# 3. AI tutor asks Socratic questions to test understanding

# 4. Save session (extracts concepts, maintains graph, syncs to review)
/save options-trading-session

# 5. Review regularly using spaced repetition
/review finance

# 6. Track your progress
/progress finance
```

---

## 📚 Core Commands

| Command | Description |
|---------|-------------|
| `/learn <file-path>` | Start interactive Socratic learning session |
| `/save [topic]` | Extract concepts, maintain graph, archive conversation (all-in-one) |
| `/review [domain│concept-id]` | Review concepts using FSRS algorithm |
| `/progress [domain│file-path]` | View learning progress and analytics |
| `/ask <question>` | Ask any question with automatic web research |
| `/discover-relations <rem-id│--domain path>` | Discover typed relations for existing Rems |
| `/visualize [domain]` | Generate interactive knowledge graph visualization |
| `/kb-init` | Initialize or repair knowledge system |

---

## 🏗️ System Architecture

```
knowledge-system/
├── .claude/                    # Claude Code configuration
│   ├── commands/               # Slash commands
│   ├── agents/                 # AI tutors (language, finance, programming, etc.)
│   ├── hooks/                  # Event-driven automation
│   ├── settings.json           # Hook configuration
│   └── CLAUDE.md               # System instructions
│
├── learning-materials/         # Original materials + progress tracking
│   ├── finance/
│   ├── language/
│   ├── programming/
│   └── [domain]/
│
├── knowledge-base/             # Extracted knowledge (Rem-style)
│   ├── _index/                 # Auto-generated indexes
│   │   ├── backlinks.json      # Bidirectional link index
│   │   └── graph-data.json     # Knowledge graph cache
│   ├── _taxonomy/              # UNESCO ISCED taxonomy reference
│   └── [ISCED-code]/           # Domain-organized concepts
│
├── .review/                    # FSRS review system
│   ├── schedule.json           # Review scheduling
│   ├── history.json            # Review history
│   └── adaptive-profile.json   # Adaptive difficulty
│
├── chats/                      # Conversation archives
│   ├── index.json              # Searchable index
│   └── [YYYY-MM]/              # Monthly archives
│
└── scripts/                    # Maintenance utilities
    ├── archival/               # Conversation processing
    ├── knowledge-graph/        # Graph maintenance
    ├── learning-materials/     # File parsers
    ├── review/                 # FSRS implementation
    └── hooks/                  # Hook utilities
```

### Agent Architecture

The system uses a **three-party consultation pattern** for optimal efficiency:

1. **Consultant Agents** (Silent domain experts):
   - `language-tutor`, `finance-tutor`, `programming-tutor`, `book-tutor`, `medicine-tutor`, `law-tutor`, `science-tutor`
   - Provide JSON consultations to main agent
   - Never interact with user directly
   - ~73% token savings vs direct interaction

2. **Standalone Agents** (User-facing):
   - `analyst` - Universal Q&A with web research
   - `review-master` - Conducts spaced repetition sessions

3. **Utility Agents** (Background workers):
   - `knowledge-indexer` - Maintains knowledge graph structure

**See**: `architecture/agent-classification.md` for details

---

## 💡 Core Concepts

### Rem-Style Knowledge Points

Each concept is stored as a minimal Markdown file (~100-120 tokens) with:
- **Hierarchical structure**: Parent → Child relationships
- **Bidirectional links**: `[[concept-a]]` ↔ `[[concept-b]]`
- **Typed relations**: synonym, antonym, prerequisite_of, etc.
- **Tags**: Domain, difficulty, topic tags
- **Dual taxonomy**: UNESCO ISCED + Dewey Decimal codes
- **Metadata**: Creation date, review history, FSRS data

### Typed Relations

The system supports semantic relationships:
- **Lexical**: synonym, antonym, hypernym, hyponym, part_of
- **Conceptual**: is_a, prerequisite_of, cause_of, example_of
- **Comparative**: contrasts_with, analogous_to, related

**Discovery**: Automatically during `/save` or manually via `/discover-relations`

**See**: `architecture/standards/RELATION_TYPES.md`

### FSRS Review System

- **Algorithm**: FSRS (Free Spaced Repetition Scheduler)
- **Efficiency**: 30-50% more efficient than traditional SM-2
- **Rating Scale**: 1-4 (1 = hard, 2 = medium, 3 = good, 4 = easy)
- **Adaptive**: Based on difficulty, stability, and retrievability
- **Conversation-based**: Not flashcards - test through Socratic dialogue

---

## 🔧 Automation & Hooks

The system uses **9 hooks** for automatic safety checks and maintenance:

| Hook | Purpose |
|------|---------|
| **SessionStart** | Display count of due reviews |
| **UserPromptSubmit** | Prevent secret commits, review reminders |
| **PreToolUse (Bash)** | Block dangerous AI commands |
| **PreToolUse (Edit)** | Protect critical indexes |
| **PreToolUse (Read)** | Warn about large files (>5MB) |
| **PostToolUse (Edit)** | Auto-rebuild backlinks after edits |
| **SubagentStop** | Audit trail for review sessions |
| **PreCompact** | Backup conversation index |
| **Stop/SessionEnd** | Log session completion |

**Key Automation**: Every time you edit a knowledge file, the backlinks index is automatically rebuilt. No manual maintenance needed!

**See**: `architecture/hooks.md`

---

## 📖 Learning Workflow

### 1. Add Learning Materials

Place materials in the appropriate domain folder:

```
learning-materials/
├── finance/
│   ├── options-trading.pdf
│   └── derivatives-handbook.epub
├── programming/
│   ├── python-deep-dive.pdf
│   └── algorithms-textbook.pdf
└── language/
    ├── french-grammar.epub
    └── spanish-vocab.pdf
```

### 2. Interactive Learning

```bash
/learn learning-materials/finance/options-trading.pdf
```

The AI tutor will:
- Present passages from the material
- Ask Socratic questions to test understanding
- Extract concepts as knowledge Rems
- Track your progress automatically

### 3. Save Session

```bash
/save options-trading-session
```

This one command:
- Extracts concepts as ultra-minimal Rems (100-120 tokens)
- Discovers typed relations via domain tutors
- Normalizes wikilinks automatically
- Rebuilds knowledge graph
- Syncs to FSRS review schedule
- Archives the conversation

### 4. Review Regularly

```bash
/review                    # Review all due concepts
/review finance            # Review finance concepts only
/review [[concept-id]]     # Review specific concept
```

### 5. Track Progress

```bash
/progress                  # Overall progress
/progress finance          # Domain-specific
/progress learning-materials/finance/options-trading.pdf  # Material-specific
```

---

## 📊 Knowledge Graph Visualization

```bash
/visualize              # Full knowledge graph (all domains)
/visualize finance      # Finance concepts only
```

**Features**:
- D3.js force-directed graph with domain-colored nodes
- Interactive: zoom, pan, drag, click for details
- Hover to highlight connected concepts
- Search to filter and focus
- Auto-detected clusters
- Node size = review count

Opens `knowledge-graph.html` in your browser.

---

## 🛠️ Maintenance & Utilities

### Automatic Maintenance

Most maintenance is automated via hooks. For manual operations:

```bash
# Rebuild bidirectional links with typed relations
python3 scripts/knowledge-graph/rebuild-backlinks.py

# Convert [[wikilinks]] to clickable file links
python3 scripts/knowledge-graph/normalize-links.py --mode replace

# Add typed relation between concepts (with auto-reciprocal)
python3 scripts/knowledge-graph/add-relation.py \
  --from call-option --to put-option --type antonym

# Materialize two-hop inferred links (preview first!)
python3 scripts/knowledge-graph/materialize-inferred-links.py --dry-run
```

All scripts support:
- `--dry-run` - Preview changes without writing
- `--verbose` - Detailed debug output
- `--help` - Full usage documentation

### Large File Handling

The system automatically handles large files using smart chunking:

**Content-Aware Processing**:
- **Text-heavy PDFs** (textbooks): 5-10 pages at a time
- **Image-heavy PDFs** (picture books): 1 page at a time
- **Mixed content**: Adaptive 3-5 pages

**Size Thresholds**:

| Size Range | Action | Method |
|-----------|--------|---------|
| < 5 MB | ✅ Read normally | Standard `Read` tool |
| 5-20 MB | ⚠️ Warn but allow | `Read` with warning |
| > 20 MB | ⛔ Block `Read` | **MUST** use chunking |

---

## 🎯 Best Practices

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

---

## 🔍 Troubleshooting

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

---

## 📝 Git Workflow

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

---

## 📚 Documentation

### For Users
- **[README.md](./README.md)** - This file (quick start and overview)
- **[architecture/](./architecture/)** - System architecture documentation

### For Developers
- **[architecture/agent-classification.md](./architecture/agent-classification.md)** - Agent types and consultation pattern
- **[architecture/hooks.md](./architecture/hooks.md)** - Hook system documentation
- **[architecture/conversation-index.md](./architecture/conversation-index.md)** - Conversation archive schema
- **[architecture/standards/](./architecture/standards/)** - Standards and conventions

---

## 🤝 Contributing

This is a personal knowledge system template. Customize to your needs:

1. Add new domains to taxonomy
2. Create specialized agents for your fields
3. Modify progress tracking granularity
4. Adjust FSRS parameters for your learning style

---

## 📄 License

MIT License - Use freely for personal learning

---

## 🙏 Credits

Built with [Claude Code](https://claude.com/code) by Anthropic

Inspired by:
- **SuperMemo** - Spaced repetition pioneer
- **RemNote** - Knowledge graph and bidirectional links
- **Zettelkasten** - Note-taking methodology
- **FSRS** - Modern spaced repetition algorithm

---

## 🌟 System Highlights

### What Makes This System Unique?

1. **Socratic Dialogue**: Unlike traditional flashcards, the system uses AI-powered Socratic questioning to develop deep understanding

2. **Three-Party Architecture**: Innovative consultation pattern reduces token usage by 73% while maintaining expert guidance

3. **Typed Relations**: Semantic relationships between concepts (prerequisite_of, synonym, contrasts_with) enable intelligent review scheduling and knowledge discovery

4. **Automatic Maintenance**: Hooks ensure indexes and links stay synchronized without manual intervention

5. **Multi-Format Support**: Learn from PDFs, EPUBs, PowerPoint, Word, Excel, and Markdown with intelligent chunking

6. **Domain Expertise**: Specialized tutors for Language, Finance, Programming, Medicine, Law, and Science provide tailored learning experiences

7. **Git-Based**: Everything is Markdown - version control, sync across devices, full ownership of your data

8. **FSRS Algorithm**: State-of-the-art spaced repetition 30-50% more efficient than traditional methods

---

Happy learning! 🎓

For questions or issues, please open an issue on GitHub.
