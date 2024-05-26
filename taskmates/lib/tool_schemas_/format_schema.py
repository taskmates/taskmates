import dpath
import jsonref


def jsonref_to_dict(json_ref_obj):
    if isinstance(json_ref_obj, dict):
        return {k: jsonref_to_dict(v) for k, v in dict(json_ref_obj).items()}
    elif isinstance(json_ref_obj, list):
        return [jsonref_to_dict(v) for v in json_ref_obj]
    else:
        return json_ref_obj


def format_schema(schema):
    schema = schema.copy()
    schema = jsonref_to_dict(jsonref.replace_refs(schema, lazy_load=False))
    dpath.delete(schema, '**/title')
    if 'definitions' in schema:
        del schema['definitions']

    required = []

    for name, value in schema['properties'].items():
        if 'default' not in value:
            required.append(name)

    if required:
        schema['required'] = required

    return schema
