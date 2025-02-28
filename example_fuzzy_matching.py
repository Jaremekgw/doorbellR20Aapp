from rapidfuzz import process

"""
    Example of app
    App for approximate string matching. For instance,
    Python’s difflib or RapidFuzz (an updated fork of fuzzywuzzy)
    can score how “close” a recognized string is to a list of known commands.

    solution 2:
    Use lemmatization or morphological analysis
    Polish inflection can cause issues (lampę/lampy/lampa).
    A morphological analyzer or a simpler approach that removes/normalizes
    typical inflectional endings might help:

    Tools like Morfeusz 2 or spaCy’s Polish model can help parse “lampę,” “lampy,” “lampa”
    all down to the lemma “lampa.”
    After you get lemmas, you do your matching on the canonical form.

"""

TURN_ON_VARIANTS = ["załącz lampę", "włącz lampę", "zapal lampę", 
                    "załącz światło", "włącz światło", "zapal światło",
                    "załącz lampy",  "włącz lampy",  "zapal lampy"]

def get_best_match(command: str, variants: list, threshold=80):
    best_match, score, _ = process.extractOne(command, variants)
    if score >= threshold:
        return best_match
    return None


