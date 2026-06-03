"""
Module with function to determine replacement candidates in a sentence.

Functions:
    get_replacement_candidates(x):  Returns the list of replaceable tokens in x
"""

from spacy.tokens import Doc, Token

_OBJECT_TAGS = {'dobj', 'pobj'}             # Dependency tags considered as grammatical objects to replace.
SUBJECT_TAGS = {'nsubj', 'nsubjpass'}      # Dependency tags considered as grammatical subjects to replace.

# Lists of pronouns, exluded as replacement targets because they'd require careful handling and dedicated agreement
# (Technically, of the object pronouns, only replacing me in imperatives and whom in questions would sound too much broken)
_OBJ_PRONOUNS = {'me', 'him', 'her', 'it', 'us', 'them', 'whom'}
_SUBJ_PERSONAL_PRONOUNS = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}

# Partitive/measure heads used in constructs like "a piece of cake".
_PARTITIVE_HEADS = {
    # Portions
    'bit', 'block', 'chunk', 'dash', 'drop', 'lump', 'piece', 'pinch', 'portion', 'splash', 'serving', 'strip', 'sheet', 'slice',
    # Groups
    'amount', 'bunch', 'collection', 'group', 'heap', 'lack', 'load', 'number', 'pair', 'pile', 'quantity', 'series', 'set', 'stack',
    # Containers
    'bag', 'barrel', 'bottle', 'bowl', 'box', 'bucket', 'can', 'carton', 'cup', 'glass', 'jar', 'jug', 'pack', 'packet', 'tube',
    # Measurements
    'foot', 'gallon', 'gram', 'inch', 'kilo', 'kilogram', 'liter', 'litre',
    'meter', 'mile', 'ounce', 'pint', 'pound', 'teaspoon', 'tablespoon',
    # Counting
    'couple', 'dozen', 'handful', 'hundred', 'lot', 'plenty', 'thousand',
    # Kind
    'kind', 'sort', 'type',
}   #TODO what about all and both ?

def _detect_object_candidate(token: Token) -> Token | None:
    """Returns the token if it's a object or even just grammatically object-like"""
    if (token.dep_ == 'conj' and token.head.dep_ in _OBJECT_TAGS):
        # This catches secondary coordinated objects (conjuncts) since only the primary is tagged as object
        # E.g. "I like cats and dogs"
        return token
    if token.dep_ in _OBJECT_TAGS:
        # This catches regular objects
        return token
    return None

def _detect_subject_candidate(token: Token) -> Token | None:
    """Returns the token if it's a subject or even just grammatically subject-like"""
    if (token.dep_ == 'attr' and token.head.lemma_.lower() == 'be'
        and any(child.dep_ == 'expl' for child in token.head.children)
    ):
        # This catches "there is a X" constructs. The expletive "there" is the actual subject
        # but we want "X", which is technically just the predicative attribute
        return token
    if (token.dep_ == 'conj' and token.head.dep_ in SUBJECT_TAGS):
        # This catches secondary coordinated subjects (conjuncts) since only the primary is tagged as subject
        # E.g. "Cats and dogs are enemies"
        return token
    if token.dep_ in SUBJECT_TAGS:
        # This catches regular subjects
        return token
    return None

def _is_excluded_subject_structure(token: Token) -> bool:
    """Determines whether the token is a subject gerund, relative clause, clausal subject or appositonal structure"""
    if token.tag_ == 'VBG' and token.dep_ in SUBJECT_TAGS:
        return True
    if token.head.dep_ == 'relcl' or token.dep_ in {'csubj', 'appos'}:
        return True
    if any(child.dep_ == 'appos' for child in token.children):
        return True
    ancestor = token.head
    while ancestor != ancestor.head:
        if ancestor.dep_ == 'relcl':
            return True
        ancestor = ancestor.head
    return False

def _is_partitive_head(token: Token) -> bool:
    """Returns whether the token is a partitive head with an 'of' child."""
    if token.lemma_.lower() not in _PARTITIVE_HEADS:
        return False
    return any(child.dep_ == 'prep' and child.lower_ == 'of' for child in token.children)


def get_replacement_candidates(doc: Doc) -> list[Token]:
    """Return all tokens that are considered replaceable objects or subjects."""
    candidates = []
    seen = set()    # Used to safeguard against possible duplication of malformed tokens that may qualify as both object or subject
                    # or as multiple instances due to coercion
    for token in doc:
        candidate = _detect_object_candidate(token)
        if not(candidate is None):
            # If it's an object pronoun
            if (not (candidate.pos_ == 'PRON' and candidate.lower_ in _OBJ_PRONOUNS)
                and candidate.i not in seen
                and not _is_partitive_head(candidate)       # For constructs like "a piece of X" only X should be replaceable
            ):
                seen.add(candidate.i)
                candidates.append(candidate)
            continue    # Skips unnecessary subject coercion attempt below (can't be subject if it's object)
        candidate = _detect_subject_candidate(token)
        if not (candidate is None                           # Excludes anything that isn't a subject or subject-like
            or candidate.i in seen
            or (candidate.pos_ == 'PRON'and candidate.lower_ in _SUBJ_PERSONAL_PRONOUNS)      # Excludes personal pronouns
            or candidate.tag_ in {'NNP', 'NNPS'}            # Excludes proper nouns
            or _is_excluded_subject_structure(candidate)    # Excludes some type of subjects that are not meant for replacing
        ):
            seen.add(candidate.i)
            candidates.append(candidate)
    return candidates