import sys
import random

class DSLCompilerError(Exception):
    def __init__(self, line_number, line_text, message):
        self.line_number = line_number
        self.line_text = line_text
        self.message = message
        super().__init__(f"Compilation error on line {line_number}: '{line_text}' -> {message}")

builtin_funcs = {"len", "type", "int", "float", "str", "list", "tuple", "dict", "set",
                 "abs", "max", "min", "round", "sum", "range", "enumerate", "help", "dir",
                 "upper", "lower", "concat", "pow"}

def process_condition(condition: str) -> str:
    tokens = condition.split()
    processed_tokens = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "text":
            if i + 1 < len(tokens):
                processed_tokens.append(f'"{tokens[i+1]}"')
                i += 2
            else:
                raise Exception("Expected literal after 'text' in condition")
        elif token.lower() == "true":
            processed_tokens.append("True")
            i += 1
        elif token.lower() == "false":
            processed_tokens.append("False")
            i += 1
        else:
            processed_tokens.append(token)
            i += 1
    return " ".join(processed_tokens)

def process_text_in_args(args_str: str) -> str:
    tokens = args_str.split()
    result = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "text" and i + 1 < len(tokens):
            result.append(f'"{tokens[i+1]}"')
            i += 2
        else:
            result.append(tokens[i])
            i += 1
    return " ".join(result)

def compile_builtin_expression(tokens):
    func_name = tokens[0]
    args_str = " ".join(tokens[1:]).strip()
    if func_name == "upper":
        if not args_str:
            raise Exception("upper function requires one argument")
        args_str = process_text_in_args(args_str)
        return f"str({args_str}).upper()"
    elif func_name == "lower":
        if not args_str:
            raise Exception("lower function requires one argument")
        args_str = process_text_in_args(args_str)
        return f"str({args_str}).lower()"
    elif func_name == "concat":
        if not args_str:
            raise Exception("concat function requires at least one argument")
        parts = [part.strip() for part in args_str.split(',')]
        processed_parts = []
        for part in parts:
            processed_parts.append(process_text_in_args(part))
        return " + ".join(processed_parts)
    elif func_name == "pow":
        args = [arg.strip() for arg in args_str.split(',')]
        if len(args) != 2:
            raise Exception("pow function requires two arguments (base, exponent)")
        return f"pow({args[0]}, {args[1]})"
    elif func_name in builtin_funcs:
        args_str = process_text_in_args(args_str)
        return f"{func_name}({args_str})"
    else:
        raise Exception(f"Unknown function: {func_name}")

def compile_random_expression(tokens):
    if len(tokens) < 2:
        raise Exception("Invalid random expression: missing type specification")
    rtype = tokens[1]
    if rtype == "number":
        if len(tokens) != 5 or tokens[3] != "to":
            raise Exception("Invalid random number syntax. Expected: random number <min> to <max>")
        try:
            min_val = int(tokens[2])
            max_val = int(tokens[4])
        except ValueError:
            raise Exception("Random number values must be integers")
        return f"random.randint({min_val}, {max_val})"
    elif rtype == "text":
        rest = " ".join(tokens[2:])
        options = [opt.strip() for opt in rest.split(",") if opt.strip()]
        if not options:
            raise Exception("Invalid random text syntax. Provide comma-separated options")
        options_expr = ", ".join(f'"{opt}"' for opt in options)
        return f"random.choice([{options_expr}])"
    elif rtype == "boolean":
        return "random.choice([True, False])"
    else:
        raise Exception("Unknown random type: " + rtype)

