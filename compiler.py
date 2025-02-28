import sys
import math
import datetime
import os
import random

class DSLCompilerError(Exception):
    def __init__(self, line_number, line_text="", message=""):
        self.line_number = line_number
        self.line_text = line_text
        self.message = message
        super().__init__(f"Compilation error on line {line_number}: '{line_text}' -> {message}")


builtin_funcs = {"length", "type", "integer", "float", "string", "list", "tuple", "dictionary", "set",
                 "abs", "maxof", "minof", "round", "sumof", "range", "enumeratearray", "helpfunction", "directoryof",
                 "uppercase", "lowercase", "concat", "exponent"}


math_funcs_mapping = {
    "sqrt": "sqrt",
    "ceil": "ceil",
    "floor": "floor",
    "mod": "mod",
    "log": "log",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan"
}

def process_condition(condition: str) -> str:
    """Processes conditions by replacing DSL tokens with Python equivalents."""
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
    """Converts DSL text arguments into a quoted string."""
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

def normalize_booleans(tokens):
    """Converts boolean literals to proper Python booleans."""
    return [("True" if tok.lower() == "true" else "False" if tok.lower() == "false" else tok)
            for tok in tokens]

def compile_builtin_expression(tokens):
    """
    Compiles an expression that calls a built-in DSL function.
    Raises DSLCompilerError if the syntax is invalid.
    """
    tokens = normalize_booleans(tokens)
    func_name = tokens[0]
    args_str = " ".join(tokens[1:]).strip()

    
    if func_name == "text":
        if len(tokens) < 2:
            raise Exception("text requires a literal")
        literal = " ".join(tokens[1:])
        return f'"{literal}"'

    
    if func_name in math_funcs_mapping:
        if len(tokens) != 2:
            raise Exception(f"{func_name} function requires one argument")
        python_func_name = math_funcs_mapping[func_name]
        return f"math.{python_func_name}({tokens[1]})"
    elif func_name == "mod":
        args = " ".join(tokens[1:]).split(',')
        if len(args) != 2:
            raise Exception("mod function requires two arguments separated by a comma")
        return f"({args[0].strip()}) % ({args[1].strip()})"
    elif func_name == "log":
        args = " ".join(tokens[1:]).split(',')
        if len(args) != 2:
            raise Exception("log function requires two arguments (number, base) separated by a comma")
        return f"math.log({args[0].strip()}, {args[1].strip()})"
    elif func_name == "substring":
        if tokens[1] == "text":
            if len(tokens) != 7:
                raise Exception("substring with literal requires: substring text <literal> start <start> length <length>")
            text_expr = f'"{tokens[2]}"'
            if tokens[3] != "start" or tokens[5] != "length":
                raise Exception("substring syntax must include 'start' and 'length'")
            start_expr = tokens[4]
            length_expr = tokens[6]
        else:
            if len(tokens) != 6:
                raise Exception("substring with variable requires: substring <variable> start <start> length <length>")
            text_expr = tokens[1]
            if tokens[2] != "start" or tokens[4] != "length":
                raise Exception("substring syntax must include 'start' and 'length'")
            start_expr = tokens[3]
            length_expr = tokens[5]
        return f"({text_expr})[{start_expr}:{start_expr}+{length_expr}]"
    elif func_name == "replace":
        if tokens[1] == "text":
            if len(tokens) != 7:
                raise Exception("replace with literal requires: replace text <literal> old <old> new <new>")
            text_expr = f'"{tokens[2]}"'
            if tokens[3] != "old" or tokens[5] != "new":
                raise Exception("replace syntax must include 'old' and 'new'")
            old_expr = f'"{tokens[4]}"'
            new_expr = f'"{tokens[6]}"'
        else:
            if len(tokens) != 6:
                raise Exception("replace with variable requires: replace <variable> old <old> new <new>")
            text_expr = tokens[1]
            if tokens[2] != "old" or tokens[4] != "new":
                raise Exception("replace syntax must include 'old' and 'new'")
            old_expr = tokens[3]
            new_expr = tokens[5]
        return f"({text_expr}).replace({old_expr}, {new_expr})"
    elif func_name == "split":
        if tokens[1] == "text":
            if len(tokens) != 5:
                raise Exception("split with literal requires: split text <literal> by <separator>")
            text_expr = f'"{tokens[2]}"'
            if tokens[3] != "by":
                raise Exception("split syntax must include 'by'")
            sep_expr = f'"{tokens[4]}"'
        else:
            if len(tokens) != 4:
                raise Exception("split with variable requires: split <variable> by <separator>")
            text_expr = tokens[1]
            if tokens[2] != "by":
                raise Exception("split syntax must include 'by'")
            sep_expr = f'"{tokens[3]}"'
        return f"({text_expr}).split({sep_expr})"
    elif func_name == "join":
        if tokens[1] == "list":
            if len(tokens) != 5:
                raise Exception("join with literal separator requires: join list <list> by <separator>")
            list_expr = tokens[2]
            if tokens[3] != "by":
                raise Exception("join syntax must include 'by'")
            sep_expr = tokens[4] if tokens[4].startswith('"') and tokens[4].endswith('"') else f'"{tokens[4]}"'
        else:
            if len(tokens) != 4:
                raise Exception("join with variable requires: join <list> by <separator>")
            list_expr = tokens[1]
            if tokens[2] != "by":
                raise Exception("join syntax must include 'by'")
            sep_expr = tokens[3] if tokens[3].startswith('"') and tokens[3].endswith('"') else f'"{tokens[3]}"'
        return f"{sep_expr}.join([str(item) for item in {list_expr}])"
    elif func_name == "reverse":
        
        if len(tokens) >= 2 and tokens[1] == "text":
            if len(tokens) != 3:
                raise Exception("reverse text requires: reverse text <literal_or_variable>")
            text_expr = f'"{tokens[2]}"'
            return f'("".join(reversed({text_expr})))'
        elif len(tokens) >= 2 and tokens[1] in {"list", "array"}:
            if len(tokens) != 3:
                raise Exception("reverse list/array requires: reverse list <list> or reverse array <array>")
            list_expr = tokens[2]
            return f"{list_expr}[::-1]"
        elif len(tokens) != 2:
            raise Exception("reverse requires either 'text' or 'list/array' and one argument")
        text_expr = tokens[1]
        return f'("".join(reversed({text_expr})))'
    elif func_name == "append" and tokens[1] in {"list", "array"}:
        if len(tokens) < 4:
            raise Exception("append list/array requires: append list|array <list_or_array> value <value>")
        list_expr = tokens[2]
        if tokens[3] != "value":
            raise Exception("append syntax must include 'value'")
        value_expr = " ".join(tokens[4:])
        return f"{list_expr}.append({value_expr})"
    elif func_name == "remove" and tokens[1] in {"list", "array"}:
        if len(tokens) < 4:
            raise Exception("remove list/array requires: remove list|array <list_or_array> value <value>")
        list_expr = tokens[2]
        if tokens[3] != "value":
            raise Exception("remove syntax must include 'value'")
        value_expr = " ".join(tokens[4:])
        return f"{list_expr}.remove({value_expr})"
    elif func_name == "pop" and tokens[1] in {"list", "array"}:
        if len(tokens) < 4:
            raise Exception("pop list/array requires: pop list|array <list_or_array> index <index>")
        list_expr = tokens[2]
        if tokens[3] != "index":
            raise Exception("pop syntax must include 'index'")
        index_expr = " ".join(tokens[4:])
        return f"{list_expr}.pop({index_expr})"
    elif func_name == "indexof" and tokens[1] in {"list", "array"}:
        if len(tokens) < 4:
            raise Exception("indexof list/array requires: indexof list|array <list_or_array> value <value>")
        list_expr = tokens[2]
        if tokens[3] != "value":
            raise Exception("indexof syntax must include 'value'")
        value_expr = " ".join(tokens[4:])
        return f"{list_expr}.index({value_expr})"
    elif func_name == "countof" and tokens[1] in {"list", "array"}:
        if len(tokens) < 4:
            raise Exception("countof list/array requires: countof list|array <list_or_array> value <value>")
        list_expr = tokens[2]
        if tokens[3] != "value":
            raise Exception("countof syntax must include 'value'")
        value_expr = " ".join(tokens[4:])
        return f"{list_expr}.count({value_expr})"
    elif func_name == "sortlist" and tokens[1] in {"list", "array"}:
        if len(tokens) != 3:
            raise Exception("sortlist list/array requires: sortlist list|array <list_or_array>")
        list_expr = tokens[2]
        return f"{list_expr}.sort()"
    elif func_name == "uniquelist" and tokens[1] in {"list", "array"}:
        if len(tokens) != 3:
            raise Exception("uniquelist list/array requires: uniquelist list|array <list_or_array>")
        list_expr = tokens[2]
        return f"list(dict.fromkeys({list_expr}))"
    elif func_name == "logicalnot":
        if len(tokens) != 2:
            raise Exception("logicalnot function requires one argument")
        return f"not {tokens[1]}"
    elif func_name == "logicaland":
        if len(tokens) != 3:
            raise Exception("logicaland function requires two arguments")
        return f"({tokens[1]}) and ({tokens[2]})"
    elif func_name == "logicalor":
        if len(tokens) != 3:
            raise Exception("logicalor function requires two arguments")
        return f"({tokens[1]}) or ({tokens[2]})"
    elif func_name == "logicalxor":
        if len(tokens) != 3:
            raise Exception("logicalxor function requires two arguments")
        return f"(({tokens[1]}) and (not {tokens[2]})) or ((not {tokens[1]}) and ({tokens[2]}))"
    elif func_name == "keysfromdictionary" and tokens[1] == "dictionary":
        if len(tokens) != 3:
            raise Exception("keysfromdictionary dictionary requires: keys dictionary <dictionary>")
        dict_expr = tokens[2]
        return f"list({dict_expr}.keys())"
    elif func_name == "valuesfromdictionary" and tokens[1] == "dictionary":
        if len(tokens) != 3:
            raise Exception("valuesfromdictionary dictionary requires: values dictionary <dictionary>")
        dict_expr = tokens[2]
        return f"list({dict_expr}.values())"
    elif func_name == "getvaluefromdictionary" and tokens[1] == "dictionary":
        if len(tokens) != 5 or tokens[3] != "key":
            raise Exception("getvaluefromdictionary dictionary requires: getvaluefromdictionary dictionary <dictionary> key <key>")
        dict_expr = tokens[2]
        key_expr = tokens[4]
        return f"{dict_expr}.get({key_expr})"
    elif func_name == "setvalueindictionary" and tokens[1] == "dictionary":
        if len(tokens) < 6 or tokens[3] != "key" or tokens[5] != "value":
            raise Exception("setvalueindictionary dictionary requires: setvalueindictionary dictionary <dictionary> key <key> value <value>")
        dict_expr = tokens[2]
        key_expr = tokens[4]
        value_tokens = tokens[6:]
        
        if value_tokens and value_tokens[0] == "text":
            literal = " ".join(value_tokens[1:])
            value_expr = f'"{literal}"'
        else:
            value_expr = " ".join(value_tokens)
        return f"{dict_expr}[{key_expr}] = {value_expr}"
    elif func_name == "removekeyfromdictionary" and tokens[1] == "dictionary":
        if len(tokens) != 5 or tokens[2] != "key":
            raise Exception("removekeyfromdictionary dictionary requires: removekeyfromdictionary dictionary <dictionary> key <key>")
        dict_expr = tokens[3]
        key_expr = tokens[4]
        return f"del {dict_expr}[{key_expr}]"
    elif func_name == "readfile" and tokens[1] == "file":
        if len(tokens) != 3:
            raise Exception("readfile file requires: read file <path>")
        path_expr = f'"{tokens[2]}"'
        return f'open({path_expr}).read()'
    elif func_name == "writefile" and tokens[1] == "file":
        if len(tokens) < 5 or tokens[3] != "text":
            raise Exception("writefile file requires: write file <path> text <content>")
        path_expr = f'"{tokens[2]}"'
        text_expr = " ".join(tokens[4:])
        return f'open({path_expr}, "w").write("{text_expr}")' 
    elif func_name == "appendfile" and tokens[1] == "file":
        if len(tokens) < 5 or tokens[3] != "text":
            raise Exception("appendfile file requires: append file <path> text <content>")
        path_expr = f'"{tokens[2]}"'
        text_expr = " ".join(tokens[4:])
        return f'open({path_expr}, "a").write("{text_expr}")' 
    elif func_name == "lengthof":
        if len(tokens) != 2:
            raise Exception("lengthof function requires one argument (text or array)")
        return f"len({tokens[1]})"
    elif func_name == "typeof":
        if len(tokens) != 2:
            raise Exception("typeof function requires one argument")
        return f"type({tokens[1]}).__name__"
    elif func_name == "abs":
        if len(tokens) != 2:
            raise Exception("abs function requires one argument")
        return f"abs({tokens[1]})"
    elif func_name == "maxof":
        args = ", ".join(tokens[1:])
        if not args:
            raise Exception("maxof function requires at least one argument")
        return f"max({args})"
    elif func_name == "minof":
        args = ", ".join(tokens[1:])
        if not args:
            raise Exception("minof function requires at least one argument")
        return f"min({args})"
    elif func_name == "round":
        if len(tokens) != 2:
            raise Exception("round function requires one argument")
        return f"round({tokens[1]})"
    elif func_name == "sumof":
        if len(tokens) != 2:
            raise Exception("sumof function requires one argument (array)")
        return f"sum({tokens[1]})"
    elif func_name == "range":
        args = ", ".join(tokens[1:]).split(',')
        if not (1 <= len(args) <= 2):
            raise Exception("range function requires one or two arguments (end) or (start, end)")
        if len(args) == 1:
            return f"list(range({args[0].strip()}))"
        else:
            return f"list(range({args[0].strip()}, {args[1].strip()} + 1))"
    elif func_name == "enumeratearray":
        if len(tokens) != 2:
            raise Exception("enumeratearray function requires one argument (array)")
        return f"list(enumerate({tokens[1]}))"
    elif func_name == "helpfunction":
        if len(tokens) != 2:
            raise Exception("helpfunction requires one argument (function name)")
        return f"help({tokens[1]})"
    elif func_name == "directoryof":
        if len(tokens) != 2:
            raise Exception("directoryof function requires one argument (module name)")
        return f"dir({tokens[1]})"
    elif func_name == "uppercase":
        if len(tokens) != 2:
            raise Exception("uppercase function requires one argument (text)")
        return f"({tokens[1]}).upper()"
    elif func_name == "lowercase":
        if len(tokens) != 2:
            raise Exception("lowercase function requires one argument (text)")
        return f"({tokens[1]}).lower()"
    elif func_name == "concat":
        if len(tokens) < 3:
            raise Exception("concat function requires at least two arguments (texts)")
        args = ", ".join([f"str({arg})" for arg in tokens[1:]])
        return f"('').join([{args}])"
    elif func_name == "exponent":
        if len(tokens) != 3:
            raise Exception("exponent function requires two arguments (base, exponent)")
        return f"({tokens[1]})**({tokens[2]})"
    elif func_name == "clearscreen":
        if len(tokens) != 1:
            raise Exception("clearscreen function does not require any arguments")
        return "os.system('cls' if os.name == 'nt' else 'clear')"
    elif func_name == "exitprogram":
        if len(tokens) != 1:
            raise Exception("exitprogram function does not require any arguments")
        return "sys.exit()"
    elif func_name == "currenttime":
        if len(tokens) != 1:
            raise Exception("currenttime function does not require any arguments")
        return "datetime.datetime.now().strftime('%H:%M:%S')"
    elif func_name == "currentdate":
        if len(tokens) != 1:
            raise Exception("currentdate function does not require any arguments")
        return "datetime.datetime.now().strftime('%Y-%m-%d')"
    elif func_name == "currenttimestamp":
        if len(tokens) != 1:
            raise Exception("currenttimestamp function does not require any arguments")
        return "str(datetime.datetime.now().timestamp())"
    elif func_name == "createtext":
        if len(tokens) < 2:
            raise Exception("createtext function requires at least one argument (text literal)")
        literal = " ".join(tokens[1:])
        return f'"{literal}"'
    elif func_name == "createarray":
        if len(tokens) < 2:
            raise Exception("createarray function requires at least one argument (array elements)")
        elements = ", ".join(tokens[1:])
        return f"[{elements}]"
    elif func_name == "createdictionary":
        if (len(tokens) - 1) % 4 != 0:
            raise DSLCompilerError(0, "", "Syntax error in 'createdictionary': Incorrect number of arguments. Expected key-value pairs like 'key <key> value <value> ...'") 
        dict_pairs = []
        i = 1
        while i < len(tokens):
            if tokens[i] != "key":
                raise DSLCompilerError(0, "", f"Syntax error in 'createdictionary': Expected keyword 'key' at position {i}, but found '{tokens[i]}'. Dictionary key-value pairs must start with 'key'.") 
            key_token = tokens[i+1]
            if tokens[i+2] != "value":
                raise DSLCompilerError(0, "", f"Syntax error in 'createdictionary': Expected keyword 'value' after key '{key_token}' at position {i+2}, but found '{tokens[i+2]}'.") 

            value_tokens = []
            i += 3 

            while i < len(tokens) and tokens[i] not in ["key", "value"]:
                value_tokens.append(tokens[i])
                i += 1

            if not value_tokens:
                raise DSLCompilerError(0, "", f"Syntax error in 'createdictionary': Missing value after 'value' keyword for key '{key_token}'. Each 'value' keyword must be followed by a value expression.") 

            value_expr = compile_builtin_expression(value_tokens) if value_tokens and value_tokens[0] in builtin_funcs else f'"{ " ".join(value_tokens)}"'

            dict_pairs.append(f"'{key_token}': {value_expr}")
            i = i

            if i < len(tokens) and tokens[i] in ["key", "value"]:
                continue
            elif i < len(tokens):
                raise DSLCompilerError(0, "", f"Syntax error in 'createdictionary': Unexpected token after value for key '{key_token}' at position {i}: '{tokens[i]}'. Expected 'key' or 'value' for next pair, or end of dictionary definition.") 

        return "{" + ", ".join(dict_pairs) + "}"

