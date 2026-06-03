"""
Module to drive replacement while adapting the sentence to the replacement.

Functions:
    replace_token(x, y):    Returns the updates necessary to adapt x into y
"""

import pyinflect
from dataclasses import dataclass
from spacy.tokens import Token
from ._linguistics_utils import get_indefinite_article, match_token_case
from ._word_forms import Form
from ._candidates_selection import SUBJECT_TAGS

@dataclass(frozen=True)
class _Modifiers:                               # Modifiers attached to a token that can influence agreement
    determiner: Token | None
    number_modifier: Token | None
    single_modifiers: tuple[Token, ...]
    quantifier_modifiers: tuple[Token, ...]

# Determiners that usually imply plural semantics.
_PLURALISH_DETERMINERS = {'some', 'many', 'several', 'these', 'those', 'few', 'fewer', 'both'}
# Determiners that usually imply singular semantics (excludes a/an, handled separately by _article_update).
_SINGULARISH_DETERMINERS = {'one', 'this', 'that', 'each', 'every', 'either', 'neither'}
# Demonstratives conversion maps
_DEMONSTRATIVE_TO_PLURAL = {'this': 'these', 'that': 'those'}
_DEMONSTRATIVE_TO_SINGULAR = {'these': 'this', 'those': 'that'}
# Quantifiers with specific countability preferences.
_COUNTABLE_QUANTIFIERS = {'many', 'few', 'fewer', 'several', 'both'}
_UNCOUNTABLE_QUANTIFIERS = {'much', 'little', 'less'}
# Common uncountable nouns, to avoid forcing incorrect indefinite articles.
_UNCOUNTABLE_NOUNS = {
    'advice', 'air', 'baggage', 'butter', 'cash', 'chaos', 'clothing',
    'equipment', 'evidence', 'furniture', 'homework', 'information',
    'juice', 'knowledge', 'luggage', 'mail', 'money', 'news', 'progress', 'rice',
    'software', 'traffic', 'water', 'work'
}

def _is_uncountable_word(word: str) -> bool:
    """Returns whether the word in uncountable"""
    stripped = word.strip().lower()
    if not stripped:
        return False
    if stripped in _UNCOUNTABLE_NOUNS:
        return True
    # Also tries the rightmost token, for eventual compounds (e.g. "apple juice" -> "juice").
    return stripped.split()[-1] in _UNCOUNTABLE_NOUNS

def _collect_modifiers(token: Token) -> _Modifiers:
    """Returns other tokens representing various possible modifiers for the token"""
    determiner = None
    number_modifier = None
    single_modifiers = []
    quantifier_modifiers = []
    for child in token.children:
        # Keep nearest determiner/number modifier by index for stable rewrite behavior.
        if child.dep_ == 'det' and (determiner is None or child.i < determiner.i):
            determiner = child
        elif child.dep_ == 'nummod' and (number_modifier is None or child.i < number_modifier.i):
            number_modifier = child
        elif child.dep_ == 'amod' and child.lower_ == 'single':
            single_modifiers.append(child)
        elif child.dep_ in {'amod', 'quantmod'} and child.lower_ in _COUNTABLE_QUANTIFIERS | _UNCOUNTABLE_QUANTIFIERS:
            quantifier_modifiers.append(child)
    return _Modifiers(
        determiner=determiner,
        number_modifier=number_modifier,
        single_modifiers=tuple(single_modifiers),
        quantifier_modifiers=tuple(quantifier_modifiers),
    )

def _collect_coordinated_tokens(token: Token) -> list[Token]:
    """Collects all children token of a coordination head token"""
    coordinated = []
    for child in token.children:
        if child.dep_ == 'conj':
            coordinated.append(child)
            for cc_child in child.children:
                if cc_child.dep_ == 'cc':
                    coordinated.append(cc_child)
    for child in token.children:
        if child.dep_ == 'cc':
            coordinated.append(child)
    if not coordinated:
        return []
    unique_by_index = {child.i: child for child in coordinated}
    return [unique_by_index[i] for i in sorted(unique_by_index)]

def _collect_attached_phrase_tokens(token: Token) -> list[Token]:
    """Collects various children tokens grammatically related to the token """
    attached = []
    for child in token.children:
        if child.dep_ in {'det', 'compound', 'amod', 'nummod', 'poss', 'predet', 'quantmod'}:
            attached.append(child)
    if not attached:
        return []
    unique_by_index = {child.i: child for child in attached}
    return [unique_by_index[i] for i in sorted(unique_by_index)]

