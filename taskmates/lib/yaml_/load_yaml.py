import yaml



def load_yaml(yaml_str):
    result = yaml.safe_load(yaml_str)
    return result
