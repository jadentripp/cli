import tiktoken
from functools import lru_cache
from typing import List, Dict, Any

MODEL = "gpt-4o-mini"

@lru_cache(maxsize=1)
def get_encoding():
    return tiktoken.encoding_for_model(MODEL)

def tokenize(text: str) -> List[int]:
    return get_encoding().encode(text)

def num_tokens_from_messages(messages: List[Dict[str, Any]], model: str = MODEL) -> int:
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = get_encoding()
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    except Exception:
        return 0  # Return 0 if there's an error in token counting