def _compound_and_coordination_updates(token: Token) -> dict[int, str]:
    """Returns the updates necessary to adapt tokens related to the token"""
    updates: dict[int, str] = {}
    for child in token.children:
        if child.dep_ == 'compound':
            updates[child.i] = ''
    for coordinated_token in _collect_coordinated_tokens(token):
        updates[coordinated_token.i] = ''
        for attached_token in _collect_attached_phrase_tokens(coordinated_token):
            updates[attached_token.i] = ''
    return updates

def _indefinite_subject_replacement(token: Token, word_form: Form) -> Form | None:
    """Returns the replacement for indefinite subject pronouns"""
    lower = token.lower_
    if lower in {'everyone', 'everybody'}:
        return Form(f'all {word_form.text}' if word_form.is_plural else f'every {word_form.text}', word_form.is_plural)
    if lower in {'someone', 'somebody'}:
        return Form(f'some {word_form.text}', word_form.is_plural)
    if lower in {'nobody', 'noone'}:
        return Form(f'no {word_form.text}', word_form.is_plural)
    return None

def _article_update(token: Token, modifiers: _Modifiers, replacement: Form) -> dict[int, str]:
    """Returns the updates necessary to match the article token to the token replacement"""
    updates: dict[int, str] = {}
    det = modifiers.determiner
    # "the" stays regardless of plurality or countability
    if det is None or det.lower_ == 'the':
        return updates
    if replacement.is_plural:
        # Remove indefinite article before plural noun (e.g., "a pears" -> "pears").
        if det.lower_ in {'a', 'an'}:
            updates[det.i] = ''
            return updates
        # Demonstratives agree with plurality
        if det.lower_ in _DEMONSTRATIVE_TO_PLURAL:
            updates[det.i] = match_token_case(det, _DEMONSTRATIVE_TO_PLURAL[det.lower_])
            return updates
    else:
        # Picks the correct indefinite article
        if det.lower_ in {'a', 'an'}:
            updates[det.i] = match_token_case(det, get_indefinite_article(replacement.text))
            return updates
        # Demonstratives agree with singularity
        if det.lower_ in _DEMONSTRATIVE_TO_SINGULAR:
            updates[det.i] = match_token_case(det, _DEMONSTRATIVE_TO_SINGULAR[det.lower_])
            return updates
    return updates

def _quantifier_updates(token: Token, modifiers: _Modifiers, replacement: Form) -> dict[int, str]:
    """Returns the updates necessary to match quantifier tokens to the token replacement"""
    updates: dict[int, str] = {}
    det = modifiers.determiner
    replacement_is_uncountable = _is_uncountable_word(replacement.text)
    article = 'some' if replacement_is_uncountable else get_indefinite_article(replacement.text)
    if replacement.is_plural:
        # Singular-ish determiners conflict with a plural replacement (excludes demonstratives, handled by _article_update)
        if det and det.lower_ in _SINGULARISH_DETERMINERS and det.lower_ not in _DEMONSTRATIVE_TO_PLURAL:
            updates[det.i] = match_token_case(det, 'some')
        for quant in modifiers.quantifier_modifiers:
            if quant.lower_ in _UNCOUNTABLE_QUANTIFIERS:
                updates[quant.i] = match_token_case(quant, 'many')
        for single_mod in modifiers.single_modifiers:
            updates[single_mod.i] = ''
    else:
        # Plural-ish determiners conflict with a singular replacement (but demonstratives already handled by _article_update)
        if det and det.lower_ in _PLURALISH_DETERMINERS and det.lower_ not in _DEMONSTRATIVE_TO_SINGULAR:
            updates[det.i] = match_token_case(det, article)
        for quant in modifiers.quantifier_modifiers:
            if quant.lower_ in _COUNTABLE_QUANTIFIERS:
                updates[quant.i] = match_token_case(quant, 'much' if replacement_is_uncountable else article)
            elif quant.lower_ in _UNCOUNTABLE_QUANTIFIERS and not replacement_is_uncountable:
                updates[quant.i] = match_token_case(quant, article)
    num = modifiers.number_modifier
    if num is not None:
        if det:
            # Suppress the numeral and all its dependents (in compound numerals like twenty-one)
            updates[num.i] = ''
            for dependent in num.subtree:
                if dependent.i != num.i:
                    updates[dependent.i] = ''
        else:
            # Replace the numeral and replace its dependents
            updates[num.i] = match_token_case(num, 'some' if replacement.is_plural else article)
            for dependent in num.subtree:
                if dependent.i != num.i:
                    updates[dependent.i] = ''
    return updates

