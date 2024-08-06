def merge_template_params(template_params: list) -> dict:
    merged = {}
    for params in template_params:
        merged.update(params)
    return merged
