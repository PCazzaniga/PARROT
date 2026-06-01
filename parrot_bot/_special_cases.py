"""
Module to handle special replacements.

Functions:
    build_special_rules(x, y):  Computes the rules from y as using x
    find_special_matches(x, y): Returns the list of special matches from y found in x
"""

import re
from dataclasses import dataclass

@dataclass(frozen=True)
class _SpecialMatch:                # Record of a match of a special rule
    start: int
    end: int
    say: str
    pattern_index: int

@dataclass(frozen=True)
class SpecialRule:                 # Representation of the concrete form of a special case
    match_regex: re.Pattern
    say: str
    pattern_index: int

def build_special_rules(word: str, special_cases) -> list[SpecialRule]:
    """Computes the special rules adapted to the word"""
    stripped_word = word.strip()
    if stripped_word:
        rules: list[SpecialRule] = [
            SpecialRule(
                match_regex=re.compile(r'\b' + re.escape(p.MATCH) + r'\b'),
                say=p.SAY.replace('<WORD>', stripped_word) if "<WORD>" in p.SAY else p.SAY,
                pattern_index=index
            )
            for index, p in enumerate(special_cases.PATTERNS)
            if p.MATCH
        ]
        rules.append(
            SpecialRule(
                match_regex=re.compile(r'\b' + re.escape(stripped_word) + r'\b'),
                say=(
                    special_cases.RECURSIVE.replace('<WORD>', stripped_word)
                    if "<WORD>" in special_cases.RECURSIVE
                    else special_cases.RECURSIVE
                ),
                pattern_index=len(rules)
            )
        )
        return rules
    return []

def find_special_matches(text: str, rules: list[SpecialRule]) -> list[_SpecialMatch]:
    """Finds all matches of special rules in the text"""
    matches: list[_SpecialMatch] = []
    # For optimization, if special rules grow beyond 50 one could use compiled regex alternation with
    # combined = re.compile('|'.join(
    #   f'(?P<p{rule.pattern_index}>{rule.match_regex.pattern})'
    #   for rule in rules
    # ))
    # and finditer only on that.
    # It would then also be wise to cache the combined pattern in _SpecialRulesCache instead of rebuilding every time.
    for rule in rules:
        for m in rule.match_regex.finditer(text):
            matches.append(
                _SpecialMatch(
                    start=m.start(),
                    end=m.end(),
                    say=rule.say,
                    pattern_index=rule.pattern_index,
                )
            )
    # Sorts by Longest match -> Earlier match -> Pattern order
    matches.sort(key=lambda m: (-(m.end - m.start), m.start, m.pattern_index))
    selected: list[_SpecialMatch] = []
    for candidate in matches:
        if any(candidate.start < chosen.end and chosen.start < candidate.end for chosen in selected):
            continue
        selected.append(candidate)
    selected.sort(key=lambda m: m.start)
    return selected