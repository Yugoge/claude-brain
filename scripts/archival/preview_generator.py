#!/usr/bin/env python3
"""
Preview generation module
Generates token-efficient previews for archival confirmation
"""

import time

class PreviewGenerator:
    """Generate previews for concept archival."""

    def generate_preview(self, concepts=None, session_type="learn", rems_reviewed=None):
        """
        Generate token-efficient preview.
        Target: ~600 tokens total.
        """
        start_time = time.time()
        concepts = concepts or []
        rems_reviewed = rems_reviewed or []

        if session_type == "review":
            preview = self.format_review_preview(concepts, rems_reviewed)
        else:
            preview = self.format_learn_preview(concepts)

        gen_time = time.time() - start_time
        print(f"⏱️  Preview generated in {gen_time:.2f}s")

        return preview

    def format_learn_preview(self, concepts):
        """Format preview for learn/ask sessions (ultra-compact)."""
        lines = []
        lines.append("=" * 63)
        lines.append("📝 Concepts to Archive")
        lines.append("=" * 63)
        lines.append("")

        for i, concept in enumerate(concepts, 1):
            # One-line preview (20 tokens each)
            title = concept.get('title', 'Untitled')[:50]
            summary = concept.get('content', '')[:60]
            path = f"{concept.get('domain', 'general')}/concepts/{title.lower().replace(' ', '-')}.md"
            lines.append(f"{i}. {title} → {summary} → {path}")

        lines.append("")
        lines.append(f"Total: {len(concepts)} concepts")

        return '\n'.join(lines)

    def format_review_preview(self, concepts, rems_reviewed):
        """Format three-section preview for review sessions."""
        lines = []
        lines.append("=" * 63)
        lines.append("📊 Review Session Analysis")
        lines.append("=" * 63)
        lines.append("")

        # Section 1: Reviewed Rems
        lines.append(f"✅ Reviewed Rems (FSRS Updated): {len(rems_reviewed)}")
        for i, rem in enumerate(rems_reviewed[:5], 1):
            rem_id = rem.get('id', 'unknown')
            rating = rem.get('rating', '?')
            lines.append(f"  {i}. [[{rem_id}]] - Rating: {rating}")
        if len(rems_reviewed) > 5:
            lines.append(f"  ... and {len(rems_reviewed) - 5} more")
        lines.append("")

        # Section 2: New concepts
        lines.append(f"💡 New Concepts Discovered: {len(concepts)}")
        for i, concept in enumerate(concepts, 1):
            title = concept.get('title', 'Untitled')[:60]
            concept_type = concept.get('type', 'general')
            tokens = concept.get('tokens', 100)
            slug = title.lower().replace(' ', '-')
            lines.append(f"{i}. **{title}** (Type {concept_type})")
            lines.append(f"   File: {slug}.md | Tokens: ~{tokens}")
        lines.append("")

        # Section 3: Summary
        lines.append("=" * 63)
        lines.append("📊 Summary:")
        lines.append(f"  - Reviewed: {len(rems_reviewed)} Rems (FSRS progress saved)")
        lines.append(f"  - Create: {len(concepts)} new Rems")
        lines.append(f"  - Archive: 1 conversation file")

        return '\n'.join(lines)

    def format_compact_preview(self, data, max_tokens=600):
        """
        Generate ultra-compact preview within token budget.
        """
        # Token-aware formatting
        lines = []
        token_count = 0
        max_line_tokens = 20  # Approximate tokens per line

        for item in data:
            if token_count >= max_tokens:
                lines.append("... [truncated for token limit]")
                break

            line = self.format_single_item(item)
            lines.append(line)
            token_count += max_line_tokens

        return '\n'.join(lines)

    def format_single_item(self, item):
        """Format single item for preview."""
        if isinstance(item, dict):
            title = item.get('title', 'Item')[:40]
            value = item.get('value', '')[:20]
            return f"• {title}: {value}"
        return f"• {str(item)[:60]}"