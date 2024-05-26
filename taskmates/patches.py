from json import JSONEncoder

import yaml


def patch_yaml():
    if hasattr(patch_yaml, "_patched"):
        return
    patch_yaml._patched = True

    def str_presenter(dumper, data):
        if data.count('\n') > 0:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.add_representer(str, str_presenter)
    yaml.representer.SafeRepresenter.add_representer(str, str_presenter)

    # def path_dict_presenter(dumper, data):
    #     return dumper.represent_dict(data.dict)
    #
    # from lib.dict_.dot_dict import DotDict
    # yaml.add_representer(DotDict, path_dict_presenter)
    # yaml.representer.SafeRepresenter.add_representer(DotDict, path_dict_presenter)

    def flatten_constructor(loader, node):
        seqs = []
        for item in node.value:
            if isinstance(item, yaml.nodes.SequenceNode):
                seq = loader.construct_sequence(item)
                seqs.extend(seq)
        return seqs

    yaml.add_constructor('!flatten', flatten_constructor, Loader=yaml.FullLoader)
    yaml.add_constructor('!flatten', flatten_constructor, Loader=yaml.SafeLoader)


def install():
    patch_json()
    patch_yaml()


def patch_json():
    if hasattr(patch_json, "_patched"):
        return
    patch_json._patched = True

    def wrapped_default(self, obj):
        return getattr(obj.__class__, "__json__", wrapped_default.default)(obj)

    wrapped_default.default = JSONEncoder().default

    # apply the patch
    JSONEncoder.original_default = JSONEncoder.default
    JSONEncoder.default = wrapped_default
