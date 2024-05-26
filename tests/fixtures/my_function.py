import sys


async def print_and_return():
    print("This is a test message.", flush=True)
    sys.stderr.write("This is a test error message.\n")
    print("Another test message.", flush=True)
    sys.stderr.write("Another test error message.\n")
    return "Test function completed."
