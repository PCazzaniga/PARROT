"""
Module for smartly replacing elements in sentences.

Functions:
    update_special_cases(x):        Adds x to the patterns used to identify and match special elements
    has_replaceable_elements(x, y): Checks if x has elements replaceable with y
    replace_elements(x, y, z, k):   Replaces elements in x with y, with likelihood z each, using k to choose how to adapt the rest
    reset_caches():                 FOR TESTING ONLY
    set_random_seed():              FOR TESTING ONLY
"""

import random
from spacy.tokens import Token
from ._caches import get_caches, ensure_analysis, ensure_special_analysis, reset_caches
from ._word_forms import Form, is_plural_word, build_replacement_forms
from ._special_cases import build_special_rules
from ._load_settings import settings, Pattern, SpecialCases
from ._adapt_word import replace_token as replace_adapt
from ._adapt_sentence import replace_token as replace_preserve

_RNG = random.Random()
_SPECIAL_CASES: SpecialCases = settings.SPECIAL_CASES

##### THIS IS CURRENTLY UNUSED #####
def update_special_cases(new_special_case: Pattern) -> None:
    """Activates a new special case pattern for the current session."""
    _SPECIAL_CASES.PATTERNS.append(new_special_case)
    caches = get_caches()
    caches.rules.rules = build_special_rules(caches.rules.word, _SPECIAL_CASES)
    # This explicitly stales the cache to force a rebuild next time _ensure_special_analysis is called
    # The pattern has_replaceable_elements -> update_special_cases -> replace_elements is highly unusual
    # and discouraged, but this at least guarantees correctness and that the new pattern isn't missed
    caches.specials.sentence = ""

# This method caches language analysis on the sentence so the flow
#       has_replaceable_elements(str, word) >>> new_str = replace_elements(str, word, 100, True)
# should have essentially the same performance as
#       new_str = replace_elements(str, word, 100, True) >>> new_str != str
def has_replaceable_elements(sentence: str, word: str) -> bool:
    """
    Returns whether the sentence contains at least one replaceable object or subject token or any special case.
    
    Args:
        sentence (str): The input sentence
        word (str): The replacement word (for caching purposes)
    """
    ensure_analysis(sentence)
    ensure_special_analysis(sentence, word, _SPECIAL_CASES)
    caches = get_caches()
    return bool(caches.analysis.candidates) or bool(caches.specials.modified_token_ids)

def replace_elements(
    sentence: str,
    word: str,
    replacement_likelihood: float = 100,
    adapt_replacement: bool = True
) -> str:
    """
    Replaces grammatical objects and selected subjects in the sentence
    with the given word, adjusting the sentence to read grammatically coherent.

    Args:
        sentence (str): The input sentence.
        word (str): The word to replace objects and subjects with.
        replacement_likelihood (float): Percentage probability for each replacement opportunity to occurr.
        adapt_replacement (bool): Choice whether to conform the replacements to the rest of the sentence or viceversa

    Returns:
        str: The modified sentence.
    
    Raises:
        ValueError: If sentence or word are empty or blank, or if replacement_likelihood is not in (0, 100].
    """
    if not (0 < replacement_likelihood <= 100):
        #  If the likelihood is not in (0, 100] raise error (should have been normalized BEFORE calling)
        raise ValueError(f"Invalid replacement likelihood ({replacement_likelihood}), must be in (0, 100]")
    if not (word and sentence and word.strip() and sentence.strip()):
        #   If word or sentence are None, empty or only whitespace raise error (wasteful and useless to continue otherwise)
        raise ValueError(f"Invalid word ({word}) or sentence ({sentence})")
    # Parses once, or loads from cache, then operates via token-indexed replacements to preserve spacing/punctuation.
    ensure_analysis(sentence)
    # Matches and applies special replacements
    ensure_special_analysis(sentence, word, _SPECIAL_CASES)
    caches = get_caches()
    specials_ch = caches.specials
    # Finds all possibly replaceable tokens
    replacement_candidates = [
        token
        for token in caches.analysis.candidates
        if token.i not in specials_ch.modified_token_ids
    ]
    # If no regular candidate is left and no special replacement was found, returns the original sentence.
    if not replacement_candidates and not specials_ch.modified_token_ids:
        return sentence
    replacements: dict[int, str] = {}
    last_candidate_index = len(replacement_candidates) - 1
    # Special-case matches count as an already-applied replacement.
    no_replacement_applied = not bool(specials_ch.modified_token_ids)
    likelihood = replacement_likelihood / 100
    word_f = build_replacement_forms(word) if adapt_replacement else Form(word, is_plural_word(word))
    for candidate_index, token in enumerate(replacement_candidates):
        # Decides whether this candidate is replaced or is skipped.
        must_replace = no_replacement_applied and candidate_index == last_candidate_index
        if not (must_replace or (_RNG.random() <= likelihood)):
            continue
        replacement_text, extra_updates = (
            replace_adapt(token, word_f)
            if adapt_replacement
            else replace_preserve(token, word_f)
            )
        replacements[token.i] = replacement_text
        replacements.update(extra_updates)
        no_replacement_applied = False
    # Uses merged dictionary, to look in both at once
    # Regular replacements technically get priority, but candidates do not overlap so this is fine
    merged = {**specials_ch.replacements, **replacements}
    return ''.join(
        text + (t.whitespace_ if text else '')
        for t in caches.analysis.doc
        # This check assigns the appropriate replacement string but also skips empty strings
        # (e.g. from multi-token special matches)
        if (text := merged.get(t.i, t.text)) is not None
    )

def caches_reset() -> None:
    """Resets all of the current thread's caches. Intended for testing purposes only."""
    reset_caches()

def set_random_seed(seed: int | None) -> None:
    """Seeds the internal random number generator. Intended for testing purposes only."""
    _RNG.seed(seed)