#!/usr/bin/env python3
"""
Main orchestrator for the /save command
Coordinates all archival operations
"""

import sys
import time
from session_detector import SessionDetector
from concept_extractor import ConceptExtractor
from preview_generator import PreviewGenerator
from question_classifier import QuestionClassifier

def main():
    """Main entry point for /save command."""
    perf_start = time.time()

    # Parse arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if args and args[0] == '--all':
        topic = 'all'
    elif args:
        topic = ' '.join(args)
    else:
        topic = 'recent'

    print(f"📝 Saving session with topic: {topic}")

    # Step 1: Detect session type (with confidence scoring)
    detector = SessionDetector()
    session_type, rems_reviewed, confidence = detector.detect_session_type()
    print(f"   Session type: {session_type} (confidence: {confidence:.0%})")
    print(f"   Rems reviewed: {len(rems_reviewed)}")

    # Step 2: Check if there's content to extract
    extractor = ConceptExtractor()
    if not extractor.should_extract():
        print("⏭️  No content to extract, skipping archival")
        print(f"⏱️  Total time: {time.time() - perf_start:.2f}s")
        return 0

    # Step 3: Extract concepts (with token checking and duplicate detection)
    try:
        concepts = extractor.extract_concepts(session_type)
        print(f"   Concepts found: {len(concepts)}")
    except ValueError as e:
        # Token limit exceeded
        print(f"\n❌ {e}")
        print(f"⏱️  Total time: {time.time() - perf_start:.2f}s")
        return 1

    # Step 4: Generate preview
    generator = PreviewGenerator()
    preview = generator.generate_preview(
        concepts=concepts,
        session_type=session_type,
        rems_reviewed=rems_reviewed
    )

    print("\n" + preview)

    # Step 5: Ask for approval
    print("\nWould you like to save these concepts? (y/n): ", end='')
    # In real implementation, would wait for user input

    # Step 6: Save if approved
    # Would implement actual saving logic here

    # Performance report
    total_time = time.time() - perf_start
    print(f"\n⏱️  Total execution time: {total_time:.2f}s")

    return 0

if __name__ == '__main__':
    sys.exit(main())