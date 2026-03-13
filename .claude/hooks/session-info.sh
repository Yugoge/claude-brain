#!/bin/bash
# s-info.sh — SessionStart: display environment info + tool quick reference

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Claude Code Session Started"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dir: $(pwd)"

# Git info
if [ -d .git ]; then
    branch=$(git branch --show-current 2>/dev/null || echo "detached")
    modified=$(git status --porcelain 2>/dev/null | wc -l)
    if [ "$modified" -gt 0 ]; then
        echo "  Git: $branch  (! $modified uncommitted files)"
    else
        echo "  Git: $branch  (clean)"
    fi
fi

# Project metadata
[ -f .claude/CLAUDE.md ] && echo "  CLAUDE.md: project instructions loaded"
cmd_count=$(find .claude/commands -name "*.md" 2>/dev/null | wc -l)
agent_count=$(find .claude/agents -name "*.md" 2>/dev/null | wc -l)
[ "$cmd_count" -gt 0 ] && echo "  Commands:  $cmd_count available"
[ "$agent_count" -gt 0 ] && echo "  Agents:    $agent_count available"

echo ""
echo "  TOOL QUICK REFERENCE"
echo "  ─────────────────────────────────────────────────────────────"
echo "  FILE    Read(file_path)"
echo "          Write(file_path, content)          [Read first!]"
echo "          Edit(file_path, old_string, new_string, replace_all?)"
echo "          Glob(pattern, path?)    Grep(pattern, path, include?)"
echo "          Bash(command, timeout?, description?)"
echo ""
echo "  TASKS   TodoWrite(todos=[{content, activeForm, status}])"
echo "            status: pending | in_progress | completed"
echo "            ONE in_progress at a time. ONE step completed per call."
echo "          Agent(description, prompt, subagent_type?, model?, isolation?)"
echo "          TaskOutput(task_id, block?, timeout?)  TaskStop(task_id)"
echo ""
echo "  SEARCH  WebSearch(query, allowed_domains?, blocked_domains?)"
echo "          WebFetch(url, prompt)"
echo "          ToolSearch(query, max_results?)    [use before unknown tools]"
echo ""
echo "  BROWSER navigate(url) -> snapshot() -> click(ref, element)"
echo "          type(ref, text)  fill_form(fields)  wait_for(text?)"
echo "          All: mcp__playwright__browser_<action>"
echo ""
echo "  HAPPY   mcp__happy__change_title(title)   [call at start of every chat]"
echo "  ─────────────────────────────────────────────────────────────"
echo ""
