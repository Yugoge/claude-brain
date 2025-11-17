#!/usr/bin/env python3
"""
Token Estimation Utility

Estimates token count for text content to prevent context window overflow.
Uses tiktoken library (OpenAI's tokenizer) for accurate estimates.

Usage:
    from utils.token_estimation import estimate_tokens, check_token_limit

    # Estimate tokens in text
    count = estimate_tokens(long_text)

    # Check if text exceeds limit (raises exception if over)
    check_token_limit(conversation_history, max_tokens=150000)
"""

import sys
from typing import List, Dict, Any

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


# Token limits for safety
DEFAULT_MAX_TOKENS = 150000  # Conservative limit for large conversations
WARNING_THRESHOLD = 100000   # Warn user when approaching limit


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text.

    Args:
        text: Text to estimate
        model: Model name for tokenizer (default: gpt-4)

    Returns:
        Estimated token count

    Note:
        Falls back to character-based estimation (chars/4) if tiktoken unavailable.
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback to cl100k_base (GPT-4 default)
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                pass

    # Fallback: rough approximation (1 token ≈ 4 characters)
    return len(text) // 4


def estimate_conversation_tokens(
    conversation: List[Dict[str, Any]],
    model: str = "gpt-4"
) -> int:
    """
    Estimate total tokens in conversation history.

    Args:
        conversation: List of conversation turns with 'role' and 'content'
        model: Model name for tokenizer

    Returns:
        Total estimated token count
    """
    total = 0

    for turn in conversation:
        # Add role tokens (~4 tokens per turn for role label)
        total += 4

        # Add content tokens
        content = turn.get('content', '')
        if isinstance(content, str):
            total += estimate_tokens(content, model)
        elif isinstance(content, list):
            # Handle multi-part content (text + images)
            for part in content:
                if isinstance(part, dict) and 'text' in part:
                    total += estimate_tokens(part['text'], model)

    return total


def check_token_limit(
    text_or_conversation: Any,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    context: str = "content"
) -> int:
    """
    Check if content exceeds token limit.

    Args:
        text_or_conversation: String or conversation list to check
        max_tokens: Maximum allowed tokens (default: 150000)
        context: Description of what's being checked (for error message)

    Returns:
        Actual token count

    Raises:
        ValueError: If content exceeds max_tokens
    """
    # Determine token count based on input type
    if isinstance(text_or_conversation, str):
        token_count = estimate_tokens(text_or_conversation)
    elif isinstance(text_or_conversation, list):
        token_count = estimate_conversation_tokens(text_or_conversation)
    else:
        raise TypeError(
            f"Expected str or list, got {type(text_or_conversation)}"
        )

    # Check limit
    if token_count > max_tokens:
        raise ValueError(
            f"{context} exceeds token limit: {token_count:,} > {max_tokens:,} tokens\n\n"
            f"🔴 SOLUTION: Split this into multiple smaller sessions.\n"
            f"   Current size: {token_count:,} tokens ({token_count/max_tokens:.1%} of limit)\n"
            f"   Recommended: Split into {(token_count // max_tokens) + 1} sessions"
        )

    # Warn if approaching limit
    if token_count > WARNING_THRESHOLD:
        percentage = (token_count / max_tokens) * 100
        print(
            f"⚠️  Warning: {context} is large ({token_count:,} tokens, {percentage:.0f}% of limit)",
            file=sys.stderr
        )

    return token_count


def format_token_count(count: int) -> str:
    """
    Format token count for human-readable display.

    Args:
        count: Token count

    Returns:
        Formatted string (e.g., "45.2K tokens" or "1.2M tokens")
    """
    if count < 1000:
        return f"{count} tokens"
    elif count < 1_000_000:
        return f"{count/1000:.1f}K tokens"
    else:
        return f"{count/1_000_000:.2f}M tokens"


def estimate_file_tokens(file_path: str, model: str = "gpt-4") -> int:
    """
    Estimate tokens in a file.

    Args:
        file_path: Path to text file
        model: Model name for tokenizer

    Returns:
        Estimated token count
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return estimate_tokens(content, model)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0


# Example usage
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python token_estimation.py <file_path>")
        print("\nEstimates token count for a file")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"📊 Estimating tokens for: {file_path}")
    count = estimate_file_tokens(file_path)
    print(f"   Total: {format_token_count(count)}")

    # Check against limits
    try:
        check_token_limit(count, context=f"File {file_path}")
        print(f"✅ Within safe limits")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
