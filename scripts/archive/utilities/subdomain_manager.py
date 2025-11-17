#!/usr/bin/env python3
"""
Subdomain Manager - Central subdomain logic for Rem creation

Provides:
1. Subdomain inference from ISCED + content + tutor hints
2. Next sequence number allocation per subdomain
3. Filename generation in correct format: NNN-subdomain-title.md
"""

import re
import sys
from pathlib import Path
from typing import Optional, List, Tuple

# Subdomain classification rules (synchronized with add-subdomain.py)
SUBDOMAIN_RULES = {
    '0231-language-acquisition': {
        'french': [
            'french', 'verb', 'greeting', 'negation', 'manquer', 'formality',
            'inviting', 'expressing', 'time-expressions', 'tout', 'aller',
            'lorsque', 'adverb', 'adjective', 'pattern', 'avoir-faim',
            'vocabulary-family', 'verbs-high-frequency', 'sentir', 'le-savon',
            'common-mistakes-chinese', 'mistakes-chinese'
        ],
        'english': ['etymology']
    },
    '0611-computer-use': {
        'csharp': ['*']  # All files
    },
    '0412-finance-banking-insurance': {
        'equity-derivatives': [
            'option', 'delta', 'vega', 'theta', 'black-scholes', 'vix',
            'greeks', 'implied-volatility', 'call', 'intrinsic-value',
            'dividend-adjusted', 'black-76-futures', 'pricing-replication',
            'risk-neutral-pricing'
        ],
        'fx-derivatives': [
            'fx-forward', 'fx-options', 'fx-risk', 'fx-delta',
            'covered-interest', 'deliverable-vs-ndo', 'forward-opportunity-cost',
            'forward-covered-interest'
        ],
        'interest-rate': [
            'carry-trade', 'interest-rate-differential', 'nds-payment'
        ],
        'risk-management': [
            'time-scenario', 'plbase', 'var-tail-risk', 'risk-layers',
            'scenario-analysis'
        ],
        'portfolio-management': [
            'sharpe-ratio', 'multi-asset-portfolio', 'asset-allocation'
        ],
        'quantitative-finance': [
            'volatility-as-underlying', 'tenor-vs-horizon', 'npv',
            'marginal-change', 'capital-market-pricing', 'derivatives-market-maturity',
            'credit-derivatives-jump', 'us-exceptionalism'
        ]
    },
    '0311-economics': {
        'development-economics': ['*']  # All files
    }
}


def determine_subdomain_from_filename(file_path: Path, isced: str) -> str:
    """Determine subdomain based on filename and ISCED code (from add-subdomain.py)"""
    if isced not in SUBDOMAIN_RULES:
        return 'unknown'

    rules = SUBDOMAIN_RULES[isced]
    filename_lower = file_path.stem.lower()

    # Remove number prefix for matching
    filename_lower = re.sub(r'^\d{3}-', '', filename_lower)

    for subdomain, keywords in rules.items():
        if keywords == ['*']:
            return subdomain

        for keyword in keywords:
            if keyword in filename_lower:
                return subdomain

    return 'unknown'


