from pyparsing import Word, nums, oneOf, infixNotation, opAssoc

# Define basic elements
integer = Word(nums)
operand = integer.setParseAction(lambda t: int(t[0]))

# Define arithmetic operators
plus = oneOf("+")
minus = oneOf("-")
mult = oneOf("*")
div = oneOf("/")

# Define the grammar for arithmetic expressions
expr = infixNotation(operand, [
    (mult | div, 2, opAssoc.LEFT),
    (plus | minus, 2, opAssoc.LEFT),
])

# Function to evaluate the parsed expression
def evaluate_expression(parsed):
    if isinstance(parsed, int):
        return parsed
    elif len(parsed) == 3:
        left, op, right = parsed
        if op == '+':
            return evaluate_expression(left) + evaluate_expression(right)
        elif op == '-':
            return evaluate_expression(left) - evaluate_expression(right)
        elif op == '*':
            return evaluate_expression(left) * evaluate_expression(right)
        elif op == '/':
            return evaluate_expression(left) / evaluate_expression(right)

# Example usage
expression = "3 + 5 * (2 - 8)"
parsed_expr = expr.parseString(expression, parseAll=True)[0]
result = evaluate_expression(parsed_expr)

print(f"Expression: {expression}")
print(f"Parsed: {parsed_expr}")
print(f"Result: {result}")
