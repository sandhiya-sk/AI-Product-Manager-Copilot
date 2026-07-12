"""
utils/standardizer.py — Module 3 text standardization (Step 2)

Applies the following operations to cleaned text:
  1. Lowercase conversion
  2. Date normalization (extracting and formatting dates as YYYY-MM-DD)
  3. Status normalization
  4. Priority normalization
  5. Category normalization
"""

import re
from dateutil import parser as date_parser

def to_lowercase(text: str) -> str:
    """Convert string to lowercase."""
    return text.lower() if text else ""

def normalize_date(date_str: str) -> str:
    """
    Parse any date format string and normalize to YYYY-MM-DD.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    try:
        parsed_date = date_parser.parse(str(date_str))
        return parsed_date.strftime("%Y-%m-%d")
    except Exception:
        return None

def normalize_priority(value: str) -> str:
    """
    Map various priority inputs to canonical values: Low, Medium, High, Critical.
    """
    if not value:
        return "Medium"
    val = str(value).strip().lower()
    if val in ("low", "p3", "p4", "minor"):
        return "Low"
    elif val in ("medium", "p2", "normal", "average"):
        return "Medium"
    elif val in ("high", "p1", "urgent", "major"):
        return "High"
    elif val in ("critical", "p0", "blocker", "immediate"):
        return "Critical"
    return "Medium"

def normalize_category(value: str) -> str:
    """
    Map various category inputs to canonical values:
    Bug, Feature Request, Improvement, Complaint, General.
    """
    if not value:
        return "General"
    val = str(value).strip().lower()
    if "bug" in val or "issue" in val or "error" in val or "crash" in val or "fail" in val:
        return "Bug"
    elif "feature" in val or "request" in val or "add" in val or "new" in val:
        return "Feature Request"
    elif "improve" in val or "enhance" in val or "optimization" in val or "tweak" in val:
        return "Improvement"
    elif "complaint" in val or "bad" in val or "hate" in val or "poor" in val or "annoy" in val:
        return "Complaint"
    return "General"

def standardize(text: str, record: dict = None) -> str:
    """
    Standardize text: convert to lowercase.
    Additional date normalization in text can be applied if needed.
    """
    return to_lowercase(text)