class SubdomainManager:
    """Manages subdomain classification and filename generation for Rems"""

    def __init__(self, knowledge_base_path: Path = None):
        """Initialize with knowledge base path"""
        if knowledge_base_path is None:
            knowledge_base_path = Path(__file__).parent.parent.parent / "knowledge-base"
        self.kb_path = knowledge_base_path

    def infer_subdomain(
        self,
        isced: str,
        concept_content: Optional[str] = None,
        tutor_suggestion: Optional[str] = None,
        filename_hint: Optional[str] = None
    ) -> str:
        """
        Infer subdomain from multiple sources (priority order)

        Args:
            isced: ISCED code (e.g., "0412-finance-banking-insurance")
            concept_content: Optional concept content for keyword matching
            tutor_suggestion: Optional subdomain suggested by domain tutor
            filename_hint: Optional filename/slug for pattern matching

        Returns:
            Subdomain string (e.g., "equity-derivatives") or "unknown"
        """
        # Priority 1: Tutor suggestion (most reliable)
        if tutor_suggestion and self._is_valid_subdomain(tutor_suggestion, isced):
            return tutor_suggestion

        # Priority 2: Filename hint (use existing logic)
        if filename_hint:
            # Create a mock Path object
            mock_path = Path(f"{filename_hint}.md")
            subdomain = determine_subdomain_from_filename(mock_path, isced)
            if subdomain != "unknown":
                return subdomain

        # Priority 3: Content keywords (scan for subdomain-specific terms)
        if concept_content:
            subdomain = self._infer_from_content(isced, concept_content)
            if subdomain != "unknown":
                return subdomain

        # Priority 4: Default subdomain for ISCED (if single-subdomain category)
        subdomain = self._get_default_subdomain(isced)
        if subdomain != "unknown":
            return subdomain

        return "unknown"

    def _is_valid_subdomain(self, subdomain: str, isced: str) -> bool:
        """Check if subdomain is valid for given ISCED code"""
        if isced not in SUBDOMAIN_RULES:
            return False
        return subdomain in SUBDOMAIN_RULES[isced]

    def _infer_from_content(self, isced: str, content: str) -> str:
        """Infer subdomain from content keywords"""
        if isced not in SUBDOMAIN_RULES:
            return "unknown"

        content_lower = content.lower()
        rules = SUBDOMAIN_RULES[isced]

        # Score each subdomain by keyword matches
        scores = {}
        for subdomain, keywords in rules.items():
            if keywords == ['*']:
                scores[subdomain] = 1  # Wildcard gets low priority
            else:
                score = sum(1 for kw in keywords if kw in content_lower)
                if score > 0:
                    scores[subdomain] = score

        # Return subdomain with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return "unknown"

    def _get_default_subdomain(self, isced: str) -> str:
        """Get default subdomain for ISCED codes with single subdomain"""
        if isced not in SUBDOMAIN_RULES:
            return "unknown"

        rules = SUBDOMAIN_RULES[isced]

        # If only one subdomain, return it as default
        if len(rules) == 1:
            return list(rules.keys())[0]

        # If multiple subdomains, look for wildcard
        for subdomain, keywords in rules.items():
            if keywords == ['*']:
                return subdomain

        return "unknown"

    def get_next_sequence_number(self, subdomain: str, isced_path: Path) -> str:
        """
        Get next sequence number for subdomain in ISCED directory

        Args:
            subdomain: Subdomain name (e.g., "equity-derivatives")
            isced_path: Full path to ISCED directory

        Returns:
            3-digit sequence number (e.g., "020")
        """
        # Scan directory for files matching subdomain pattern
        pattern = rf'^\d{{3}}-{re.escape(subdomain)}-.*\.md$'

        max_number = 0
        for file_path in isced_path.glob("*.md"):
            if file_path.name in ["index.md"] or "_templates" in str(file_path):
                continue

            match = re.match(r'^(\d{3})-', file_path.name)
            if match:
                number = int(match.group(1))
                # Check if it matches this subdomain
                if re.match(pattern, file_path.name):
                    max_number = max(max_number, number)

        # Next number is max + 1
        next_number = max_number + 1
        return f"{next_number:03d}"

    def generate_filename(
        self,
        sequence_number: str,
        subdomain: str,
        concept_slug: str
    ) -> str:
        """
        Generate filename in correct format: NNN-subdomain-title.md

        Args:
            sequence_number: 3-digit number (e.g., "020")
            subdomain: Subdomain name (e.g., "equity-derivatives")
            concept_slug: Kebab-case concept title (e.g., "theta-decay")

        Returns:
            Filename string (e.g., "020-equity-derivatives-theta-decay.md")
        """
        # Ensure sequence number is 3 digits
        if len(sequence_number) != 3:
            sequence_number = f"{int(sequence_number):03d}"

        # Ensure concept_slug is kebab-case
        concept_slug = self._slugify(concept_slug)

        return f"{sequence_number}-{subdomain}-{concept_slug}.md"

    def _slugify(self, text: str) -> str:
        """Convert text to kebab-case slug"""
        # Remove special characters, convert to lowercase
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        text = re.sub(r'-+', '-', text)
        return text.strip('-')

    def get_isced_path(self, isced: str) -> Optional[Path]:
        """
        Get full path to ISCED directory

        Args:
            isced: ISCED code (e.g., "0412-finance-banking-insurance")

        Returns:
            Full Path object or None if not found
        """
        # ISCED structure: knowledge-base/{broad}/{narrow}/{detailed}/
        # Example: knowledge-base/04-business-administration-and-law/
        #                          041-business-and-administration/
        #                          0412-finance-banking-insurance/

        # Extract codes
        match = re.match(r'^(\d{2})(\d{2})-(.+)$', isced)
        if not match:
            return None

        broad_code = match.group(1)
        narrow_code = broad_code + match.group(2)[0]  # FIX: Extract first digit only (041, not 0412)
        detailed_code = isced

        # Find matching directory structure
        for broad_dir in self.kb_path.glob(f"{broad_code}-*"):
            if not broad_dir.is_dir():
                continue
            for narrow_dir in broad_dir.glob(f"{narrow_code}-*"):
                if not narrow_dir.is_dir():
                    continue
                for detailed_dir in narrow_dir.glob(f"{detailed_code}"):
                    if detailed_dir.is_dir():
                        return detailed_dir

        return None

    def validate_rem_filename(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Rem filename format

        Args:
            filename: Filename to validate (e.g., "020-equity-derivatives-theta.md")

        Returns:
            (is_valid, error_message)
        """
        # Get all valid subdomains first
        all_subdomains = set()
        for isced_subdomains in SUBDOMAIN_RULES.values():
            all_subdomains.update(isced_subdomains.keys())

        # Try to match against each known subdomain
        for subdomain in all_subdomains:
            # Expected format: NNN-subdomain-title.md
            pattern = rf'^(\d{{3}})-{re.escape(subdomain)}-(.+)\.md$'
            match = re.match(pattern, filename)

            if match:
                number, title = match.groups()

                # Check number is 3 digits
                if not number.isdigit() or len(number) != 3:
                    return (False, "Sequence number must be exactly 3 digits")

                # Check title is kebab-case
                if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', title):
                    return (False, "Title must be kebab-case (lowercase with hyphens)")

                return (True, None)

        # No subdomain matched
        return (False, "Invalid format or unknown subdomain (expected: NNN-subdomain-title.md)")

    def get_all_subdomains(self) -> List[Tuple[str, str]]:
        """
        Get all available subdomains with their ISCED codes

        Returns:
            List of (isced, subdomain) tuples
        """
        result = []
        for isced, subdomains in SUBDOMAIN_RULES.items():
            for subdomain in subdomains.keys():
                result.append((isced, subdomain))
        return sorted(result)


def main():
    """CLI interface for testing subdomain manager"""
    import argparse

    parser = argparse.ArgumentParser(description='Subdomain Manager CLI')
    parser.add_argument('action', choices=['infer', 'next-number', 'generate', 'validate', 'list'],
                       help='Action to perform')
    parser.add_argument('--isced', help='ISCED code (e.g., 0412-finance-banking-insurance)')
    parser.add_argument('--subdomain', help='Subdomain name')
    parser.add_argument('--content', help='Content for inference')
    parser.add_argument('--tutor-hint', help='Tutor suggestion')
    parser.add_argument('--slug', help='Concept slug for filename')
    parser.add_argument('--number', help='Sequence number')
    parser.add_argument('--filename', help='Filename to validate')

    args = parser.parse_args()
    manager = SubdomainManager()

    if args.action == 'infer':
        if not args.isced:
            print("Error: --isced required for infer action")
            sys.exit(1)

        subdomain = manager.infer_subdomain(
            isced=args.isced,
            concept_content=args.content,
            tutor_suggestion=args.tutor_hint,
            filename_hint=args.slug
        )
        print(f"Inferred subdomain: {subdomain}")

    elif args.action == 'next-number':
        if not args.isced or not args.subdomain:
            print("Error: --isced and --subdomain required")
            sys.exit(1)

        isced_path = manager.get_isced_path(args.isced)
        if not isced_path:
            # Enhanced error message with debugging info
            match = re.match(r'^(\d{2})(\d{2})-(.+)$', args.isced)
            if match:
                broad_code = match.group(1)
                narrow_code = broad_code + match.group(2)[0]
                print(f"Error: ISCED path not found for {args.isced}")
                print(f"  Expected path pattern: knowledge-base/{broad_code}-*/{narrow_code}-*/{args.isced}/")
                print(f"  Verify directory structure matches ISCED taxonomy")
            else:
                print(f"Error: Invalid ISCED code format: {args.isced}")
                print(f"  Expected format: 0412-finance-banking-insurance")
            sys.exit(1)

        number = manager.get_next_sequence_number(args.subdomain, isced_path)
        print(f"Next sequence number: {number}")

    elif args.action == 'generate':
        if not args.number or not args.subdomain or not args.slug:
            print("Error: --number, --subdomain, and --slug required")
            sys.exit(1)

        filename = manager.generate_filename(args.number, args.subdomain, args.slug)
        print(f"Generated filename: {filename}")

    elif args.action == 'validate':
        if not args.filename:
            print("Error: --filename required")
            sys.exit(1)

        is_valid, error = manager.validate_rem_filename(args.filename)
        if is_valid:
            print(f"✓ Valid: {args.filename}")
        else:
            print(f"✗ Invalid: {error}")
            sys.exit(1)

    elif args.action == 'list':
        print("Available subdomains:")
        for isced, subdomain in manager.get_all_subdomains():
            print(f"  {isced}: {subdomain}")


if __name__ == '__main__':
    main()
