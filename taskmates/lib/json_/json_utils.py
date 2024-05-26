import json
import inflection


def camel_to_snake(key):
    return inflection.underscore(key)


def snake_to_camel(key):
    return inflection.camelize(key, False)


def convert_keys(data, conversion_function):
    if isinstance(data, list):
        return [convert_keys(item, conversion_function) for item in data]
    elif isinstance(data, dict):
        return {conversion_function(key): convert_keys(value, conversion_function) for key, value in data.items()}
    else:
        return data


def snake_case(dct):
    return convert_keys(dct, camel_to_snake)


def camel_case(dct):
    return convert_keys(dct, snake_to_camel)


# Example JSON data
json_data = '''
{
    "firstName": "John",
    "lastName": "Doe",
    "address": {
        "streetName": "Main Street",
        "streetNumber": 123
    },
    "phoneNumbers": [
        {
            "type": "home",
            "number": "555-555-1234"
        },
        {
            "type": "work",
            "number": "555-555-5678"
        }
    ]
}
'''

if __name__ == "__main__":
    # Load JSON data as a Python object
    data = json.loads(json_data)

    # Convert keys to snake_case
    snake_case_data = convert_keys(data, camel_to_snake)
    print(json.dumps(snake_case_data, indent=2, ensure_ascii=False))

    # Convert keys back to camelCase
    camel_case_data = convert_keys(snake_case_data, snake_to_camel)
    print(json.dumps(camel_case_data, indent=2, ensure_ascii=False))
