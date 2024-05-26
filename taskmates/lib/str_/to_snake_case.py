def to_snake_case(text):
    return '_'.join(word.lower() for word in text.split())
