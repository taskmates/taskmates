def is_binary_file(filename):
    try:
        with open(filename, 'r') as f:
            f.read()
    except UnicodeDecodeError:
        return True
