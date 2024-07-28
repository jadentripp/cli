import tiktoken
from functools import lru_cache
from typing import List

MODEL = "gpt-4o-mini"

@lru_cache(maxsize=1)
def get_encoding():
    return tiktoken.encoding_for_model(MODEL)

def tokenize(text: str) -> List[int]:
    return get_encoding().encode(text)