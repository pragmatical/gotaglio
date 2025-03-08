from pyparsing import Word, alphas, alphanums, oneOf, infixNotation, opAssoc

def evaluate_boolean_expression(expression, variables):
    # Define grammar
    initial_chars = alphas + "_"
    body_chars = alphanums + "_-"
    variable = Word(initial_chars, body_chars)  # Matches variable names like A, B, _, A1, A-1, etc.

    # variable = Word(alphas)  # Matches variable names like A, B, etc.
    operand = variable.setParseAction(lambda t: variables[t[0]])  # Replace variable with its boolean value

    # Define operators
    AND = "&&"
    OR = "||"
    NOT = "!"
    boolean_expr = infixNotation(
        operand,
        [
            (NOT, 1, opAssoc.RIGHT, lambda t: not t[0][1]),
            (AND, 2, opAssoc.LEFT, lambda t: t[0][0] and t[0][2]),
            (OR, 2, opAssoc.LEFT, lambda t: t[0][0] or t[0][2]),
        ],
    )

    # Parse and evaluate the expression
    return boolean_expr.parseString(expression)[0]

# # Example usage
# if __name__ == "__main__":
#     variables = {
#         "A": True,
#         "B": False,
#         "C": True,
#     }

#     expressions = [
#         "A && B",       # False
#         "A || B",       # True
#         "!A || B",      # False
#         "A && !B",      # True
#         "(A || B) && C" # True
#     ]

#     for (k,y) in variables.items():
#         print(f"{k} = {y}")
#     print()
#     for expr in expressions:
#         result = evaluate_boolean_expression(expr, variables)
#         print(f"{expr} => {result}")
