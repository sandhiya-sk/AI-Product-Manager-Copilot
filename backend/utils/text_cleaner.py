"""
utils/text_cleaner.py — Module 3 text cleaning pipeline (Step 1)

Applies the following operations in sequence to raw description text:
  1. Remove HTML tags
  2. Remove URLs
  3. Remove emojis (Unicode category filtering)
  4. Normalize punctuation (collapse repeated . and !)
  5. Remove extra whitespace
  6. Remove special characters (keep alphanumeric + basic punctuation)
"""

import re
import unicodedata


def remove_html(text: str) -> str:
    """Strip HTML tags: <b>foo</b> → foo."""
    return re.sub(r"<[^>]+>", " ", text)


def remove_urls(text: str) -> str:
    """Remove http(s) URLs and www. references."""
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)
    return text


def remove_emojis(text: str) -> str:
    """
    Remove emoji and special symbols using Unicode category lookup.
    Keeps regular punctuation and alphanumeric characters.
    """
    cleaned = []
    for char in text:
        cat = unicodedata.category(char)
        # So = Symbol, other  |  Sk = Symbol, modifier
        # Sm = Symbol, math   |  Sc = Symbol, currency (keep? removed for safety)
        # Cs = Surrogate      |  Co = Private Use
        if cat.startswith(("So", "Sk", "Sm", "Cs", "Co")):
            cleaned.append(" ")
        else:
            cleaned.append(char)
    return "".join(cleaned)


def normalize_punctuation(text: str) -> str:
    """Collapse repeated punctuation marks."""
    text = re.sub(r"\.{2,}", ".", text)   # ... → .
    text = re.sub(r"!{2,}", "!", text)   # !!! → !
    text = re.sub(r"\?{2,}", "?", text)  # ??? → ?
    text = re.sub(r",{2,}", ",", text)   # ,,, → ,
    return text


def remove_extra_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs/newlines into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def remove_special_chars(text: str) -> str:
    """
    Remove characters that are not alphanumeric or basic punctuation.
    Keeps: letters, digits, spaces, . , ! ? ' " - _
    """
    return re.sub(r"[^\w\s.,!?'\"\\-]", " ", text)


def clean_text(text: str) -> str:
    """
    Run the full cleaning pipeline on raw text.

    Pipeline order:
        HTML → URL → Emoji → Special chars → Punctuation → Whitespace

    Args:
        text: Raw description string from raw_feedback.

    Returns:
        Cleaned string (HTML-free, URL-free, emoji-free, normalized spacing).
    """
    if not text or not text.strip():
        return ""

    text = remove_html(text)
    text = remove_urls(text)
    text = remove_emojis(text)
    text = remove_special_chars(text)
    text = normalize_punctuation(text)
    text = remove_extra_whitespace(text)
    return text
