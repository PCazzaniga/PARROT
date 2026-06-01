"""
Module to drive replacement while adapting the replacement to the original sentence.

Functions:
    replace_token(x, y):    Returns the updates necessary to adapt y to x
"""

from spacy.tokens import Token
from ._linguistics_utils import get_indefinite_article, match_token_case
from ._word_forms import Form, ReplacementForms, PLURAL_TAGS

# Map to guide replacement of indefinite subject pronouns
_INDEF_SUBJ_MAP = {'everyone': 'every', 'everybody': 'every', 'someone': 'some',
                   'somebody': 'some', 'nobody': 'no', 'noone': 'no'}

def _pick_form(forms: ReplacementForms, is_plural: bool) -> Form:
    """Returns the form matching the requested plurality, preferring original when it already matches."""
    if forms.original.is_plural == is_plural:
        return forms.original
    return forms.plural if is_plural else forms.singular

def _choose_replacement_form(token: Token, forms: ReplacementForms) -> Form:
    """Returns the appropriate singular or plural Form for the token"""
    return _pick_form(forms, token.tag_ in PLURAL_TAGS)

def _indefinite_subject_replacement(token: Token, forms: ReplacementForms) -> Form | None:
    """Returns the replacement for indefinite subject pronouns"""
    if (token.pos_ != 'PRON'):
        return None
    suffix = _INDEF_SUBJ_MAP.get(token.lower_)
    return Form(f'{suffix} {_pick_form(forms, False).text}', False) if suffix else None

def _article_update(token: Token, replacement: Form) -> tuple[int, str] | None:
    """Returns the updates necessary to match the article token to the token"""
    # Gets modifiers attached to the object token to find the article.
    det = None
    for child in token.children:
        if child.dep_ == 'det' and (det is None or child.i < det.i):
            # Keeps leftmost determiner by index for stable rewrite behavior.
            det = child
    if det is None or det.lower_ not in {'a', 'an'}:
        return None
    article = get_indefinite_article(replacement.text)
    return (det.i, match_token_case(det, article))

def replace_token(token: Token, word_forms: ReplacementForms ) -> tuple[str, dict[int, str]]:
    """Given a token and the possible forms of the replacement word returns the replacement text and any update to apply"""
    # If the token is not a pronoun or not an indefinite subject one this is None
    replacement = _indefinite_subject_replacement(token, word_forms)
    if replacement is None:
        replacement = _choose_replacement_form(token, word_forms)
    replacement = Form(match_token_case(token, replacement.text), replacement.is_plural)
    updates: dict[int, str] = {}
    article_update = _article_update(token, replacement)
    if article_update:
        updates[article_update[0]] = article_update[1]
    return replacement.text, updates
