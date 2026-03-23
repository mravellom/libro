"""Keyword analysis — extract patterns from competitor titles."""

import re
from collections import Counter
from dataclasses import dataclass


# Common English stop words to filter out
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "my", "your", "his", "her", "our", "its", "me", "us",
    "not", "no", "so", "if", "do", "did", "has", "have", "had",
    "will", "can", "may", "would", "could", "should", "up", "out",
    "all", "each", "every", "both", "few", "more", "most", "some",
    "any", "other", "into", "over", "after", "before", "between",
}


@dataclass
class KeywordInsight:
    """Analysis result for a set of competitor titles."""
    top_words: list[tuple[str, int]]       # (word, frequency)
    top_bigrams: list[tuple[str, int]]     # (bigram, frequency)
    common_patterns: list[str]             # Title patterns found
    suggested_keywords: list[str]          # KDP keyword suggestions (max 7)


def analyze_titles(titles: list[str]) -> KeywordInsight:
    """Analyze competitor titles to find keyword opportunities.

    Args:
        titles: List of competitor product titles.

    Returns:
        KeywordInsight with word frequencies, patterns, and keyword suggestions.
    """
    if not titles:
        return KeywordInsight([], [], [], [])

    # Clean and tokenize
    all_words: list[str] = []
    all_bigrams: list[str] = []

    for title in titles:
        words = _tokenize(title)
        meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        all_words.extend(meaningful)

        # Bigrams (pairs of consecutive meaningful words)
        for i in range(len(meaningful) - 1):
            bigram = f"{meaningful[i]} {meaningful[i + 1]}"
            all_bigrams.append(bigram)

    # Count frequencies
    word_counts = Counter(all_words)
    bigram_counts = Counter(all_bigrams)

    top_words = word_counts.most_common(20)
    top_bigrams = bigram_counts.most_common(10)

    # Detect common title patterns
    patterns = _detect_patterns(titles)

    # Generate keyword suggestions for KDP (max 7)
    suggested = _suggest_keywords(top_words, top_bigrams)

    return KeywordInsight(
        top_words=top_words,
        top_bigrams=top_bigrams,
        common_patterns=patterns,
        suggested_keywords=suggested[:7],
    )


def _tokenize(text: str) -> list[str]:
    """Clean and split text into lowercase words."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def _detect_patterns(titles: list[str]) -> list[str]:
    """Detect common structural patterns in titles."""
    patterns = []

    # Check for common structures
    colon_count = sum(1 for t in titles if ":" in t)
    if colon_count > len(titles) * 0.3:
        patterns.append(f"Colon-split titles ({colon_count}/{len(titles)}): 'Main Title: Subtitle'")

    dash_count = sum(1 for t in titles if " - " in t)
    if dash_count > len(titles) * 0.2:
        patterns.append(f"Dash-split titles ({dash_count}/{len(titles)})")

    # Check for audience targeting
    audience_words = ["women", "men", "kids", "teens", "adults", "girls", "boys"]
    for word in audience_words:
        count = sum(1 for t in titles if word.lower() in t.lower())
        if count >= 2:
            patterns.append(f"Audience targeting: '{word}' appears in {count} titles")

    # Check for time-based
    time_words = ["daily", "weekly", "52 week", "365", "monthly", "minute"]
    for word in time_words:
        count = sum(1 for t in titles if word.lower() in t.lower())
        if count >= 2:
            patterns.append(f"Time-based: '{word}' appears in {count} titles")

    return patterns


def _suggest_keywords(
    top_words: list[tuple[str, int]],
    top_bigrams: list[tuple[str, int]],
) -> list[str]:
    """Generate KDP keyword suggestions from analysis.

    KDP allows up to 7 keywords/phrases, each max 50 chars.
    """
    suggestions: list[str] = []

    # Prioritize bigrams (more specific, better for KDP)
    for bigram, count in top_bigrams:
        if count >= 2 and len(bigram) <= 50:
            suggestions.append(bigram)
        if len(suggestions) >= 4:
            break

    # Fill with top single words
    used_words = set()
    for bigram in suggestions:
        used_words.update(bigram.split())

    for word, count in top_words:
        if word not in used_words and count >= 2:
            suggestions.append(word)
            used_words.add(word)
        if len(suggestions) >= 7:
            break

    return suggestions
