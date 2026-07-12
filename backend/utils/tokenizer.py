"""
utils/tokenizer.py — Module 3 tokenization utility using NLTK
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Pre-load stop words
STOP_WORDS = set(stopwords.words('english'))

def tokenize(text: str) -> list:
    """
    Tokenize the text into alphabetical lowercase tokens and remove stopwords.
    
    Args:
        text: Standardized text input
        
    Returns:
        List of cleaned tokens
    """
    if not text:
        return []
    
    # Tokenize words using NLTK
    raw_tokens = word_tokenize(text)
    
    # Filter: must be alphabetic and not a stop word
    cleaned_tokens = [
        t.lower() for t in raw_tokens
        if t.isalpha() and t.lower() not in STOP_WORDS
    ]
    
    return cleaned_tokens
