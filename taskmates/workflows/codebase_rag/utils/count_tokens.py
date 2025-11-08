import tiktoken

TOKENIZER_NAME = "o200k_base"
_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding(TOKENIZER_NAME)
    return _tokenizer


def count_tokens(text: str) -> int:
    """Count tokens in text, with fallback to word count."""
    try:
        tokenizer = get_tokenizer()
        if tokenizer:
            return len(tokenizer.encode(text))
    except Exception:
        pass

    return len(text.split())
