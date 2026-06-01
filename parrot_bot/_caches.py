"""
Module that handles caches for NLP analysis.

Functions:
    get_caches():                       Returns the caches.
    ensure_analysis(x):                 Performs NLP analysis on x if the cache is stale
    ensure_special_analysis(x, y, z):   Performs special analysis on x using y and z if the cache is stale
    reset_caches():                     FOR TESTING ONLY
"""

import threading
from spacy.tokens import Doc, Token
from ._nlp_pipeline import get_pipeline, ensure_pipeline_loaded
from ._special_cases import SpecialRule, build_special_rules, find_special_matches
from ._candidates_selection import get_replacement_candidates
from ._word_forms import is_plural_word, build_replacement_forms
from ._load_settings import SpecialCases

_THREAD_LOCAL = threading.local()

class _ReplacementAnalysisCache:    # Cache for the NLP analysis and replacement candidates detection of the last sentence analyzed
    def __init__(self):
        self.sentence: str = ""
        self.doc: Doc | None = None
        self.candidates: list[Token] = []

class _SpecialAnalysisCache:        # Same as above but for special matches detection
    def __init__(self):
        self.sentence: str = ""
        self.word: str = ""
        self.replacements: dict[int, str | None] = {}
        self.modified_token_ids: set[int] = set()

class _SpecialRulesCache:           # Cache for special rules adapted to the last replacement word
    def __init__(self):
        self.word: str = ""
        self.rules: list[SpecialRule] = []

class _Caches:
    def __init__(self):
        self.analysis = _ReplacementAnalysisCache()
        self.specials = _SpecialAnalysisCache()
        self.rules = _SpecialRulesCache()


def get_caches() -> _Caches:
    ensure_pipeline_loaded()
    if not hasattr(_THREAD_LOCAL, 'caches'):
        _THREAD_LOCAL.caches = _Caches()
    return _THREAD_LOCAL.caches


def ensure_analysis(sentence: str) -> None:
    """Performs and caches sentence analysis if cache is stale"""
    cache = (get_caches()).analysis
    if cache.sentence != sentence:
        cache.doc = get_pipeline()(sentence)
        cache.candidates = get_replacement_candidates(cache.doc)
        cache.sentence = sentence

def ensure_special_analysis(sentence: str, word: str, special_cases: SpecialCases) -> None:
    """Performs and caches sentence special analysis if cache is stale"""
    ensure_analysis(sentence)
    caches = get_caches()
    specials_ch = caches.specials
    if specials_ch.sentence != sentence or specials_ch.word != word:
        rules_ch = caches.rules
        if rules_ch.word != word:
            rules_ch.rules = build_special_rules(word, special_cases)
            rules_ch.word = word
        replacements: dict[int, str | None] = {t.i: t.text for t in caches.analysis.doc}
        modified_token_ids: set[int] = set()
        matches = find_special_matches(sentence, rules_ch.rules)
        for match in matches:
            # Finds all tokens that make up the match
            match_pieces = [
                t for t in caches.analysis.doc
                if t.idx < match.end and (t.idx + len(t.text)) > match.start
            ]
            if not match_pieces:
                continue
            # First token of the match gets the replacement
            replacements[match_pieces[0].i] = match.say
            modified_token_ids.add(match_pieces[0].i)
            # Any other token of the same match is "removed"
            for token in match_pieces[1:]:
                replacements[token.i] = None
                modified_token_ids.add(token.i)
        specials_ch.replacements = replacements
        specials_ch.modified_token_ids = modified_token_ids
        specials_ch.sentence = sentence
        specials_ch.word = word

def reset_caches() -> None:
    if hasattr(_THREAD_LOCAL, 'caches'):
        _THREAD_LOCAL.caches = _Caches()
    is_plural_word.cache_clear()
    build_replacement_forms.cache_clear()