#!/usr/bin/env python3
"""
Question Format Generator for FSRS Review

Implements 3 evidence-based question formats:
1. Short Answer (current Socratic dialogue)
2. Cloze Deletion (high efficiency per SuperMemo)
3. Problem-Solving (calculations for Finance/Science domains)

Design: Minimal implementation, maximum pedagogical value.
Research: PMC 11684041 (2024), SuperMemo 20 Rules.
"""

from typing import Dict, List, Optional
from enum import Enum


class QuestionFormat(Enum):
    """Supported question formats"""
    SHORT_ANSWER = "short-answer"  # Current Socratic dialogue
    MULTIPLE_CHOICE = "multiple-choice"  # MCQ with 3-4 options
    CLOZE = "cloze"  # Fill-in-the-blank with context
    PROBLEM_SOLVING = "problem-solving"  # Calculations, coding, translations


# Format effectiveness ratings (research-based)
FORMAT_EFFECTIVENESS = {
    QuestionFormat.SHORT_ANSWER: 9.0,  # PMC 11684041: 9/10
    QuestionFormat.MULTIPLE_CHOICE: 6.5,  # PMC 11684041: easier but less effective long-term
    QuestionFormat.CLOZE: 8.0,  # SuperMemo: "easy and effective"
    QuestionFormat.PROBLEM_SOLVING: 8.5,  # Transfer research: high for application
}


class QuestionFormatGenerator:
    """Generate questions in different formats based on Rem content"""

    def __init__(self):
        """Initialize format generator"""
        pass

    def generate_short_answer(
        self, rem_content: str, difficulty: str = "medium"
    ) -> Dict:
        """
        Generate Short Answer question (Socratic dialogue).

        This is the current default format used by review-master.

        Args:
            rem_content: Content from Rem file
            difficulty: "easy" | "medium" | "hard"

        Returns:
            {
                "format": "short-answer",
                "question_template": "str (for review-master to customize)",
                "expected_elements": ["key", "concepts"],
                "validation_strategy": "semantic-similarity",
                "hints": ["progressive", "hints"]
            }
        """
        # This is already implemented in review-master agent
        # Just return metadata for format tracking
        return {
            "format": QuestionFormat.SHORT_ANSWER.value,
            "question_template": "Ask open-ended question about core concepts",
            "expected_elements": [],  # Populated by review-master
            "validation_strategy": "semantic-similarity",
            "hints": [],  # Populated by review-master
        }

    def generate_multiple_choice(
        self, rem_content: str, difficulty: str = "medium"
    ) -> Dict:
        """
        Generate Multiple Choice question.

        Easier but less effective long-term (6.5/10). Good for recognition.

        Args:
            rem_content: Content from Rem file
            difficulty: "easy" (obvious wrong) | "medium" (plausible) | "hard" (subtle differences)

        Returns:
            {
                "format": "multiple-choice",
                "question_template": "str (question stem)",
                "options": [{"label": "A", "text": "...", "correct": bool}],
                "validation_strategy": "exact-match"
            }

        Example:
            Q: What does 'retrospectively' mean?
            <option>A. Looking forward to future events</option>
            <option>B. Looking back at past events (✓)</option>
            <option>C. Looking at current situations</option>
            <option>D. Looking at alternative possibilities</option>
        """
        option_count = {"easy": 3, "medium": 4, "hard": 4}.get(difficulty, 4)

        return {
            "format": QuestionFormat.MULTIPLE_CHOICE.value,
            "question_template": "Create MCQ with 1 correct + 3 plausible distractors",
            "option_count": option_count,
            "validation_strategy": "exact-match",
            "hint_strategy": "eliminate-one-wrong-option",
        }

    def generate_cloze(
        self, rem_content: str, difficulty: str = "medium"
    ) -> Dict:
        """
        Generate Cloze Deletion question.

        SuperMemo principle: "Easy and effective" for pattern matching.

        Args:
            rem_content: Content from Rem file (Core Memory Points section)
            difficulty: "easy" (1 blank) | "medium" (2 blanks) | "hard" (3 blanks)

        Returns:
            {
                "format": "cloze",
                "question_text": "str with {blank} placeholders",
                "blanks": [{"index": 1, "answer": "str", "hints": []}],
                "context": "str (unchanged parts for pattern matching)",
                "validation_strategy": "fuzzy-match"
            }

        Example:
            Input: "Relative shift: dS = S × ε (proportional)"
            Output: "Relative shift: dS = {blank1} (proportional)"
                    blanks: [{"index": 1, "answer": "S × ε"}]
        """
        # Extract key formulas/terms from rem_content
        # For MVP: Let review-master agent generate cloze questions
        # This method provides structure for future automation

        blank_count = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 1)

        return {
            "format": QuestionFormat.CLOZE.value,
            "question_template": f"Create cloze with {blank_count} blank(s) from core concepts",
            "blank_count": blank_count,
            "validation_strategy": "fuzzy-match",
            "hint_strategy": "first-letter | word-length",
        }

    def generate_problem_solving(
        self, rem_content: str, domain: str, difficulty: str = "medium"
    ) -> Dict:
        """
        Generate Problem-Solving question (calculations, code, translations).

        Domain-specific applications:
        - Finance: Calculate option prices, Greeks, portfolio metrics
        - Programming: Implement algorithm, debug code
        - Language: Translate sentence, conjugate verb

        Args:
            rem_content: Content from Rem file
            domain: "finance" | "programming" | "language" | "science"
            difficulty: "easy" | "medium" | "hard"

        Returns:
            {
                "format": "problem-solving",
                "problem_template": "str (scenario + question)",
                "expected_solution": {"steps": [], "final_answer": ""},
                "validation_strategy": "rubric-based",
                "rubric": {"criteria": "bool"}
            }

        Example (Finance):
            Problem: "Calculate intrinsic value of call option: S=105, K=100"
            Expected: {"steps": ["IV = max(S-K, 0)", "IV = max(5, 0)"], "final_answer": "5"}
        """
        # Domain-specific templates
        domain_templates = {
            "finance": "Generate calculation problem using concept formulas",
            "programming": "Generate coding problem applying concept",
            "language": "Generate translation/conjugation problem",
            "science": "Generate calculation/experiment problem",
        }

        template = domain_templates.get(domain, "Generate application problem")

        return {
            "format": QuestionFormat.PROBLEM_SOLVING.value,
            "question_template": template,
            "domain": domain,
            "validation_strategy": "rubric-based",
            "rubric_template": {
                "correct_formula": "Did user use correct formula?",
                "calculation_accurate": "Is calculation accurate?",
                "final_answer_correct": "Is final answer correct?",
            },
        }

    def select_format(
        self,
        rem_data: Dict,
        review_count: int = 0,
        recent_formats: Optional[List[str]] = None,
    ) -> QuestionFormat:
        """
        Provide format options context for AI to choose.

        Selection logic:
        1. First review: Always Short Answer (baseline)
        2. Avoid 3+ consecutive same format (variety)
        3. Otherwise: Return default (AI will choose based on content)

        Args:
            rem_data: Rem metadata (id, title, fsrs_state)
            review_count: Number of previous reviews
            recent_formats: List of last 3 formats used

        Returns:
            QuestionFormat enum value (default for AI to override)
        """
        if recent_formats is None:
            recent_formats = []

        # Rule 1: First review = Short Answer (baseline)
        if review_count == 0:
            return QuestionFormat.SHORT_ANSWER

        # Rule 2: Avoid 3+ consecutive same format
        if len(recent_formats) >= 2:
            if recent_formats[-1] == recent_formats[-2]:
                last_format = recent_formats[-1]
                available = [f for f in QuestionFormat if f.value != last_format]
                if available:
                    # Prefer variety: MCQ, Cloze, or Problem-Solving
                    for preferred in [QuestionFormat.MULTIPLE_CHOICE, QuestionFormat.CLOZE, QuestionFormat.PROBLEM_SOLVING]:
                        if preferred in available:
                            return preferred
                    return available[0]

        # Default: Return Short Answer as suggestion
        # AI will choose based on Rem content:
        # - Definitions/vocabulary → MCQ or Cloze
        # - Formulas → Cloze
        # - Calculations → Problem-Solving
        return QuestionFormat.SHORT_ANSWER


