def snake_case_action(_text, _loc, toks):
    return toks[0].lower().strip().replace(" ", "_")
