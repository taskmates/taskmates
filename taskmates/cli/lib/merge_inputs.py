from typeguard import typechecked


@typechecked
def merge_inputs(inputs: list[dict]) -> dict:
    merged = {}
    for params in inputs:
        merged.update(params)
    return merged