# Self-test
if __name__ == "__main__":
    print("Running QuestionFormatGenerator self-test...")

    generator = QuestionFormatGenerator()

    # Test format generation
    sa_question = generator.generate_short_answer("Test content", "medium")
    assert sa_question["format"] == "short-answer"
    print("✅ generate_short_answer: PASS")

    mcq_question = generator.generate_multiple_choice("Test content", "medium")
    assert mcq_question["format"] == "multiple-choice"
    assert mcq_question["option_count"] == 4
    print("✅ generate_multiple_choice: PASS")

    cloze_question = generator.generate_cloze("Test content", "medium")
    assert cloze_question["format"] == "cloze"
    assert cloze_question["blank_count"] == 2
    print("✅ generate_cloze: PASS")

    ps_question = generator.generate_problem_solving("Test content", "finance", "medium")
    assert ps_question["format"] == "problem-solving"
    assert ps_question["domain"] == "finance"
    print("✅ generate_problem_solving: PASS")

    # Test format selection
    result = generator.select_format(
        {"id": "test", "title": "Test"},
        review_count=0,
    )
    assert result == QuestionFormat.SHORT_ANSWER, "First review should be Short Answer"
    print("✅ select_format (first review): PASS")

    result = generator.select_format(
        {"id": "test", "title": "Test"},
        review_count=2,
        recent_formats=["short-answer", "short-answer"],
    )
    # Should return MCQ (first preferred alternative) or Cloze or Problem-Solving
    assert result in [QuestionFormat.MULTIPLE_CHOICE, QuestionFormat.CLOZE, QuestionFormat.PROBLEM_SOLVING], "Avoid 3rd consecutive Short Answer"
    print(f"✅ select_format (variety): PASS (selected {result.value})")

    result = generator.select_format(
        {"id": "test", "title": "Test"},
        review_count=5,
    )
    assert result == QuestionFormat.SHORT_ANSWER, "Default is Short Answer (AI will override)"
    print("✅ select_format (default): PASS")

    print("\n✅ All QuestionFormatGenerator self-tests passed!")
