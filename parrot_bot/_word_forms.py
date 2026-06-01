"""
Module with functions that handles a replacement word's plurality.

Functions:
    is_plural_word(x):          Determines if x is a plural word
    build_replacement_forms(x): Returns the plurality alternatives of x
"""

import pyinflect
from dataclasses import dataclass
from functools import lru_cache
from ._nlp_pipeline import get_pipeline


PLURAL_TAGS = {'NNS', 'NNPS'}              # Penn Treebank plural noun tags.

_COMMON_FALSE_PLURALS = {                   # Nouns that may appear plural but are not (mostly)
    'news', 'series', 'species', 'means', 'headquarters', 'physics', 'mathematics', 'maths', 'economics', 'politics',
    'statistics', 'athletics', 'measles', 'diabetes'
    }

@dataclass(frozen=True)
class Form:                        # Form of a word
    text: str
    is_plural: bool

@dataclass(frozen=True)
class ReplacementForms:            # Original word form plus normalized singular/plural variants.
    original: Form
    singular: Form
    plural: Form

@lru_cache(maxsize=None)
def is_plural_word(word: str) -> bool:
    """Determines whether the word is plural based on NLP analysis or a simple ends-with-s heuristic"""
    stripped = word.strip()
    lower_word = stripped.lower()
    # First a safeguard against false plurals
    if lower_word in _COMMON_FALSE_PLURALS:
        return False
    # Second, parses in isolation (fast result for most nouns).
    nlp = get_pipeline()
    parsed = nlp(stripped)
    if len(parsed) == 1:
        if parsed[0].tag_ in PLURAL_TAGS:
            return True
        if parsed[0].tag_ in {'NN', 'NNP'}:
            return False
    # Third, reparses in determiner context ("the ..."). This biases the model towards nominal analysis,
    # improving result for forms that may be mis-tagged when isolated (e.g. "sails" is tagged as verb)
    contextual = nlp(f'the {stripped}')
    if len(contextual) >= 2:
        candidate = contextual[1]
        if candidate.tag_ in PLURAL_TAGS:
            return True
        if candidate.tag_ in {'NN', 'NNP'}:
            return False
    # Last resort, a basic "ends with s" heuristic
    return lower_word.endswith('s') and not lower_word.endswith('ss')

@lru_cache(maxsize=None)
def build_replacement_forms(word: str) -> ReplacementForms:
    """Builds the forms of the word and its computed singular and plural variants"""
    replacement_doc = get_pipeline()(word.strip())
    original = Form(word, is_plural_word(word))
    if len(replacement_doc) == 0:
        return ReplacementForms(original=original, singular=original, plural=original)
    if len(replacement_doc) == 1:
        head_token = replacement_doc[0]
        prefix = ""
    else:
        # For multi-token words, inflection considers the last token only (e.g. "truck" in "fire truck")
        head_token = replacement_doc[-1]
        prefix = word.rstrip()[: word.rstrip().rfind(head_token.text)]
    head_word = head_token.text
    singular = head_word
    plural = head_word
    # If original is plural tries to build its singular form, otherwise viceversa
    if original.is_plural:
        # First, tries with lemmatizer (the best for irregular forms).
        singular = head_token.lemma_ or head_word
        # Second, fallback to pyinflect if the lemma appears still plural
        if is_plural_word(singular):
            inflected = pyinflect.getInflection(head_word, 'NN')
            if inflected:
                singular = inflected[0]
        # Finally, fallback to an heuristic if none of the above produced a singular-looking word
        if is_plural_word(singular):
            lower = singular.lower()
            if lower.endswith('ies') and len(singular) > 3:                                             # Example: "cities" -> "city".
                singular = singular[:-3] + 'y'
            elif lower.endswith(('sses', 'shes', 'ches', 'xes', 'zes', 'oes')) and len(singular) > 2:   # Example: "boxes" -> "box".
                singular = singular[:-2]
            elif lower.endswith('s') and not lower.endswith('ss') and len(singular) > 1:                # Example: "cars" -> "car".
                singular = singular[:-1]
    else:
        # To build the plural, pyinflect is enough
        inflected = pyinflect.getInflection(head_word, 'NNS')
        if inflected:
            plural = inflected[0]
    return ReplacementForms(
        original=original,
        singular=Form(prefix + singular, False),
        plural=Form(prefix + plural, True)
    )