def _update_carrier(verb: Token, want_plural: bool) -> tuple[int, str] | None:
    """Returns the update necessary to match a single finite verb to the desired plurality"""
    lemma = verb.lemma_.lower()
    # "be" is the only verb that cares about past tense (VBD)
    if lemma == 'be':
        if verb.tag_ == 'VBD':
            return (verb.i, match_token_case(verb, 'were' if want_plural else 'was'))
        return (verb.i, match_token_case(verb, 'are' if want_plural else 'is'))
    # "have" and "do" have immediate inflections
    if lemma == 'have' and verb.tag_ != 'VBD':
        return (verb.i, match_token_case(verb, 'have' if want_plural else 'has'))
    if lemma == 'do' and verb.tag_ != 'VBD':
        return (verb.i, match_token_case(verb, 'do' if want_plural else 'does'))
    # For all other [present-tense] lexical verbs, use pyinflect
    if verb.tag_ in {'VBZ', 'VBP'}:
        target_tag = 'VB' if want_plural else 'VBZ'
        inflected = pyinflect.getInflection(lemma, target_tag)
        if inflected:
            return (verb.i, match_token_case(verb, inflected[0]))
    # If nothing was found leave the verb untouched
    return None

def _verb_agreement_updates(token: Token, replacement: Form) -> dict[int, str]:
    """Returns the updates necessary to match verb tokens to the token replacement"""
    updates: dict[int, str] = {}
    head = token.head
    if head is None or head.pos_ not in {'VERB', 'AUX'}:
        return updates
    # If the token is a part of a coordination, plural must be mantained even if replacing with
    # a singular (e.g. "cats and dogs are enemies" -> "Bob and dogs are enemies")
    want_plural = (
        replacement.is_plural
        or (token.dep_ == 'conj' and token.head.dep_ in SUBJECT_TAGS)
        or (token.dep_ in SUBJECT_TAGS and any(child.dep_ == 'conj' for child in token.children))
    )
    # TODO, what about partitive constructs, do they need to force singular ?
    # Find the finite carrier: prefer an aux/cop child, fall back to the head verb itself
    finite_aux = [
        child for child in head.children
        if child.dep_ in {'aux', 'auxpass', 'cop'} and child.tag_ in {'VBZ', 'VBP', 'VBD'}
    ]
    carrier = min(finite_aux, key=lambda t: t.i) if finite_aux else None
    if carrier is None and head.tag_ in {'VBZ', 'VBP', 'VBD'}:
        carrier = head
    if carrier is not None:
        update = _update_carrier(carrier, want_plural)
        if update:
            updates[update[0]] = update[1]
    # Also update coordinated verbs (e.g. "were loud and are annoying")
    for child in head.children:
        if child.dep_ == 'conj' and child.pos_ in {'AUX', 'VERB'} and child.tag_ in {'VBZ', 'VBP', 'VBD'}:
            update = _update_carrier(child, want_plural)
            if update:
                updates[update[0]] = update[1]
    return updates

def replace_token(token: Token, word_form: Form) -> tuple[str, dict[int, str]]:
    """Given a token and the replacement word returns the replacement text and any update to apply"""
    replacement = _indefinite_subject_replacement(token, word_form) or word_form
    replacement = Form(match_token_case(token, replacement.text), replacement.is_plural)
    updates: dict[int, str] = {}
    modifiers = _collect_modifiers(token)
    article_updates = _article_update(token, modifiers, replacement)
    updates.update(article_updates)
    # If article was removed (e.g. indefinite article on plural replacement) match if necessary its capitalization
    det = modifiers.determiner
    if det is not None and article_updates.get(det.i) == '' and det.is_title:
        replacement = Form(replacement.text.capitalize(), replacement.is_plural)
    updates.update(_quantifier_updates(token, modifiers, replacement))
    if (token.dep_ in SUBJECT_TAGS
        or (token.dep_ == 'conj' and token.head.dep_ in SUBJECT_TAGS)
        or (token.dep_ == 'attr'
            and token.head.lemma_.lower() == 'be'
            and any(child.dep_ == 'expl' for child in token.head.children))
    ):
        updates.update(_verb_agreement_updates(token, replacement))
    else:
        updates.update(_compound_and_coordination_updates(token))
    return replacement.text, updates