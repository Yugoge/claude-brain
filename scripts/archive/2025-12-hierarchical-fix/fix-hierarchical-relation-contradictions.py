#!/usr/bin/env python3
"""
Fix Hierarchical Contradictions in Knowledge Graph - Version 2

Enhanced version with more aggressive resolution strategies and better heuristics.
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
import re

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR / "knowledge-graph"))
sys.path.insert(0, str(SCRIPT_DIR))

from rebuild_utils import (
    create_backup,
    setup_logging,
    atomic_write_json,
    check_disk_space
)

# Constants
KB_DIR = ROOT / "knowledge-base"
IDX_DIR = KB_DIR / "_index"
BACKLINKS_PATH = IDX_DIR / "backlinks.json"

# Hierarchical relation types that should NOT be bidirectional
STRICT_HIERARCHICAL = {
    'example_of',        # specific → general (NEVER bidirectional)
    'prerequisite_of',   # fundamental → advanced (NEVER bidirectional)
    'extends',          # specific → general (NEVER bidirectional)
    'specializes',      # specific → general (NEVER bidirectional)
    'generalizes',      # general → specific (NEVER bidirectional)
}

# Symmetric relations (bidirectional is OK)
SYMMETRIC_RELATIONS = {
    'contrasts_with',
    'antonym', 
    'related_to',
    'analogous_to',
    'complements',
    'derivationally_related',
}

# Context-dependent (needs analysis)
CONTEXT_DEPENDENT = {
    'used_in',
    'uses',
    'used_by',
    'member_of',
    'applies_to',
    'supported_by',
}


@dataclass
class Contradiction:
    """Represents a bidirectional contradiction"""
    rem_a: str
    rem_b: str
    relation_type: str
    resolution: Optional[str] = None
    rationale: Optional[str] = None


class EnhancedContradictionFixer:
    """Enhanced fixer with better resolution strategies"""
    
    def __init__(self, logger: logging.Logger, dry_run: bool = False):
        self.logger = logger
        self.dry_run = dry_run
        self.backlinks_data = None
        self.contradictions = []
        self.removed_links = []
        
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
        return contradictions
    
    def analyze_example_of(self, rem_a: str, rem_b: str) -> Tuple[str, str]:
        """
        Determine which is example and which is general concept.
        Returns (example_rem, general_rem)
        """
        # Strong indicators for etymology being general
        if 'etymology' in rem_a and 'vocabulary' in rem_b:
            return (rem_b, rem_a)  # vocabulary is example of etymology
        elif 'etymology' in rem_b and 'vocabulary' in rem_a:
            return (rem_a, rem_b)  # vocabulary is example of etymology
            
        # Check titles
        info_a = self.backlinks_data.get('concepts', {}).get(rem_a, {})
        info_b = self.backlinks_data.get('concepts', {}).get(rem_b, {})
        
        title_a = info_a.get('title', rem_a).lower()
        title_b = info_b.get('title', rem_b).lower()
        
        # Specific indicators
        if any(word in title_a for word in ['specific', 'example', 'instance', 'case']):
            return (rem_a, rem_b)
        if any(word in title_b for word in ['specific', 'example', 'instance', 'case']):
            return (rem_b, rem_a)
            
        # General indicators
        if any(word in title_a for word in ['general', 'concept', 'theory', 'principle']):
            return (rem_b, rem_a)
        if any(word in title_b for word in ['general', 'concept', 'theory', 'principle']):
            return (rem_a, rem_b)
            
        # Default: use alphabetical order for consistency
        return (rem_a, rem_b) if rem_a < rem_b else (rem_b, rem_a)
    
    def analyze_prerequisite(self, rem_a: str, rem_b: str) -> Tuple[str, str]:
        """
        Determine prerequisite order.
        Returns (prerequisite_rem, advanced_rem)
        """
        # Domain-specific rules
        if 'variable-scope' in rem_a and 'inheritance' in rem_b:
            return (rem_a, rem_b)  # scope is prerequisite for inheritance
        elif 'inheritance' in rem_a and 'variable-scope' in rem_b:
            return (rem_b, rem_a)
            
        if 'basic' in rem_a or 'fundamental' in rem_a:
            return (rem_a, rem_b)
        if 'basic' in rem_b or 'fundamental' in rem_b:
            return (rem_b, rem_a)
            
        if 'advanced' in rem_a or 'complex' in rem_a:
            return (rem_b, rem_a)
        if 'advanced' in rem_b or 'complex' in rem_b:
            return (rem_a, rem_b)
            
        # Check for numbered sequences
        num_a = re.findall(r'\d+', rem_a)
        num_b = re.findall(r'\d+', rem_b)
        
        if num_a and num_b:
            try:
                if int(num_a[0]) < int(num_b[0]):
                    return (rem_a, rem_b)
                elif int(num_b[0]) < int(num_a[0]):
                    return (rem_b, rem_a)
            except:
                pass
                
        # Default: use alphabetical order
        return (rem_a, rem_b) if rem_a < rem_b else (rem_b, rem_a)
    
    def analyze_extends(self, rem_a: str, rem_b: str) -> Tuple[str, str]:
        """
        Determine extends relationship.
        Returns (specific_rem, general_rem)
        """
        # Black-Scholes is general, others extend it
        if 'black-scholes' in rem_a and 'black-scholes' not in rem_b:
            if 'vix' in rem_b or 'dividend' in rem_b:
                return (rem_b, rem_a)  # VIX/dividend extends Black-Scholes
        elif 'black-scholes' in rem_b and 'black-scholes' not in rem_a:
            if 'vix' in rem_a or 'dividend' in rem_a:
                return (rem_a, rem_b)
                
        # SABR extends Black-Scholes
        if 'sabr' in rem_a and 'black-scholes' in rem_b:
            return (rem_a, rem_b)
        elif 'sabr' in rem_b and 'black-scholes' in rem_a:
            return (rem_b, rem_a)
            
        # Jump diffusion extends Black-Scholes
        if 'jump-diffusion' in rem_a and 'black-scholes' in rem_b:
            return (rem_a, rem_b)
        elif 'jump-diffusion' in rem_b and 'black-scholes' in rem_a:
            return (rem_b, rem_a)
            
        # Default
        return (rem_a, rem_b) if rem_a > rem_b else (rem_b, rem_a)
    
    def resolve_contradiction(self, contradiction: Contradiction) -> None:
        """Resolve a single contradiction"""
        rel_type = contradiction.relation_type
        rem_a = contradiction.rem_a
        rem_b = contradiction.rem_b
        
        # Skip symmetric relations
        if rel_type in SYMMETRIC_RELATIONS:
            contradiction.resolution = 'keep_both'
            contradiction.rationale = f'{rel_type} is symmetric'
            return
            
        # Handle strict hierarchical relations
        if rel_type == 'example_of':
            example, general = self.analyze_example_of(rem_a, rem_b)
            # Keep example→general, remove general→example
            if example == rem_a:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'{example} is example of {general}'
            
        elif rel_type == 'prerequisite_of':
            prereq, advanced = self.analyze_prerequisite(rem_a, rem_b)
            # Keep prereq→advanced, remove advanced→prereq
            if prereq == rem_a:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'{prereq} is prerequisite for {advanced}'
            
        elif rel_type == 'extends':
            specific, general = self.analyze_extends(rem_a, rem_b)
            # Keep specific→general, remove general→specific
            if specific == rem_a:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'{specific} extends {general}'
            
        elif rel_type == 'specializes':
            # Same as extends
            specific, general = self.analyze_extends(rem_a, rem_b)
            if specific == rem_a:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'{specific} specializes {general}'
            
        elif rel_type == 'generalizes':
            # Opposite of extends
            specific, general = self.analyze_extends(rem_a, rem_b)
            if general == rem_a:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'{general} generalizes {specific}'
            
        elif rel_type in CONTEXT_DEPENDENT:
            # For context-dependent, remove one direction arbitrarily but consistently
            # Keep alphabetically first→second
            if rem_a < rem_b:
                contradiction.resolution = f'remove_{rem_b}_to_{rem_a}'
            else:
                contradiction.resolution = f'remove_{rem_a}_to_{rem_b}'
            contradiction.rationale = f'Removed reverse {rel_type} to avoid bidirectional'
        else:
            # Unknown - be conservative
            contradiction.resolution = 'keep_both'
            contradiction.rationale = 'Unknown relation type'
    
    def apply_resolutions(self) -> int:
        """Apply all resolutions and return count of removed links"""
        removed_count = 0
        
        for contradiction in self.contradictions:
            if not contradiction.resolution or contradiction.resolution == 'keep_both':
                continue
                
            if contradiction.resolution.startswith('remove_'):
                parts = contradiction.resolution.replace('remove_', '').split('_to_')
                if len(parts) == 2:
                    from_rem = parts[0]
                    to_rem = parts[1]
                    
                    # Remove from typed_links_to
                    if from_rem in self.backlinks_data['links']:
                        rem_data = self.backlinks_data['links'][from_rem]
                        original_count = len(rem_data.get('typed_links_to', []))
                        
                        rem_data['typed_links_to'] = [
                            link for link in rem_data.get('typed_links_to', [])
                            if not (link['to'] == to_rem and link['type'] == contradiction.relation_type)
                        ]
                        
                        if len(rem_data['typed_links_to']) < original_count:
                            removed_count += 1
                            self.removed_links.append({
                                'from': from_rem,
                                'to': to_rem,
                                'type': contradiction.relation_type,
                                'rationale': contradiction.rationale
                            })
                    
                    # Remove from typed_linked_from
                    if to_rem in self.backlinks_data['links']:
                        rem_data = self.backlinks_data['links'][to_rem]
                        rem_data['typed_linked_from'] = [
                            link for link in rem_data.get('typed_linked_from', [])
                            if not (link['from'] == from_rem and link['type'] == contradiction.relation_type)
                        ]
        
        return removed_count
    
    def run(self) -> bool:
        """Main execution"""
        if not self.load_backlinks():
            return False
            
        # Detect contradictions
        self.logger.info("Detecting contradictions...")
        contradictions = self.detect_contradictions()
        
        # Count by type
        by_type = defaultdict(int)
        for c in contradictions:
            by_type[c.relation_type] += 1
            
        self.logger.info(f"Found {len(contradictions)} bidirectional contradictions:")
        for rel_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            self.logger.info(f"  {rel_type}: {count}")
            
        # Resolve contradictions
        self.logger.info("Resolving contradictions...")
        for c in contradictions:
            self.resolve_contradiction(c)
            
        # Count resolutions
        to_remove = sum(1 for c in contradictions if c.resolution and c.resolution.startswith('remove_'))
        to_keep = sum(1 for c in contradictions if c.resolution == 'keep_both')
        
        self.logger.info(f"\nResolution summary:")
        self.logger.info(f"  Will remove: {to_remove} links")
        self.logger.info(f"  Will keep: {to_keep} bidirectional (symmetric)")
        
        if not self.dry_run:
            # Apply resolutions
            removed = self.apply_resolutions()
            self.logger.info(f"Removed {removed} contradictory links")
            
            # Update metadata
            self.backlinks_data['metadata']['last_updated'] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.backlinks_data['metadata']['contradictions_fixed'] = removed
            
        # Show sample of removed links
        if self.removed_links:
            self.logger.info("\nSample of removed links:")
            for link in self.removed_links[:10]:
                self.logger.info(f"  {link['from']} → {link['to']} ({link['type']})")
                self.logger.info(f"    Reason: {link['rationale']}")
                
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Fix hierarchical contradictions - Version 2')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    
    args = parser.parse_args()
    
    logger = setup_logging('fix-contradictions-v2', verbose=args.verbose)
    
    try:
        fixer = EnhancedContradictionFixer(logger, dry_run=args.dry_run)
        
        if not fixer.run():
            return 1
            
        if not args.dry_run:
            # Backup
            if not args.no_backup:
                backup = create_backup(BACKLINKS_PATH)
                logger.info(f"Created backup: {backup}")
                
            # Save
            atomic_write_json(BACKLINKS_PATH, fixer.backlinks_data)
            logger.info(f"✅ Saved fixes to {BACKLINKS_PATH}")
        else:
            logger.info("DRY RUN - no changes made")
            
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
