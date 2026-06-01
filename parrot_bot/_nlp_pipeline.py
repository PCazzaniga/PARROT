"""
Module that handles the NLP pipeline.

Functions:
    ensure_pipeline_loaded():   Makes sure the NLP pipeline is loaded
    get_pipeline():             Returns the NLP pipeline
"""

import spacy

_NLP_PIPELINE = None                        # Natural language parser, lazily populated at first use

def ensure_pipeline_loaded() -> None:
    """Loads the NLP pipeline if it was not yet so."""
    global _NLP_PIPELINE
    if _NLP_PIPELINE is None:
        _NLP_PIPELINE = spacy.load('en_core_web_sm', disable=['ner', 'textcat'])

def get_pipeline():
    """Returns the NLP pipeline"""
    ensure_pipeline_loaded()
    return _NLP_PIPELINE