def compile_random_expression(tokens):
    """Compiles a DSL random expression."""
    if tokens[1] == "number":
        if len(tokens) != 5 or tokens[3] != "to":
            raise Exception("random number syntax: random number <min> to <max>")
        return f"random.randint({tokens[2]}, {tokens[4]})"
    elif tokens[1] == "text":
        options = ", ".join([f'"{opt.strip()}"' for opt in " ".join(tokens[2:]).split(',')])
        return f"random.choice([{options}])"
    elif tokens[1] == "boolean":
        if len(tokens) != 2:
            raise Exception("random boolean syntax: random boolean")
        return "random.choice([True, False])"
    else:
        raise Exception(f"Unknown random type: {tokens[1]}. Expected 'number', 'text', or 'boolean'.")

def compile_language(source_code: str) -> str:
    """
    Translates DSL source code into Python code.
    Handles assignments, control structures, built-in function calls, and more.
    """
    output_lines = []
    indent = 0
    random_used = False
    line_number = 0

    
    allowed_types = {"number", "integer", "float", "text", "boolean", "array", "dictionary"}
    
    list_array_funcs = {"append", "remove", "pop", "indexof", "countof", "sortlist", "uniquelist", "reverse"}
    dict_funcs = {"keysfromdictionary", "valuesfromdictionary", "getvaluefromdictionary", "setvalueindictionary", "removekeyfromdictionary"}
    bool_funcs = {"logicalnot", "logicaland", "logicalor", "logicalxor"}
    math_funcs = {"sqrt", "ceil", "floor", "mod", "log", "sin", "cos", "tan"}
    file_funcs = {"readfile", "writefile", "appendfile"}
    screen_funcs = {"clearscreen", "exitprogram"}
    type_funcs = {"lengthof", "typeof", "integer", "float", "string", "list", "tuple", "dictionary", "set"}
    aggregate_funcs = {"abs", "maxof", "minof", "round", "sumof", "range", "enumeratearray", "helpfunction", "directoryof", "uppercase", "lowercase", "concat", "exponent"}
    create_funcs = {"createtext", "createarray", "createdictionary"}

    all_builtin_funcs = set.union(builtin_funcs, list_array_funcs, dict_funcs, bool_funcs, math_funcs,
                                  file_funcs, screen_funcs, type_funcs, aggregate_funcs, create_funcs)

    for line in source_code.splitlines():
        line_number += 1
        original_line = line.rstrip("\n")
        
        line = line.split("#", 1)[0].rstrip()
        stripped_line = line.strip()
        if not stripped_line:
            continue

        tokens = stripped_line.split()
        try:
            
            if "[" in stripped_line and "]" in stripped_line and "=" in stripped_line and not stripped_line.startswith("storage"):
                lhs, rhs = stripped_line.split("=", 1)
                lhs = lhs.strip()
                rhs_tokens = rhs.split()
                if rhs_tokens and rhs_tokens[0] in {"text"}:
                    rhs_expr = compile_builtin_expression(rhs_tokens)
                else:
                    rhs_expr = " ".join(normalize_booleans(rhs_tokens))
                output_lines.append("    " * indent + f"{lhs} = {rhs_expr}")
                continue
            
            elif "=" in stripped_line and not stripped_line.startswith("storage") and \
                 not stripped_line.startswith("if ") and not stripped_line.startswith("while ") and \
                 not stripped_line.startswith("for ") and not stripped_line.startswith("print "):
                lhs, rhs = stripped_line.split("=", 1)
                lhs = lhs.strip()
                rhs_tokens = rhs.split()
                rhs_expr = " ".join(normalize_booleans(rhs_tokens))
                output_lines.append("    " * indent + f"{lhs} = {rhs_expr}")
                continue

            if stripped_line.lower() == "end program":
                output_lines.append("    " * indent + "sys.exit()")
                continue

            if stripped_line.lower() == "end":
                indent -= 1
                if indent < 0:
                    raise DSLCompilerError(line_number, original_line, "Unmatched 'end' statement")
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
                if len(tokens) == 1 and tokens[0] in {"currenttime", "currentdate", "currenttimestamp"}:
                    output_code = f"print({compile_builtin_expression(tokens)})"
                elif len(tokens) == 1:
                    output_code = f"print({expr})"
                elif tokens[0] == "text":
                    literal = " ".join(tokens[1:]).strip()
                    if (literal.startswith('"') and literal.endswith('"')) or (literal.startswith("'") and literal.endswith("'")):
                        output_code = f"print({literal})"
                    else:
                        output_code = f'print("{literal}")'
                elif tokens[0] == "storage":
                    var_name = " ".join(tokens[1:])
                    if not var_name:
                        raise DSLCompilerError(line_number, original_line, "Missing variable name in print command.")
                    output_code = f"print({var_name})"
                elif tokens[0] == "random":
                    expr_compiled = compile_random_expression(tokens)
                    random_used = True
                    output_code = f"print({expr_compiled})"
                elif tokens[0] in all_builtin_funcs:
                    expr_compiled = compile_builtin_expression(tokens)
                    output_code = f"print({expr_compiled})"
                else:
                    output_code = f"print({expr})"
                output_lines.append("    " * indent + output_code)
                continue

            
            
            if stripped_line.startswith("storage"):
                parts = stripped_line[len("storage"):].strip().split()
                if len(parts) < 3:
                    raise DSLCompilerError(line_number, original_line, "Incomplete 'storage' command. Expected: 'storage <type> <variable> = <value>'") 
                if parts[0].lower() not in allowed_types:
                    allowed_types_str = ", ".join(allowed_types)
                    raise DSLCompilerError(line_number, original_line, f"Invalid storage type '{parts[0]}'. Allowed types are: {allowed_types_str}. Please use one of these types to declare storage.") 
                typ = parts[0].lower()
                var_name = parts[1]
                if not var_name.isidentifier():
                    raise DSLCompilerError(line_number, original_line, f"Invalid variable name '{var_name}'. Variable names must be valid Python identifiers (start with a letter or underscore, followed by letters, numbers, or underscores).") 
                if parts[2] != "=":
                    raise DSLCompilerError(line_number, original_line, "Syntax error in 'storage' command: Missing '='.  The correct format is 'storage <type> <variable> = <value>'. Ensure there's an equals sign after the variable name.") 
                expression_tokens = parts[3:]
                if not expression_tokens:
                    raise DSLCompilerError(line_number, original_line, "Missing value expression after '=' in 'storage' command. You need to assign a value to the variable. For example: 'storage number myVar = 10'.") 
                arithmetic_operators = {"+", "-", "*", "/", "%"}
                if any(tok in arithmetic_operators for tok in expression_tokens):
                    norm_tokens = normalize_booleans(expression_tokens)
                    value_expr = " ".join(norm_tokens)
                elif expression_tokens[0] in {"random", "text"}:
                    if expression_tokens[0] == "random":
                        value_expr = compile_random_expression(expression_tokens)
                        random_used = True
                    elif expression_tokens[0] == "text": 
                        literal = " ".join(expression_tokens[1:]).strip()
                        value_expr = f'"{literal}"' 
                    else: 
                        value_expr = " ".join(expression_tokens) 
                elif expression_tokens[0] in all_builtin_funcs:
                    value_expr = compile_builtin_expression(expression_tokens)
                else:
                    norm_tokens = normalize_booleans(expression_tokens)
                    value_expr = " ".join(norm_tokens)
                    if typ == "text" and not (value_expr.startswith('"') or value_expr.startswith("'")):
                        value_expr = f'"{value_expr}"'
                    elif typ == "boolean":
                        if value_expr.lower() == "true":
                            value_expr = "True"
                        elif value_expr.lower() == "false":
                            value_expr = "False"
                        else:
                            raise DSLCompilerError(line_number, original_line, f"Invalid boolean value: '{value_expr}'. For boolean storage, use 'true' or 'false'.") 
                if typ == "float":
                    value_expr = f"float({value_expr})"
                elif typ in {"number", "integer"}:
                    value_expr = f"int({value_expr})"
                output_code = f"{var_name} = {value_expr}"
                output_lines.append("    " * indent + output_code)
                continue

            
            tokens = stripped_line.split()
            if tokens:
                first_token = tokens[0]
                second_token = tokens[1] if len(tokens) > 1 else None

                if second_token in list_array_funcs:
                    expr_tokens = [second_token, "array", first_token] + tokens[2:]
                    expr_compiled = compile_builtin_expression(expr_tokens)
                    output_lines.append("    " * indent + expr_compiled)
                    continue
                elif first_token in list_array_funcs:
                    expr_compiled = compile_builtin_expression(tokens)
                    output_lines.append("    " * indent + expr_compiled)
                    continue
                elif first_token in all_builtin_funcs:
                    expr_compiled = compile_builtin_expression(tokens)
                    output_lines.append("    " * indent + expr_compiled)
                    continue
                elif first_token == "clear":
                    if second_token == "screen":
                        output_lines.append("    " * indent + compile_builtin_expression(["clearscreen"]))
                        continue
                    else:
                        raise DSLCompilerError(line_number, original_line, f"Unknown command: '{stripped_line}'. Did you mean 'clear screen'?")
                elif first_token == "exit":
                    if second_token == "program":
                        output_lines.append("    " * indent + compile_builtin_expression(["exitprogram"]))
                        continue
                    else:
                        raise DSLCompilerError(line_number, original_line, f"Unknown command: '{stripped_line}'. Did you mean 'exit program'?")
                else:
                    raise DSLCompilerError(line_number, original_line, f"Unknown command: '{stripped_line}'")
            else:
                continue

        except DSLCompilerError as dce:
            raise dce
        except Exception as e:
            raise DSLCompilerError(line_number, original_line, str(e))

    if indent != 0:
        raise DSLCompilerError(line_number, "", "Unclosed block statements detected. Some blocks are not properly terminated with 'end'.")
    
    header_lines = ["import math", "import sys", "import datetime", "import os"]
    if random_used:
        header_lines.append("import random")
    output_lines = header_lines + output_lines
    return "\n".join(output_lines)

def compile_file(input_file_path):
    """Reads a DSL file, compiles it to Python code, and executes it."""
    try:
        with open(input_file_path, 'r') as f:
            source_code = f.read()
        compiled_code = compile_language(source_code)
        
        
        
        
        exec(compiled_code)
        print(f"Execution of '{input_file_path}' successful.")
    except DSLCompilerError as e:
        print(e)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compiler.py <input_file.easy>")
        sys.exit(1)
    input_file_path = sys.argv[1]
    compile_file(input_file_path)
