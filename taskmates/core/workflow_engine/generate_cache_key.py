import hashlib
import json
from typing import Dict, Any


def generate_cache_key(outcome: str, inputs: Dict[str, Any]) -> str:
    """Generate a cache key from outcome and inputs."""
    sorted_inputs = json.dumps(inputs, sort_keys=True)
    hash_value = hashlib.sha256(sorted_inputs.encode()).hexdigest()
    return f"{outcome}/{hash_value}"
