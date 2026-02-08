#!/usr/bin/env python3
"""
Fix Hierarchical Contradictions in Knowledge Graph

This script detects and fixes bidirectional contradictions in typed relations
that violate hierarchical semantics. It applies intelligent resolution logic
for each type of relationship to maintain graph integrity.

Contradiction types handled:
- example_of: Keep specific→general, remove general→specific
- prerequisite_of: Analyze dependencies, keep fundamental→advanced
- extends/specializes/generalizes: Keep specific→general direction
- contrasts_with/antonym: Allow bidirectional (symmetric)
- related_to: Allow bidirectional (symmetric)
- used_in/uses: Context-dependent resolution

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/fix-hierarchical-contradictions.py [options]

Options:
    --dry-run           Preview changes without writing
    --verbose           Enable detailed logging
    --quiet             Minimize output
    --backup-dir DIR    Custom backup directory
    --no-backup         Skip backup creation
    --report FILE       Save detailed report to file
    --auto-approve      Skip confirmation prompts
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import shutil
import time

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR / "knowledge-graph"))
sys.path.insert(0, str(SCRIPT_DIR))

from rebuild_utils import (
    create_backup,
    setup_logging,
    atomic_write_json,
    check_disk_space,
    cleanup_old_backups
)

# Constants
KB_DIR = ROOT / "knowledge-base"
IDX_DIR = KB_DIR / "_index"
BACKLINKS_PATH = IDX_DIR / "backlinks.json"

# Hierarchical relation types (directional, not symmetric)
HIERARCHICAL_RELATIONS = {
    'example_of',        # specific → general
    'prerequisite_of',   # fundamental → advanced
    'extends',          # specific → general
    'specializes',      # specific → general
    'generalizes',      # general → specific
    'part_of',          # part → whole
    'has_part',         # whole → part
    'member_of',        # member → group
    'cause_of',         # cause → effect
    'caused_by',        # effect → cause
    'defines',          # definition → concept
    'applies_to',       # rule → context
    'has_subtype',      # general → specific
    'has_prerequisite', # advanced → fundamental
}

# Symmetric relation types (bidirectional allowed)
SYMMETRIC_RELATIONS = {
    'contrasts_with',
    'antonym',
    'related_to',
    'analogous_to',
    'complements',
    'derivationally_related',
}

# Context-dependent relation types
CONTEXT_RELATIONS = {
    'used_in',          # Can be bidirectional in some contexts
    'uses',             # Can be bidirectional in some contexts  
    'used_by',          # Can be bidirectional in some contexts
    'supported_by',     # Can be bidirectional in some contexts
    'provides_evidence_for',  # Usually unidirectional
}

# Inverse relation mappings
INVERSE_RELATIONS = {
    'prerequisite_of': 'has_prerequisite',
    'has_prerequisite': 'prerequisite_of',
    'extends': 'generalizes',
    'generalizes': 'extends',
    'specializes': 'has_subtype',
    'has_subtype': 'specializes',
    'part_of': 'has_part',
    'has_part': 'part_of',
    'cause_of': 'caused_by',
    'caused_by': 'cause_of',
}


@dataclass
class Contradiction:
    """Represents a bidirectional contradiction"""
    rem_a: str
    rem_b: str
    relation_type: str
    resolution: Optional[str] = None
    rationale: Optional[str] = None
    
    @property
    def pair_key(self) -> Tuple[str, str]:
        """Get sorted pair key for deduplication"""
        return tuple(sorted([self.rem_a, self.rem_b]))


@dataclass
class ResolutionStats:
    """Statistics for resolution process"""
    total_contradictions: int = 0
    resolved: int = 0
    skipped: int = 0
    failed: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    removed_links: List[Dict] = field(default_factory=list)
    added_links: List[Dict] = field(default_factory=list)


class HierarchicalContradictionFixer:
    """Main class for fixing hierarchical contradictions"""
    
    def __init__(self, logger: logging.Logger, dry_run: bool = False):
        self.logger = logger
        self.dry_run = dry_run
        self.backlinks_data = None
        self.contradictions = []
        self.stats = ResolutionStats()
        
    def load_backlinks(self) -> bool:
        """Load backlinks.json file"""
        try:
            with open(BACKLINKS_PATH, 'r', encoding='utf-8') as f:
                self.backlinks_data = json.load(f)
            self.logger.info(f"Loaded backlinks with {len(self.backlinks_data['links'])} concepts")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load backlinks: {e}")
            return False
    
    def detect_contradictions(self) -> List[Contradiction]:
        """Detect all bidirectional contradictions"""
        contradictions = []
        seen_pairs = set()
        
        for rem_id, rem_data in self.backlinks_data['links'].items():
            for typed_link in rem_data.get('typed_links_to', []):
                to_id = typed_link['to']
                rel_type = typed_link['type']
                
                # Skip if we've already processed this pair
                pair_key = tuple(sorted([rem_id, to_id]))
                if (pair_key, rel_type) in seen_pairs:
                    continue
                
                # Check if reverse relation exists
                if to_id in self.backlinks_data['links']:
                    reverse_data = self.backlinks_data['links'][to_id]
                    for reverse_link in reverse_data.get('typed_links_to', []):
                        if reverse_link['to'] == rem_id and reverse_link['type'] == rel_type:
                            # Found bidirectional relation of same type
                            contradiction = Contradiction(
                                rem_a=rem_id,
                                rem_b=to_id,
                                relation_type=rel_type
                            )
                            contradictions.append(contradiction)
                            seen_pairs.add((pair_key, rel_type))
                            break
        
        self.contradictions = contradictions
        self.stats.total_contradictions = len(contradictions)
        
        # Count by type
        for c in contradictions:
            self.stats.by_type[c.relation_type] = self.stats.by_type.get(c.relation_type, 0) + 1
        
        return contradictions
    
    def get_rem_info(self, rem_id: str) -> Dict:
        """Get concept information for a Rem"""
        if rem_id in self.backlinks_data.get('concepts', {}):
            return self.backlinks_data['concepts'][rem_id]
        return {'title': rem_id, 'file': f'{rem_id}.md'}
    
    def determine_generality(self, rem_a: str, rem_b: str) -> str:
        """
        Determine which concept is more general based on heuristics.
        Returns 'a' if rem_a is more general, 'b' if rem_b is more general,
        or 'unknown' if cannot determine.
        """
        # Heuristic 1: Check concept titles for general indicators
        info_a = self.get_rem_info(rem_a)
        info_b = self.get_rem_info(rem_b)
        
        title_a = info_a.get('title', rem_a).lower()
        title_b = info_b.get('title', rem_b).lower()
        
        # General concept indicators
        general_indicators = ['general', 'concept', 'theory', 'principle', 
                             'framework', 'system', 'model', 'paradigm',
                             'overview', 'introduction', 'fundamental']
        
        # Specific concept indicators  
        specific_indicators = ['example', 'instance', 'specific', 'particular',
                              'implementation', 'application', 'case', 'sample',
                              'concrete', 'detailed']
        
        # Etymology is always more general than specific vocabulary
        if 'etymology' in rem_a and 'vocabulary' in rem_b:
            return 'a'
        elif 'etymology' in rem_b and 'vocabulary' in rem_a:
            return 'b'
        
        # Count indicators
        a_general = sum(1 for ind in general_indicators if ind in title_a)
        a_specific = sum(1 for ind in specific_indicators if ind in title_a)
        b_general = sum(1 for ind in general_indicators if ind in title_b)
        b_specific = sum(1 for ind in specific_indicators if ind in title_b)
        
        # Heuristic 2: Check file paths (deeper paths often more specific)
        path_a = info_a.get('file', '')
        path_b = info_b.get('file', '')
        
        depth_a = path_a.count('/')
        depth_b = path_b.count('/')
        
        # Combine heuristics
        if a_general > b_general and a_specific <= b_specific:
            return 'a'
        elif b_general > a_general and b_specific <= a_specific:
            return 'b'
        elif depth_a < depth_b:
            return 'a'  # Shallower path = more general
        elif depth_b < depth_a:
            return 'b'
        
        # Heuristic 3: Check number of incoming links (more links = more general)
        links_to_a = len(self.backlinks_data['links'].get(rem_a, {}).get('linked_from', []))
        links_to_b = len(self.backlinks_data['links'].get(rem_b, {}).get('linked_from', []))
        
        if links_to_a > links_to_b * 1.5:  # Significant difference
            return 'a'
        elif links_to_b > links_to_a * 1.5:
            return 'b'
        
        return 'unknown'
    
    def analyze_prerequisites(self, rem_a: str, rem_b: str) -> str:
        """
        Analyze which concept is more fundamental (prerequisite).
        Returns 'a' if rem_a is prerequisite, 'b' if rem_b is prerequisite,
        or 'unknown' if cannot determine.
        """
        # Check for explicit ordering indicators
        info_a = self.get_rem_info(rem_a)
        info_b = self.get_rem_info(rem_b)
        
        title_a = info_a.get('title', rem_a).lower()
        title_b = info_b.get('title', rem_b).lower()
        
        # Fundamental concepts
        fundamental = ['basic', 'fundamental', 'introduction', 'elementary',
                      'foundation', 'prerequisite', 'required', 'essential']
        
        # Advanced concepts
        advanced = ['advanced', 'complex', 'sophisticated', 'specialized',
                   'expert', 'optimization', 'extension', 'enhancement']
        
        a_fundamental = sum(1 for ind in fundamental if ind in title_a)
        a_advanced = sum(1 for ind in advanced if ind in title_a)
        b_fundamental = sum(1 for ind in fundamental if ind in title_b)
        b_advanced = sum(1 for ind in advanced if ind in title_b)
        
        if a_fundamental > b_fundamental and a_advanced <= b_advanced:
            return 'a'
        elif b_fundamental > a_fundamental and b_advanced <= a_advanced:
            return 'b'
        
        # Check for numbered sequences (lower numbers = more fundamental)
        import re
        num_a = re.findall(r'\d+', rem_a)
        num_b = re.findall(r'\d+', rem_b)
        
        if num_a and num_b:
            try:
                if int(num_a[0]) < int(num_b[0]):
                    return 'a'
                elif int(num_b[0]) < int(num_a[0]):
                    return 'b'
            except:
                pass
        
        # Domain-specific rules
        if 'variable-scope' in rem_a and 'inheritance' in rem_b:
            return 'a'  # Scope is more fundamental than inheritance
        elif 'inheritance' in rem_a and 'variable-scope' in rem_b:
            return 'b'
        
        return 'unknown'
    
    def resolve_contradiction(self, contradiction: Contradiction) -> None:
        """Resolve a single contradiction based on relation type"""
        rel_type = contradiction.relation_type
        rem_a = contradiction.rem_a
        rem_b = contradiction.rem_b
        
        # Skip symmetric relations (allowed to be bidirectional)
        if rel_type in SYMMETRIC_RELATIONS:
            contradiction.resolution = 'keep_both'
            contradiction.rationale = f'{rel_type} is a symmetric relation'
            self.stats.skipped += 1
            return
        
        # Handle hierarchical relations
        if rel_type == 'example_of':
            # Keep specific→general, remove general→specific
            generality = self.determine_generality(rem_a, rem_b)
            if generality == 'a':
                # rem_a is more general, keep b→a
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
                contradiction.rationale = f'{rem_b} is specific example of general concept {rem_a}'
            elif generality == 'b':
                # rem_b is more general, keep a→b
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
                contradiction.rationale = f'{rem_a} is specific example of general concept {rem_b}'
            else:
                # Can't determine, keep the one with more supporting evidence
                contradiction.resolution = 'keep_both'
                contradiction.rationale = 'Unable to determine generality hierarchy'
                
        elif rel_type == 'prerequisite_of':
            # Keep fundamental→advanced, remove advanced→fundamental
            prerequisite = self.analyze_prerequisites(rem_a, rem_b)
            if prerequisite == 'a':
                # rem_a is prerequisite, keep a→b
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
                contradiction.rationale = f'{rem_a} is fundamental prerequisite for {rem_b}'
            elif prerequisite == 'b':
                # rem_b is prerequisite, keep b→a
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
                contradiction.rationale = f'{rem_b} is fundamental prerequisite for {rem_a}'
            else:
                # Check for cycles, prefer breaking the cycle
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
                contradiction.rationale = 'Breaking potential prerequisite cycle'
                
        elif rel_type in ['extends', 'specializes']:
            # Keep specific→general
            generality = self.determine_generality(rem_a, rem_b)
            if generality == 'a':
                # rem_a is more general, keep b extends a
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
                contradiction.rationale = f'{rem_b} extends/specializes general {rem_a}'
            elif generality == 'b':
                # rem_b is more general, keep a extends b
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
                contradiction.rationale = f'{rem_a} extends/specializes general {rem_b}'
            else:
                contradiction.resolution = 'keep_both'
                contradiction.rationale = 'Unable to determine specialization hierarchy'
                
        elif rel_type == 'generalizes':
            # Keep general→specific (opposite of extends)
            generality = self.determine_generality(rem_a, rem_b)
            if generality == 'a':
                # rem_a is more general, keep a generalizes b
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
                contradiction.rationale = f'{rem_a} generalizes specific {rem_b}'
            elif generality == 'b':
                # rem_b is more general, keep b generalizes a
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
                contradiction.rationale = f'{rem_b} generalizes specific {rem_a}'
            else:
                contradiction.resolution = 'keep_both'
                contradiction.rationale = 'Unable to determine generalization hierarchy'
                
        elif rel_type in CONTEXT_RELATIONS:
            # Context-dependent relations - check domain context
            # For now, allow bidirectional for these
            contradiction.resolution = 'keep_both'
            contradiction.rationale = f'{rel_type} can be bidirectional in certain contexts'
            self.stats.skipped += 1
            
        else:
            # Unknown relation type - be conservative
            contradiction.resolution = 'keep_both'
            contradiction.rationale = f'Unknown relation type: {rel_type}'
            self.stats.skipped += 1
    
    def apply_resolutions(self) -> None:
        """Apply all resolutions to the backlinks data"""
        for contradiction in self.contradictions:
            if not contradiction.resolution or contradiction.resolution == 'keep_both':
                continue
            
            if contradiction.resolution.startswith('remove_'):
                # Parse which link to remove
                parts = contradiction.resolution.replace('remove_', '').split('_to_')
                if len(parts) == 2:
                    from_rem = parts[0]
                    to_rem = parts[1]
                    
                    # Remove the specified link
                    if from_rem in self.backlinks_data['links']:
                        rem_data = self.backlinks_data['links'][from_rem]
                        
                        # Remove from typed_links_to
                        new_typed_links = [
                            link for link in rem_data.get('typed_links_to', [])
                            if not (link['to'] == to_rem and link['type'] == contradiction.relation_type)
                        ]
                        
                        if len(new_typed_links) < len(rem_data.get('typed_links_to', [])):
                            rem_data['typed_links_to'] = new_typed_links
                            self.stats.removed_links.append({
                                'from': from_rem,
                                'to': to_rem,
                                'type': contradiction.relation_type
                            })
                            self.stats.resolved += 1
                            self.logger.debug(f"Removed {from_rem} → {to_rem} ({contradiction.relation_type})")
                    
                    # Also remove from reverse typed_linked_from
                    if to_rem in self.backlinks_data['links']:
                        rem_data = self.backlinks_data['links'][to_rem]
                        new_typed_from = [
                            link for link in rem_data.get('typed_linked_from', [])
                            if not (link['from'] == from_rem and link['type'] == contradiction.relation_type)
                        ]
                        rem_data['typed_linked_from'] = new_typed_from
    
    def validate_fixes(self) -> bool:
        """Validate that fixes don't break graph integrity"""
        valid = True
        
        # Re-detect contradictions
        remaining = []
        for rem_id, rem_data in self.backlinks_data['links'].items():
            for typed_link in rem_data.get('typed_links_to', []):
                to_id = typed_link['to']
                rel_type = typed_link['type']
                
                # Skip symmetric relations
                if rel_type in SYMMETRIC_RELATIONS or rel_type in CONTEXT_RELATIONS:
                    continue
                    
                # Check if reverse still exists
                if to_id in self.backlinks_data['links']:
                    reverse_data = self.backlinks_data['links'][to_id]
                    for reverse_link in reverse_data.get('typed_links_to', []):
                        if reverse_link['to'] == rem_id and reverse_link['type'] == rel_type:
                            remaining.append((rem_id, to_id, rel_type))
                            valid = False
        
        if remaining:
            self.logger.warning(f"Found {len(remaining)} remaining contradictions after fixes:")
            for rem_a, rem_b, rel_type in remaining[:5]:
                self.logger.warning(f"  - {rem_a} ↔ {rem_b} ({rel_type})")
        else:
            self.logger.info("✅ All hierarchical contradictions resolved successfully")
        
        return valid
    
    def generate_report(self) -> str:
        """Generate detailed report of fixes"""
        report = []
        report.append("=" * 80)
        report.append("HIERARCHICAL CONTRADICTION FIX REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Total contradictions found: {self.stats.total_contradictions}")
        report.append(f"Resolved: {self.stats.resolved}")
        report.append(f"Skipped (symmetric): {self.stats.skipped}")
        report.append(f"Failed: {self.stats.failed}")
        report.append("")
        
        # By type breakdown
        report.append("CONTRADICTIONS BY TYPE")
        report.append("-" * 40)
        for rel_type, count in sorted(self.stats.by_type.items(), key=lambda x: -x[1]):
            status = "symmetric" if rel_type in SYMMETRIC_RELATIONS else "hierarchical"
            report.append(f"  {rel_type}: {count} ({status})")
        report.append("")
        
        # Detailed resolutions
        report.append("DETAILED RESOLUTIONS")
        report.append("-" * 40)
        
        # Group by relation type
        by_type = defaultdict(list)
        for c in self.contradictions:
            by_type[c.relation_type].append(c)
        
        for rel_type in sorted(by_type.keys()):
            contradictions = by_type[rel_type]
            report.append(f"\n{rel_type.upper()} ({len(contradictions)} contradictions)")
            report.append("=" * 60)
            
            for i, c in enumerate(contradictions[:10], 1):
                info_a = self.get_rem_info(c.rem_a)
                info_b = self.get_rem_info(c.rem_b)
                
                report.append(f"\n{i}. {info_a['title']} ↔ {info_b['title']}")
                report.append(f"   IDs: {c.rem_a} ↔ {c.rem_b}")
                report.append(f"   Resolution: {c.resolution or 'pending'}")
                report.append(f"   Rationale: {c.rationale or 'none'}")
            
            if len(contradictions) > 10:
                report.append(f"\n   ... and {len(contradictions) - 10} more")
        
        # Removed links
        if self.stats.removed_links:
            report.append("\n\nREMOVED LINKS")
            report.append("-" * 40)
            for link in self.stats.removed_links[:20]:
                report.append(f"  - {link['from']} → {link['to']} ({link['type']})")
            if len(self.stats.removed_links) > 20:
                report.append(f"  ... and {len(self.stats.removed_links) - 20} more")
        
        report.append("\n" + "=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run(self, auto_approve: bool = False) -> bool:
        """Main execution flow"""
        # Load backlinks
        if not self.load_backlinks():
            return False
        
        # Detect contradictions
        self.logger.info("Detecting bidirectional contradictions...")
        contradictions = self.detect_contradictions()
        
        self.logger.info(f"Found {len(contradictions)} bidirectional contradictions")
        for rel_type, count in sorted(self.stats.by_type.items(), key=lambda x: -x[1]):
            self.logger.info(f"  {rel_type}: {count}")
        
        # Resolve each contradiction
        self.logger.info("Analyzing and resolving contradictions...")
        with_progress = len(contradictions) > 10
        
        for i, contradiction in enumerate(contradictions):
            self.resolve_contradiction(contradiction)
            if with_progress and (i + 1) % 10 == 0:
                self.logger.info(f"  Processed {i + 1}/{len(contradictions)} contradictions...")
        
        # Show preview of changes
        self.logger.info(f"\nProposed changes:")
        self.logger.info(f"  - Remove {len(self.stats.removed_links)} incorrect links")
        self.logger.info(f"  - Keep {self.stats.skipped} symmetric bidirectional relations")
        
        # Get user confirmation if not auto-approve and not dry-run
        if not self.dry_run and not auto_approve:
            response = input("\nProceed with fixes? (y/N): ")
            if response.lower() != 'y':
                self.logger.info("Aborted by user")
                return False
        
        # Apply resolutions
        if not self.dry_run:
            self.logger.info("Applying resolutions...")
            self.apply_resolutions()
            
            # Validate fixes
            self.logger.info("Validating fixes...")
            self.validate_fixes()
            
            # Update metadata
            self.backlinks_data['metadata']['last_updated'] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.backlinks_data['metadata']['contradictions_fixed'] = len(self.stats.removed_links)
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Fix hierarchical contradictions in knowledge graph',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable DEBUG level logging')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimize output (warnings only)')
    parser.add_argument('--backup-dir', type=str,
                        help='Custom backup directory')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip backup creation')
    parser.add_argument('--report', type=str,
                        help='Save detailed report to file')
    parser.add_argument('--auto-approve', action='store_true',
                        help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging('fix-contradictions', verbose=args.verbose, quiet=args.quiet)
    
    try:
        # Check disk space
        if not check_disk_space(BACKLINKS_PATH, required_mb=10):
            logger.error("Insufficient disk space")
            return 3
        
        # Create fixer instance
        fixer = HierarchicalContradictionFixer(logger, dry_run=args.dry_run)
        
        # Run fixes
        success = fixer.run(auto_approve=args.auto_approve)
        
        if not success:
            return 1
        
        # Generate and save report
        report = fixer.generate_report()
        
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report)
            logger.info(f"Report saved to: {report_path}")
        elif args.verbose:
            print("\n" + report)
        
        # Save changes if not dry run
        if not args.dry_run:
            # Create backup
            if not args.no_backup and BACKLINKS_PATH.exists():
                backup_dir = Path(args.backup_dir) if args.backup_dir else None
                backup_path = create_backup(BACKLINKS_PATH, backup_dir)
                if backup_path:
                    logger.info(f"Created backup: {backup_path}")
            
            # Write updated backlinks
            atomic_write_json(BACKLINKS_PATH, fixer.backlinks_data)
            logger.info(f"✅ Fixes applied successfully to {BACKLINKS_PATH}")
            logger.info(f"   Removed {len(fixer.stats.removed_links)} contradictory links")
            logger.info(f"   Preserved {fixer.stats.skipped} symmetric relations")
        else:
            logger.info("DRY RUN completed - no changes made")
        
        return 0
        
    except KeyboardInterrupt:
        logger.error("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
