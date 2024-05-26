import hashlib
import json


def get_digest(value):
    digest = hashlib.sha1(json.dumps(value, ensure_ascii=False).encode()).hexdigest()
    return digest
