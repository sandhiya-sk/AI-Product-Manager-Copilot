"""
utils/lemmatizer.py — Module 3 lemmatization utility using spaCy
"""

import spacy
import sys
import subprocess

nlp = None

def get_nlp():
    """Dynamically load or install spaCy model."""
    global nlp
    if nlp is not None:
        return nlp
    
    model_name = "en_core_web_sm"
    try:
        nlp = spacy.load(model_name)
    except OSError:
        # Model not found, attempt to download it
        print(f"spaCy model '{model_name}' not found. Downloading...")
        try:
            subprocess.run([sys.executable, "-m", "spacy", "download", model_name], check=True)
            nlp = spacy.load(model_name)
        except Exception as e:
            print(f"Error downloading spaCy model: {e}")
            # Fallback: simple lemmatization or return tokens if download fails
            raise e
    return nlp

def lemmatize(tokens: list) -> list:
    """
    Lemmatize a list of tokens using spaCy.
    
    Args:
        tokens: List of strings (tokens)
        
    Returns:
        List of lemmatized strings
    """
    if not tokens:
        return []
    
    try:
        nlp_model = get_nlp()
        # Join tokens back to process as a document
        doc = nlp_model(" ".join(tokens))
        
        lemmatized_tokens = [
            token.lemma_.lower() for token in doc
            if not token.is_stop and not token.is_punct and token.lemma_ != "-PRON-" and len(token.lemma_) > 1
        ]
        return lemmatized_tokens
    except Exception as e:
        print(f"Lemmatization fallback due to error: {e}")
        # Robust fallback: return lowercase tokens
        return [t.lower() for t in tokens if len(t) > 1]
