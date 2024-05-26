import os

from taskmates.lib.resources_.resources import load_resource


def print_dir_tree(path, prefix=''):
    """
    Prints the directory tree structure for a given path.
    """
    if not os.path.isdir(path):
        # If the path is not a directory, simply print the file name
        print(prefix + '|  |-- ' + os.path.basename(path))
        return

    # Print the directory name with a heading "|--"
    print(prefix + '|-- ' + os.path.basename(path) + "/")

    # Recursively print the tree structure of each subdirectory
    entries = sorted(os.listdir(path))
    for entry in entries:
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            print_dir_tree(entry_path, prefix=prefix + '|  ')
        else:
            resource = load_resource(entry_path, load_unsupported=True)
            preview = repr(resource)
            if len(preview) > 50:
                preview = preview[:50] + "..."
            print(prefix + '|  |-- ' + entry + f" {preview}")
