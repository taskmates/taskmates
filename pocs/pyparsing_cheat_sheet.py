from pyparsing import Word, nums

# Define a simple grammar: one or more digits
integer = Word(nums)


# Set a parse action to convert parsed strings to integers
def convert_to_int(tokens):
    return int(tokens[0])


integer.set_parse_action(convert_to_int)


# Add another parse action to multiply the integer by 10
def multiply_by_10(tokens):
    return tokens[0] * 10


integer.add_parse_action(multiply_by_10)


# Add a condition that the integer must be even
def is_even(tokens):
    return tokens[0] % 2 == 0


integer.add_condition(is_even)

# Input string
input_string = "123 456 789"

# parse_string - parses the first occurrence that matches the grammar
try:
    result = integer.parse_string(input_string)
    print("parse_string:", result)
except Exception as e:
    print("parse_string failed:", e)

# scan_string - generator that scans through the string and yields match and location
print("scan_string:")
for tokens, start, end in integer.scan_string(input_string):
    print(f"Matched {tokens} from {start} to {end}")

# search_string - returns a list of all matches found in the string
print("search_string:", integer.search_string(input_string))


# transform_string - transforms the input string by replacing the matches
def replace_with_square(tokens):
    return str(tokens[0] ** 2)


integer.add_parse_action(replace_with_square)
print("transform_string:", integer.transform_string(input_string))
