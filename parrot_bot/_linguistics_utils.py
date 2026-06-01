"""
Module with linguistic utility functions.

Functions:
    get_indefinite_article(x):  Returns "a" or "an", whichever is better for x
    match_token_case(x, y):     Returns y modified to match x's capitalization and case
"""

import pronouncing
from spacy.tokens import Token

# Vowel-like phonemes
_ARPABET_VOWELS = { "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW" }

def get_indefinite_article(word: str) -> str:
    """Returns 'a' or 'an' based on the word's starting phoneme or using a simple first-letter heuristic."""
    # Gets the phonemes for the word
    phones = pronouncing.phones_for_word(word)
    # If succesfully got phonemes checks the first to decide
    if phones:
        first_ph = phones[0].split()[0].rstrip("012")
        return "an" if first_ph in _ARPABET_VOWELS else "a"
    # Heuristic fallback
    lower = word.lower()
    if lower.startswith(("honest", "hour", "honor", "heir", "herb")):                   # Prefixes with silent h
        return "an"
    if lower.startswith(("uni", "use", "user", "ufo", "uti", "euro", "ewe", "eul")):    # Prefixes with "you" sound
        return "a"
    if lower.startswith(("one", "once")):                                               # Prefixes with "wha" sound
        return "a"
    if word and word[0].isupper():                                                      # Uppercase acronyms with "vowel" sound
        return "an" if word[0] in "FHLMNRSX" else "a"
    if lower.startswith(("a", "e", "i", "o", "u")):                                     # Words that start with vowel
        return "an"
    return "a"                                                                          # Default assumption of consonant

def match_token_case(token: Token, value: str) -> str:
    """Return value capitalized or as-is, matching token"""
    if token.is_title:
        return value.capitalize()
    elif token.is_upper:
        return value.upper()
    else:
        return value