def compile_language(source_code: str) -> str:
    output_lines = []
    indent = 0
    random_used = False
    line_number = 0

    for line in source_code.splitlines():
        line_number += 1
        original_line = line.rstrip("\n")
        # Remove any inline comments.
        line = line.split("#", 1)[0].rstrip()
        stripped_line = line.strip()
        if not stripped_line:
            continue

        try:
            if stripped_line.lower() == "end program":
                output_lines.append("    " * indent + "sys.exit()")
                continue

            if stripped_line.lower() == "end":
                indent -= 1
                if indent < 0:
                    raise DSLCompilerError(line_number, original_line, "Unmatched 'end' statement: too many 'end' statements encountered.")
                continue

            if stripped_line.startswith("if "):
                condition_line = stripped_line[3:].rstrip()
                if condition_line.endswith(":"):
                    condition_line = condition_line[:-1].rstrip()
                if not condition_line:
                    raise DSLCompilerError(line_number, original_line, "Missing condition in if statement.")
                if condition_line.endswith(" is true"):
                    condition_expr = condition_line[:-len(" is true")].strip()
                    if not condition_expr:
                        raise DSLCompilerError(line_number, original_line, "Empty condition before 'is true'.")
                    compiled_line = f"if {condition_expr}:"
                elif condition_line.endswith(" is false"):
                    condition_expr = condition_line[:-len(" is false")].strip()
                    if not condition_expr:
                        raise DSLCompilerError(line_number, original_line, "Empty condition before 'is false'.")
                    compiled_line = f"if not ({condition_expr}):"
                else:
                    compiled_line = f"if {condition_line}:"
                output_lines.append("    " * indent + compiled_line)
                indent += 1
                continue

            if stripped_line.startswith("while "):
                loop_line = stripped_line[6:].rstrip()
                if loop_line.endswith(" do"):
                    loop_line = loop_line[:-3].rstrip()
                if not loop_line:
                    raise DSLCompilerError(line_number, original_line, "Missing condition in while loop.")
                compiled_line = f"while {loop_line}:"
                output_lines.append("    " * indent + compiled_line)
                indent += 1
                continue

            if stripped_line.startswith("for "):
                tokens = stripped_line.split()
                if len(tokens) != 5 or tokens[2] != "to" or tokens[4] != "do":
                    raise DSLCompilerError(line_number, original_line, "Invalid for loop syntax. Expected: for <start> to <end> do")
                start_val = tokens[1]
                end_val = tokens[3]
                if not start_val or not end_val:
                    raise DSLCompilerError(line_number, original_line, "Missing start or end value in for loop.")
                compiled_line = f"for i in range({start_val}, {end_val} + 1):"
                output_lines.append("    " * indent + compiled_line)
                indent += 1
                continue

            if stripped_line.startswith("print"):
                expr = stripped_line[len("print"):].strip()
                if not expr:
                    raise DSLCompilerError(line_number, original_line, "Missing expression in print command.")
                tokens = expr.split()
                if not tokens:
                    raise DSLCompilerError(line_number, original_line, "Empty expression after print command.")
                if tokens[0] == "random":
                    expr_compiled = compile_random_expression(tokens)
                    random_used = True
                    output_code = f"print({expr_compiled})"
                elif tokens[0] in builtin_funcs:
                    expr_compiled = compile_builtin_expression(tokens)
                    output_code = f"print({expr_compiled})"
                elif tokens[0] == "text":
                    literal = " ".join(tokens[1:])
                    if not literal:
                        raise DSLCompilerError(line_number, original_line, "Empty text literal in print command.")
                    output_code = f'print("{literal}")'
                elif tokens[0] == "storage":
                    var_name = " ".join(tokens[1:])
                    if not var_name:
                        raise DSLCompilerError(line_number, original_line, "Missing variable name in print command.")
                    output_code = f"print({var_name})"
                else:
                    output_code = f"print({expr})"
                output_lines.append("    " * indent + output_code)
                continue

            if stripped_line.startswith("storage"):
                parts = stripped_line[len("storage"):].strip().split()
                if len(parts) < 3:
                    raise DSLCompilerError(line_number, original_line, "Invalid storage command syntax. Expected: storage <type> <variable> = <value>")
                type_allowed = {"number", "int", "float", "text", "boolean"}
                if parts[0].lower() not in type_allowed:
                    raise DSLCompilerError(line_number, original_line, f"Unknown storage type '{parts[0]}'. Allowed types: {', '.join(type_allowed)}")
                typ = parts[0].lower()
                var_name = parts[1]
                if parts[2] != "=":
                    raise DSLCompilerError(line_number, original_line, "Missing '=' in storage command. Expected format: storage <type> <variable> = <value>")
                expression_tokens = parts[3:]
                if not expression_tokens:
                    raise DSLCompilerError(line_number, original_line, "Missing value in storage command.")
                if len(expression_tokens) == 1 and expression_tokens[0] in builtin_funcs:
                    value_expr = compile_builtin_expression(expression_tokens)
                elif expression_tokens[0] == "random":
                    value_expr = compile_random_expression(expression_tokens)
                    random_used = True
                elif expression_tokens[0] == "text" and len(expression_tokens) > 1:
                    literal = " ".join(expression_tokens[1:])
                    if not literal:
                        raise DSLCompilerError(line_number, original_line, "Empty text literal in storage command.")
                    value_expr = f'"{literal}"'
                else:
                    value_expr = " ".join(expression_tokens)
                    if typ == "text" and not (value_expr.startswith('"') or value_expr.startswith("'")):
                        value_expr = f'"{value_expr}"'
                    elif typ == "boolean":
                        if value_expr.lower() == "true":
                            value_expr = "True"
                        elif value_expr.lower() == "false":
                            value_expr = "False"
                        else:
                            raise DSLCompilerError(line_number, original_line, f"Invalid boolean value: {value_expr}")
                if typ == "float":
                    value_expr = f"float({value_expr})"
                elif typ in {"number", "int"}:
                    value_expr = f"int({value_expr})"
                output_code = f"{var_name} = {value_expr}"
                output_lines.append("    " * indent + output_code)
                continue

            raise DSLCompilerError(line_number, original_line, f"Unknown command: '{stripped_line}'")
        except DSLCompilerError as dce:
            raise dce
        except Exception as e:
            raise DSLCompilerError(line_number, original_line, str(e))

    if indent != 0:
        raise DSLCompilerError(line_number, "", "Unclosed block statements detected. Some blocks are not properly terminated with 'end'.")
    output_lines.insert(0, "import sys")
    if random_used:
        output_lines.insert(1, "import random")
    return "\n".join(output_lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file>")
        sys.exit(1)
    file_path = sys.argv[1]
    try:
        with open(file_path, "r") as f:
            source_code = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    try:
        compiled_code = compile_language(source_code)
        exec_globals = {"random": random, "sys": sys}
        exec(compiled_code, exec_globals)
    except DSLCompilerError as e:
        print(e)
    except Exception as e:
        print(f"Compilation error: {e}")

if __name__ == "__main__":
    main()
