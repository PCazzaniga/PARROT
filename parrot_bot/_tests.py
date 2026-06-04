"""
Comprehensive test module for the replacement logic.
"""

from ._replacing import replace_elements, has_replaceable_elements, caches_reset, set_random_seed
from ._nlp_pipeline import get_pipeline

set_random_seed(0)

_ADAPT    = True    # adapt-word mode (keyword adapts to sentence)
_PRESERVE = False   # adapt-sentence mode (sentence adapts to keyword)

_KEYWORD_S = "banana"   # singular keyword
_KEYWORD_P = "bananas"  # plural keyword

_tests = [

    # Basic object replacement
    ("basic singular direct object", "I love this game", _KEYWORD_S, 100, _ADAPT, "I love this banana"),
    ("basic plural direct object, keyword adapts to plural", "I love cats", _KEYWORD_S, 100, _ADAPT, "I love bananas"),
    ("basic plural direct object, sentence adapts to singular keyword", "I love cats", _KEYWORD_S, 100, _PRESERVE, "I love banana"),
    ("prepositional object", "I am thinking about pizza", _KEYWORD_S, 100, _ADAPT, "I am thinking about banana"),
    ("prepositional object plural, keyword adapts to plural", "She is looking at the stars", _KEYWORD_S, 100, _ADAPT, "She is looking at the bananas"),

    # Basic subject replacement
    ("basic singular subject", "A cat is sleeping", _KEYWORD_S, 100, _ADAPT, "A banana is sleeping"),
    ("basic plural subject, keyword adapts to plural", "The dogs are running", _KEYWORD_S, 100, _ADAPT, "The bananas are running"),
    ("basic plural subject, sentence adapts to singular keyword", "The dogs are running", _KEYWORD_S, 100, _PRESERVE, "The banana is running"),
    ("expletive 'there is' construct", "There is a problem", _KEYWORD_S, 100, _ADAPT, "There is a banana"),
    ("expletive 'there are' construct, keyword adapts to plural", "There are some cats", _KEYWORD_S, 100, _ADAPT, "There are some bananas"),

    # Article handling 
    ("indefinite article 'a' stays, no change needed", "I want a cat", _KEYWORD_S, 100, _ADAPT, "I want a banana"),
    ("indefinite article 'a' to 'an', keyword starts with vowel", "I want a cat", "umbrella", 100, _ADAPT, "I want an umbrella"),
    ("indefinite article 'an' to 'a', keyword starts with consonant", "I want an orange", _KEYWORD_S, 100, _ADAPT, "I want a banana"),
    ("definite article 'the' stays singular", "I like the cat", _KEYWORD_S, 100, _ADAPT, "I like the banana"),
    ("definite article 'the' stays plural, keyword adapts to plural", "I like the cats", _KEYWORD_S, 100, _ADAPT, "I like the bananas"),
    ("indefinite article removed before plural keyword, sentence adapts", "I want a rose", _KEYWORD_P, 100, _PRESERVE, "I want bananas"),
    ("indefinite article removed before plural, keyword adapts to singular", "I want a rose", _KEYWORD_S, 100, _ADAPT, "I want a banana"),

    # Demonstrative handling (adapt-word)
    ("'this' stays, keyword adapts to singular", "I want this cookie", _KEYWORD_S, 100, _ADAPT, "I want this banana"),
    ("'these' stays, keyword adapts to plural", "I like these flowers", _KEYWORD_S, 100, _ADAPT, "I like these bananas"),
    ("'that' stays, keyword adapts to singular", "I want that sandwich", _KEYWORD_S, 100, _ADAPT, "I want that banana"),
    ("'those' stays, keyword adapts to plural", "I like those cookies", _KEYWORD_S, 100, _ADAPT, "I like those bananas"),

    # Demonstrative handling (adapt-sentence)
    ("'this' to 'these', sentence adapts to plural keyword", "I want this cookie", _KEYWORD_P, 100, _PRESERVE, "I want these bananas"),
    ("'that' to 'those', sentence adapts to plural keyword", "I want that sandwich", _KEYWORD_P, 100, _PRESERVE, "I want those bananas"),
    ("'these' to 'this', sentence adapts to singular keyword", "I like these flowers", _KEYWORD_S, 100, _PRESERVE, "I like this banana"),
    ("'those' to 'that', sentence adapts to singular keyword", "I like those cookies", _KEYWORD_S, 100, _PRESERVE, "I like that banana"),
    ("coordinated demonstratives, sentence adapts to plural keyword", "I want this cookie and that biscuit", _KEYWORD_P, 100, _PRESERVE, "I want these bananas and those bananas"),

    # Quantifier handling (adapt-word)
    ("'some' stays, keyword adapts to plural", "I want some cats", _KEYWORD_S, 100, _ADAPT, "I want some bananas"),
    ("'many' stays, keyword adapts to plural", "I want many cats", _KEYWORD_S, 100, _ADAPT, "I want many bananas"),
    ("'several' stays, keyword adapts to plural", "I need several apples", _KEYWORD_S, 100, _ADAPT, "I need several bananas"),
    ("'much' stays, keyword adapts to uncountable", "I need much advice", "water", 100, _ADAPT, "I need much water"),

    # Quantifier handling (adapt-sentence)
    ("'some' stays, no change needed with plural keyword", "I want some cats", _KEYWORD_P, 100, _PRESERVE, "I want some bananas"),
    ("'some' to article, sentence adapts to singular keyword", "I want some cats", _KEYWORD_S, 100, _PRESERVE, "I want a banana"),
    ("'many' stays, no change needed with plural keyword", "I want many cats", _KEYWORD_P, 100, _PRESERVE, "I want many bananas"),
    ("'many' to article, sentence adapts to singular keyword", "I want many cats", _KEYWORD_S, 100, _PRESERVE, "I want a banana"),
    ("'several' stays, no change needed with plural keyword", "I need several apples", _KEYWORD_P, 100, _PRESERVE, "I need several bananas"),
    ("'several' to article, sentence adapts to singular keyword", "I need several apples", _KEYWORD_S, 100, _PRESERVE, "I need a banana"),
    ("'much' to 'many', sentence adapts to countable plural keyword", "I need much advice", _KEYWORD_P, 100, _PRESERVE, "I need many bananas"),
    ("'much' to article, sentence adapts to countable singular keyword", "I need much advice", _KEYWORD_S, 100, _PRESERVE, "I need a banana"),
    ("'single' removed, sentence adapts to plural keyword", "I want a single rose", _KEYWORD_P, 100, _PRESERVE, "I want bananas"),

    # Number modifier handling (adapt-sentence)
    ("numeral to article, sentence adapts to singular keyword", "I want three cats", _KEYWORD_S, 100, _PRESERVE, "I want a banana"),
    ("numeral to 'some', sentence adapts to plural keyword", "I want three cats", _KEYWORD_P, 100, _PRESERVE, "I want some bananas"),

    # Verb agreement (adapt-word)
    ("'is' stays, keyword adapts to singular", "The cat is sleeping", _KEYWORD_S, 100, _ADAPT, "The banana is sleeping"),
    ("'are' stays, keyword adapts to plural", "The dogs are barking", _KEYWORD_S, 100, _ADAPT, "The bananas are barking"),
    ("'was' stays, keyword adapts to singular", "The cat was here", _KEYWORD_S, 100, _ADAPT, "The banana was here"),
    ("'were' stays, keyword adapts to plural", "The dogs were loud", _KEYWORD_S, 100, _ADAPT, "The bananas were loud"),
    ("'has' stays, keyword adapts to singular", "The cat has eaten", _KEYWORD_S, 100, _ADAPT, "The banana has eaten"),
    ("'have' stays, keyword adapts to plural", "The dogs have eaten", _KEYWORD_S, 100, _ADAPT, "The bananas have eaten"),
    ("'does' stays, keyword adapts to singular", "The cat does well", _KEYWORD_S, 100, _ADAPT, "The banana does well"),
    ("'do' stays, keyword adapts to plural", "The dogs do well", _KEYWORD_S, 100, _ADAPT, "The bananas do well"),
    ("'runs' stays, keyword adapts to singular", "The cat runs fast", _KEYWORD_S, 100, _ADAPT, "The banana runs fast"),
    ("'run' stays, keyword adapts to plural", "The dogs run fast", _KEYWORD_S, 100, _ADAPT, "The bananas run fast"),

    # Verb agreement (adapt-sentence)
    ("'are' to 'is', sentence adapts to singular keyword", "The dogs are running", _KEYWORD_S, 100, _PRESERVE, "The banana is running"),
    ("'were' to 'was', sentence adapts to singular keyword", "The dogs were loud", _KEYWORD_S, 100, _PRESERVE, "The banana was loud"),
    ("'is' to 'are', sentence adapts to plural keyword", "The cat is sleeping", _KEYWORD_P, 100, _PRESERVE, "The bananas are sleeping"),
    ("'was' to 'were', sentence adapts to plural keyword", "The cat was here", _KEYWORD_P, 100, _PRESERVE, "The bananas were here"),
    ("'have' to 'has', sentence adapts to singular keyword", "The dogs have eaten", _KEYWORD_S, 100, _PRESERVE, "The banana has eaten"),
    ("'has' to 'have', sentence adapts to plural keyword", "The cat has eaten", _KEYWORD_P, 100, _PRESERVE, "The bananas have eaten"),
    ("'do' to 'does', sentence adapts to singular keyword", "The dogs do well", _KEYWORD_S, 100, _PRESERVE, "The banana does well"),
    ("'does' to 'do', sentence adapts to plural keyword", "The cat does well", _KEYWORD_P, 100, _PRESERVE, "The bananas do well"),
    ("'run' to 'runs', sentence adapts to singular keyword", "The dogs run fast", _KEYWORD_S, 100, _PRESERVE, "The banana runs fast"),
    ("'runs' to 'run', sentence adapts to plural keyword", "The cat runs fast", _KEYWORD_P, 100, _PRESERVE, "The bananas run fast"),
    ("coordinated verb agreement, sentence adapts to singular keyword", "The dogs were loud and are annoying", _KEYWORD_S, 100, _PRESERVE, "The banana was loud and is annoying"),

    # Coordination
    ("coordinated objects, keyword adapts to each independently", "I like cats and dogs", _KEYWORD_S, 100, _ADAPT, "I like bananas and bananas"),
    ("coordinated subjects, keyword adapts to each, verb stays plural", "Cats and dogs are enemies", _KEYWORD_S, 100, _ADAPT, "Bananas and bananas are enemies"),

    # Partitive constructs
    ("'piece of X', only X replaced", "I want a piece of cake", _KEYWORD_S, 100, _ADAPT, "I want a piece of banana"),
    ("'cup of X', only X replaced", "I want a cup of coffee", _KEYWORD_S, 100, _ADAPT, "I want a cup of banana"),
    ("'bunch of X', only X replaced, keyword adapts to plural", "I want a bunch of flowers", _KEYWORD_S, 100, _ADAPT, "I want a bunch of bananas"),

    # Indefinite subject pronouns
    ("'everyone' with plural keyword, keyword adapts", "Everyone clapped", _KEYWORD_P, 100, _ADAPT, "Every banana clapped"),
    ("'everyone' with singular keyword, keyword adapts", "Everyone clapped", _KEYWORD_S, 100, _ADAPT, "Every banana clapped"),
    ("'everyone' with plural keyword, sentence adapts", "Everyone clapped", _KEYWORD_P, 100, _PRESERVE, "All bananas clapped"),
    ("'someone' with singular keyword, keyword adapts", "Someone left", _KEYWORD_S, 100, _ADAPT, "Some banana left"),
    ("'nobody' with singular keyword, keyword adapts", "Nobody complained", _KEYWORD_S, 100, _ADAPT, "No banana complained"),

    # Exclusions
    ("gerund clausal subject excluded", "Swimming is fun", _KEYWORD_S, 100, _ADAPT, "Swimming is fun"),
    ("relative clause object excluded", "The cat that I love is gone", _KEYWORD_S, 100, _ADAPT, "The banana that I love is gone"),
    ("proper noun subject excluded", "John likes pizza", _KEYWORD_S, 100, _ADAPT, "John likes banana"),
    ("personal pronoun subject excluded", "I love pizza", _KEYWORD_S, 100, _ADAPT, "I love banana"),
    ("personal pronoun object excluded", "She loves him", _KEYWORD_S, 100, _ADAPT, "She loves him"),

    # Nothing to replace
    ("no replaceable elements, interjection", "haha", _KEYWORD_S, 100, _ADAPT, "haha"),

    # Case matching
    ("lowercase preserved", "I want a cookie", _KEYWORD_S, 100, _ADAPT, "I want a banana"),
    ("uppercase preserved, sentence adapts", "I want some COFFEE", _KEYWORD_S, 100, _PRESERVE, "I want a BANANA"),
    ("capitalization transferred from removed article, sentence adapts", "A cat is sleeping", _KEYWORD_P, 100, _PRESERVE, "Bananas are sleeping"),

]

def _debug_parse(sentence: str):
    doc = get_pipeline()(sentence)
    print(f"       Parse: {sentence}")
    for token in doc:
        print(f"              {token.text:<15} dep={token.dep_:<12} tag={token.tag_:<8} pos={token.pos_:<8} head={token.head.text}")

if __name__ == '__main__':
    passed = 0
    failed = 0
    for description, sentence, keyword, intensity, adapt, expected in _tests:
        caches_reset()
        try:
            if not has_replaceable_elements(sentence, keyword):
                actual = sentence
            else:
                actual = replace_elements(sentence, keyword, intensity, adapt)
        except Exception as e:
            actual = f"ERROR: {e}"
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {description}")
        if not ok:
            print(f"       input:    {sentence}")
            print(f"       keyword:  {keyword} ({'adapt-word' if adapt else 'adapt-sentence'})")
            print(f"       expected: {expected}")
            print(f"       actual:   {actual}")
            doc = get_pipeline()(sentence)
            print(f"       Parse:")
            for token in doc:
                print(f"              {token.text:<15} dep={token.dep_:<12} tag={token.tag_:<8} pos={token.pos_:<8} head={token.head.text}")
    print()
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")