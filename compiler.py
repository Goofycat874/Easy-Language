"""Easy Language v3.0 — A beginner-friendly programming language that compiles to Python."""

import argparse
import datetime
import difflib
import math
import os
import random
import re
import shlex
import sys
import time as _time_mod
from pathlib import Path
from typing import Any

VERSION = "3.1.0"

# ─── Color helpers (ANSI) ────────────────────────────────────────────────────

_COLOR_SUPPORT = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR_SUPPORT else text

def _red(text: str) -> str:
    return _c("1;31", text)


def _yellow(text: str) -> str:
    return _c("1;33", text)


def _cyan(text: str) -> str:
    return _c("36", text)


def _dim(text: str) -> str:
    return _c("2", text)


def _bold(text: str) -> str:
    return _c("1", text)

# ─── Error classes ────────────────────────────────────────────────────────────

KNOWN_KEYWORDS = [
    "if", "else", "elif", "end", "stop", "while", "for", "foreach", "repeat",
    "print", "say", "let", "variable", "input", "sleep", "wait", "assert", "function",
    "return", "try", "catch", "check", "error", "do", "number", "text", "boolean", "float",
    "integer", "array", "dictionary", "storage", "clear", "exit",
]

def _suggest(word: str) -> str | None:
    matches = difflib.get_close_matches(word, KNOWN_KEYWORDS, n=1, cutoff=0.6)
    return matches[0] if matches else None

class EasyError(Exception):
    """Rich compile-time error with context."""
    def __init__(self, line_num: int, line_text: str = "", message: str = "", suggestion: str | None = None):
        self.line_num = line_num
        self.line_text = line_text
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"Line {line_num}: {message}")


def format_error(err: EasyError, source: str, filename: str) -> str:
    """Produce a beautiful, colorized error message with context lines."""
    lines = source.splitlines()
    ln = err.line_num
    parts: list[str] = []

    parts.append(_red(f"✗ Error in {filename}, line {ln}"))
    parts.append("")

    for i in range(max(1, ln - 1), min(len(lines) + 1, ln + 2)):
        prefix = _red("▸") if i == ln else " "
        num = f"{i:>4} │"
        if i == ln:
            parts.append(f"  {prefix} {_bold(num)} {_red(lines[i-1] if i <= len(lines) else '')}")
        else:
            parts.append(f"  {prefix} {_dim(num)} {_dim(lines[i-1] if i <= len(lines) else '')}")

    parts.append("")
    parts.append(f"  {_red(err.message)}")

    hint = err.suggestion
    if not hint and err.line_text:
        tokens = err.line_text.strip().split()
        if tokens:
            hint_word = _suggest(tokens[0])
            if hint_word:
                hint = f"Did you mean '{hint_word}'?"
    if hint:
        parts.append(f"  {_yellow('💡 ' + hint)}")

    return "\n".join(parts)


# ─── Constants ────────────────────────────────────────────────────────────────

ALLOWED_TYPES = {"number", "integer", "float", "text", "boolean", "array", "dictionary"}

LIST_FUNCS = {"append", "remove", "pop", "indexof", "countof", "sortlist", "uniquelist", "reverse"}
DICT_FUNCS = {"keys", "values", "get", "set", "removekey",
              "keysfromdictionary", "valuesfromdictionary", "getvaluefromdictionary",
              "setvalueindictionary", "removekeyfromdictionary"}
BOOL_FUNCS = {"logicalnot", "logicaland", "logicalor", "logicalxor"}
MATH_FUNCS = {"sqrt", "ceil", "floor", "sin", "cos", "tan"}
FILE_FUNCS = {"readfile", "writefile", "appendfile"}
TYPE_FUNCS = {"length", "len", "typeof", "lengthof", "integer", "float", "string", "list", "tuple", "dictionary", "set"}
AGG_FUNCS = {"abs", "maxof", "minof", "round", "sumof", "range", "enumeratearray", "helpfunction", "directoryof", "exponent", "max", "min", "sum"}
TEXT_FUNCS = {"substring", "replace", "split", "join", "uppercase", "lowercase", "concat", "createtext", "upper", "lower", "trim"}
CREATE_FUNCS = {"createarray", "createdictionary"}
SPECIAL_FUNCS = {"text", "mod", "log", "clearscreen", "exitprogram", "currenttime", "currentdate", "currenttimestamp", "clear", "exit"}

ALL_BUILTINS = set().union(
    LIST_FUNCS, DICT_FUNCS, BOOL_FUNCS, MATH_FUNCS, FILE_FUNCS,
    TYPE_FUNCS, AGG_FUNCS, TEXT_FUNCS, CREATE_FUNCS, SPECIAL_FUNCS,
)

EXPR_OPS = {"+", "-", "*", "/", "%", "//", "**", "<", ">", "<=", ">=", "==", "!=", "and", "or", "not"}
LITERAL_KW = {"true", "false", "none"}
COMPOUND_OPS = {"+=", "-=", "*=", "/="}

# English word → operator mappings (applied during preprocessing)
WORD_OPS = {
    "plus": "+", "minus": "-", "times": "*",
    "modulo": "%", "power": "**",
}

STARTER_TEMPLATE = '''# Easy Language v3.1 — Starter
# Run with: python compiler.py run {filename}

# --- Variables ---
variable greeting is "Hello from Easy Language!"
say Welcome to Easy Language!
print greeting

# --- Numbers & conditions ---
variable age is 20
if age >= 18 then
    say You are an adult
else
    say You are a minor
stop

# --- Math with words ---
variable x is 10
variable y is x plus 5
print y

# --- Loops ---
repeat 3 times
    print random number 1 to 10
stop

# --- Functions ---
function greet(name) then
    say Hello there,
    print name
stop

greet("World")

# --- Error handling ---
check then
    variable bad is 100 / 0
error e then
    say Oops, something went wrong!
    print e
stop

print currentdate
print currenttime
'''


# ─── Tokenizer & helpers ─────────────────────────────────────────────────────

def strip_comment(line: str) -> str:
    in_sq = in_dq = escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif ch in ("#",) and not in_sq and not in_dq:
            return line[:i]
        elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_sq and not in_dq:
            return line[:i]
    return line


def preprocess_line(line: str) -> str:
    """Translate English-like syntax into the compiler's core syntax.

    Transformations (applied left-to-right on the stripped line):
      stop           → end
      variable x is  → let x =
      check          → try
      error          → catch
      then (at end)  → :
      plus/minus/times/divided by → +/-/*/÷
    """
    s = line

    # --- stop → end ---
    lo = s.strip().lower()
    if lo == "stop" or lo == "stop program":
        return s.replace(s.strip(), "end" if lo == "stop" else "end program", 1)

    # --- variable ... is ... → let ... = ... ---
    stripped = s.strip()
    indent_ws = s[:len(s) - len(s.lstrip())]  # preserve indentation
    lo_stripped = stripped.lower()

    if lo_stripped.startswith("variable "):
        rest = stripped[len("variable "):]
        # Find 'is' used as assignment (not inside quotes)
        # We only replace the FIRST 'is' that is surrounded by spaces
        parts = rest.split(None)
        if len(parts) >= 3 and parts[1].lower() == "is":
            var_name = parts[0]
            value = rest.split(None, 2)[2]  # everything after 'variable name is'
            s = f"{indent_ws}let {var_name} = {value}"
        elif len(parts) >= 1:
            # variable name (no 'is'), treat as let
            s = f"{indent_ws}let {rest}"

    # --- check → try ---
    stripped = s.strip()
    lo_stripped = stripped.lower()
    if lo_stripped in ("check", "check:", "check then"):
        s = s[:len(s) - len(s.lstrip())] + "try:"

    # --- error → catch ---
    if lo_stripped.startswith("error ") or lo_stripped in ("error", "error:"):
        inner = stripped[len("error"):].strip().rstrip(":").strip()
        # Remove trailing 'then' if present
        if inner.lower().endswith(" then"):
            inner = inner[:-5].strip()
        elif inner.lower() == "then":
            inner = ""
        if inner:
            s = s[:len(s) - len(s.lstrip())] + f"catch {inner}:"
        else:
            s = s[:len(s) - len(s.lstrip())] + "catch:"

    # --- 'then' at end of line → ':' ---
    stripped = s.strip()
    if stripped.lower().endswith(" then") and not stripped.lower().startswith(("say ", "print ")):
        s = s[:len(s) - len(s.lstrip())] + stripped[:-4].rstrip() + ":"

    # --- 'divided by' → '/' ---
    # Do this before word ops to avoid partial matches
    s_check = s.lower()
    if " divided by " in s_check:
        # Case-insensitive replace while preserving structure
        idx = s_check.find(" divided by ")
        s = s[:idx] + " / " + s[idx + len(" divided by "):]

    # --- Word operators: plus→+, minus→-, times→*, etc. ---
    # Skip word-op replacement for say/print (text) and repeat (uses 'times' keyword)
    lo_check = s.strip().lower()
    skip_word_ops = lo_check.startswith(("say ", "repeat "))
    if not skip_word_ops:
        for word, op in WORD_OPS.items():
            parts = []
            in_sq = in_dq = False
            i = 0
            while i < len(s):
                ch = s[i]
                if ch == '"' and not in_sq: in_dq = not in_dq
                elif ch == "'" and not in_dq: in_sq = not in_sq
                if not in_sq and not in_dq:
                    before_ok = (i == 0 or s[i-1] == ' ')
                    end_i = i + len(word)
                    after_ok = (end_i >= len(s) or s[end_i] == ' ')
                    if before_ok and after_ok and s[i:end_i].lower() == word:
                        parts.append(op)
                        i = end_i
                        continue
                parts.append(ch)
                i += 1
            s = "".join(parts)

    return s


def tokenize(line: str) -> list[str]:
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        return line.split()


def norm_bools(tokens: list[str]) -> list[str]:
    return ["True" if t.lower() == "true" else "False" if t.lower() == "false" else t for t in tokens]


def join_tok(tokens: list[str]) -> str:
    return " ".join(tokens)


def is_quoted(s: str) -> bool:
    s = s.strip()
    return len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]


def is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def interpolate_string(s: str) -> str:
    """Convert {var} inside a string to f-string syntax."""
    if "{" in s and "}" in s:
        return "f" + repr(s).replace("{", "{").replace("\\{", "{")
    return repr(s)


def apply_interpolation(raw: str) -> str:
    """If a string has {var} patterns, produce an f-string."""
    if re.search(r'\{[a-zA-Z_]\w*\}', raw):
        return 'f"' + raw.replace('"', '\\"') + '"'
    return repr(raw)


# ─── Builtin expression compiler ─────────────────────────────────────────────

def compile_random(tokens: list[str]) -> str:
    if len(tokens) < 2:
        raise Exception("random needs a type: number, text, or boolean")
    if tokens[1] == "number":
        if len(tokens) != 5 or tokens[3] != "to":
            raise Exception("Syntax: random number <min> to <max>")
        return f"random.randint({tokens[2]}, {tokens[4]})"
    if tokens[1] == "text":
        raw = join_tok(tokens[2:])
        opts = [o.strip() for o in raw.split(",") if o.strip()]
        if not opts:
            raise Exception("random text needs at least one option")
        return f"random.choice([{', '.join(repr(o) for o in opts)}])"
    if tokens[1] == "boolean":
        return "random.choice([True, False])"
    raise Exception(f"Unknown random type '{tokens[1]}'. Use number, text, or boolean.")


def _two_args(tokens: list[str], name: str) -> tuple[str, str]:
    raw = join_tok(tokens)
    parts = [p.strip() for p in raw.split(",") if p.strip()] if "," in raw else [p.strip() for p in tokens if p.strip()]
    if len(parts) != 2:
        raise Exception(f"{name} requires exactly 2 arguments")
    return parts[0], parts[1]


def compile_builtin(tokens: list[str]) -> str:
    tokens = norm_bools(tokens)
    fn = tokens[0]

    # ── Aliases ──
    if fn == "length" or fn == "len" or fn == "lengthof":
        if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
        return f"len({tokens[1]})"
    if fn == "typeof":
        if len(tokens) != 2: raise Exception("typeof requires one argument")
        return f"type({tokens[1]}).__name__"
    if fn in ("upper", "uppercase"):
        if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
        return f"({tokens[1]}).upper()"
    if fn in ("lower", "lowercase"):
        if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
        return f"({tokens[1]}).lower()"
    if fn == "trim":
        if len(tokens) != 2: raise Exception("trim requires one argument")
        return f"({tokens[1]}).strip()"
    if fn == "text":
        if len(tokens) < 2: raise Exception("text requires a literal")
        return repr(join_tok(tokens[1:]))
    if fn in MATH_FUNCS:
        if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
        return f"math.{fn}({tokens[1]})"
    if fn == "mod":
        a, b = _two_args(tokens[1:], "mod")
        return f"({a}) % ({b})"
    if fn == "log":
        a, b = _two_args(tokens[1:], "log")
        return f"math.log({a}, {b})"

    # ── Substring ──
    if fn == "substring":
        if len(tokens) == 7 and tokens[1] == "text" and tokens[3] == "start" and tokens[5] == "length":
            return f"({repr(tokens[2])})[{tokens[4]}:{tokens[4]}+{tokens[6]}]"
        if len(tokens) == 6 and tokens[2] == "start" and tokens[4] == "length":
            return f"({tokens[1]})[{tokens[3]}:{tokens[3]}+{tokens[5]}]"
        raise Exception("substring syntax: substring <text> start <n> length <n>")

    # ── Replace ──
    if fn == "replace":
        if len(tokens) == 7 and tokens[1] == "text" and tokens[3] == "old" and tokens[5] == "new":
            return f"({repr(tokens[2])}).replace({repr(tokens[4])}, {repr(tokens[6])})"
        if len(tokens) == 6 and tokens[2] == "old" and tokens[4] == "new":
            return f"({tokens[1]}).replace({repr(tokens[3])}, {repr(tokens[5])})"
        raise Exception("replace syntax: replace <text> old <old> new <new>")

    # ── Split / Join ──
    if fn == "split":
        if len(tokens) == 5 and tokens[1] == "text" and tokens[3] == "by":
            return f"({repr(tokens[2])}).split({repr(tokens[4])})"
        if len(tokens) == 4 and tokens[2] == "by":
            return f"({tokens[1]}).split({repr(tokens[3])})"
        raise Exception("split syntax: split <text> by <sep>")
    if fn == "join":
        if len(tokens) >= 4 and tokens[-2] == "by":
            lst = tokens[2] if tokens[1] in ("list", "array") else tokens[1]
            sep = repr(tokens[-1])
            return f"{sep}.join([str(i) for i in {lst}])"
        raise Exception("join syntax: join <list> by <sep>")

    # ── Reverse ──
    if fn == "reverse":
        if len(tokens) == 3 and tokens[1] == "text": return f"''.join(reversed({repr(tokens[2])}))"
        if len(tokens) == 3 and tokens[1] in ("list", "array"): return f"{tokens[2]}[::-1]"
        if len(tokens) == 2: return f"''.join(reversed({tokens[1]}))"
        raise Exception("reverse syntax: reverse text <val> | reverse list <var> | reverse <var>")

    # ── List ops ──
    if fn == "append" and len(tokens) >= 5 and tokens[1] in ("list", "array") and tokens[3] == "value":
        return f"{tokens[2]}.append({join_tok(tokens[4:])})"
    if fn == "remove" and len(tokens) >= 5 and tokens[1] in ("list", "array") and tokens[3] == "value":
        return f"{tokens[2]}.remove({join_tok(tokens[4:])})"
    if fn == "pop" and len(tokens) >= 5 and tokens[1] in ("list", "array") and tokens[3] == "index":
        return f"{tokens[2]}.pop({join_tok(tokens[4:])})"
    if fn == "indexof" and len(tokens) >= 5 and tokens[1] in ("list", "array") and tokens[3] == "value":
        return f"{tokens[2]}.index({join_tok(tokens[4:])})"
    if fn == "countof" and len(tokens) >= 5 and tokens[1] in ("list", "array") and tokens[3] == "value":
        return f"{tokens[2]}.count({join_tok(tokens[4:])})"
    if fn == "sortlist" and len(tokens) == 3 and tokens[1] in ("list", "array"):
        return f"{tokens[2]}.sort()"
    if fn == "uniquelist" and len(tokens) == 3 and tokens[1] in ("list", "array"):
        return f"list(dict.fromkeys({tokens[2]}))"

    # ── Boolean logic ──
    if fn == "logicalnot":
        if len(tokens) != 2: raise Exception("logicalnot requires one argument")
        return f"not ({tokens[1]})"
    if fn == "logicaland":
        if len(tokens) != 3: raise Exception("logicaland requires two arguments")
        return f"({tokens[1]}) and ({tokens[2]})"
    if fn == "logicalor":
        if len(tokens) != 3: raise Exception("logicalor requires two arguments")
        return f"({tokens[1]}) or ({tokens[2]})"
    if fn == "logicalxor":
        if len(tokens) != 3: raise Exception("logicalxor requires two arguments")
        return f"(({tokens[1]}) and (not {tokens[2]})) or ((not {tokens[1]}) and ({tokens[2]}))"

    # ── Dict ops (new short names + legacy) ──
    if fn in ("keys", "keysfromdictionary"):
        if len(tokens) == 3 and tokens[1] in ("dictionary", "dict"): return f"list({tokens[2]}.keys())"
        if len(tokens) == 2: return f"list({tokens[1]}.keys())"
        raise Exception(f"{fn} syntax: {fn} <dict>")
    if fn in ("values", "valuesfromdictionary"):
        if len(tokens) == 3 and tokens[1] in ("dictionary", "dict"): return f"list({tokens[2]}.values())"
        if len(tokens) == 2: return f"list({tokens[1]}.values())"
        raise Exception(f"{fn} syntax: {fn} <dict>")
    if fn in ("get", "getvaluefromdictionary"):
        if len(tokens) == 5 and tokens[1] in ("dictionary", "dict") and tokens[3] == "key":
            return f"{tokens[2]}.get({tokens[4]})"
        if len(tokens) == 3: return f"{tokens[1]}.get({tokens[2]})"
        raise Exception(f"{fn} syntax: {fn} <dict> <key>")
    if fn in ("set", "setvalueindictionary"):
        if len(tokens) >= 7 and tokens[1] in ("dictionary", "dict") and tokens[3] == "key" and tokens[5] == "value":
            vt = tokens[6:]
            ve = repr(join_tok(vt[1:])) if vt[0] == "text" else compile_builtin(vt) if vt[0] in ALL_BUILTINS else join_tok(vt)
            return f"{tokens[2]}[{tokens[4]}] = {ve}"
        raise Exception(f"{fn} syntax: {fn} dict <d> key <k> value <v>")
    if fn in ("removekey", "removekeyfromdictionary"):
        if len(tokens) == 5 and tokens[1] in ("dictionary", "dict") and tokens[3] == "key":
            return f"del {tokens[2]}[{tokens[4]}]"
        if len(tokens) == 3: return f"del {tokens[1]}[{tokens[2]}]"
        raise Exception(f"{fn} syntax: {fn} <dict> <key>")

    # ── File I/O ──
    if fn == "readfile" and len(tokens) == 3 and tokens[1] == "file":
        return f"open({repr(tokens[2])}, 'r', encoding='utf-8').read()"
    if fn == "writefile" and len(tokens) >= 5 and tokens[1] == "file" and tokens[3] == "text":
        return f"open({repr(tokens[2])}, 'w', encoding='utf-8').write({repr(join_tok(tokens[4:]))})"
    if fn == "appendfile" and len(tokens) >= 5 and tokens[1] == "file" and tokens[3] == "text":
        return f"open({repr(tokens[2])}, 'a', encoding='utf-8').write({repr(join_tok(tokens[4:]))})"

    # ── Type conversions ──
    for cast_fn, py_fn in [("integer", "int"), ("float", "float"), ("string", "str"), ("list", "list"), ("tuple", "tuple"), ("dictionary", "dict"), ("set", "set")]:
        if fn == cast_fn:
            if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
            return f"{py_fn}({tokens[1]})"

    # ── Aggregates ──
    if fn == "abs":
        if len(tokens) != 2: raise Exception("abs requires one argument")
        return f"abs({tokens[1]})"
    if fn in ("maxof", "max"):
        if len(tokens) < 2: raise Exception(f"{fn} requires at least one argument")
        return f"max({', '.join(tokens[1:])})"
    if fn in ("minof", "min"):
        if len(tokens) < 2: raise Exception(f"{fn} requires at least one argument")
        return f"min({', '.join(tokens[1:])})"
    if fn == "round":
        if len(tokens) != 2: raise Exception("round requires one argument")
        return f"round({tokens[1]})"
    if fn in ("sumof", "sum"):
        if len(tokens) != 2: raise Exception(f"{fn} requires one argument")
        return f"sum({tokens[1]})"
    if fn == "range":
        args = [p.strip() for p in ",".join(tokens[1:]).split(",") if p.strip()]
        if len(args) == 1: return f"list(range({args[0]}))"
        if len(args) == 2: return f"list(range({args[0]}, {args[1]} + 1))"
        raise Exception("range requires one or two arguments")
    if fn == "enumeratearray":
        if len(tokens) != 2: raise Exception("enumeratearray requires one argument")
        return f"list(enumerate({tokens[1]}))"
    if fn == "exponent":
        if len(tokens) != 3: raise Exception("exponent requires two arguments")
        return f"({tokens[1]})**({tokens[2]})"
    if fn == "helpfunction":
        if len(tokens) != 2: raise Exception("helpfunction requires one argument")
        return f"help({tokens[1]})"
    if fn == "directoryof":
        if len(tokens) != 2: raise Exception("directoryof requires one argument")
        return f"dir({tokens[1]})"

    # ── String creation ──
    if fn == "concat":
        if len(tokens) < 3: raise Exception("concat requires at least two arguments")
        return f"''.join([{', '.join(f'str({a})' for a in tokens[1:])}])"
    if fn == "createtext":
        if len(tokens) < 2: raise Exception("createtext requires at least one argument")
        return repr(join_tok(tokens[1:]))
    if fn == "createarray":
        if len(tokens) < 2: raise Exception("createarray requires at least one element")
        elems = []
        for t in tokens[1:]:
            if is_numeric(t) or t.lower() in ("true", "false", "none") or t.isidentifier():
                elems.append(t)
            else:
                elems.append(repr(t))
        return f"[{', '.join(elems)}]"

    # ── createdictionary ──
    if fn == "createdictionary":
        i, pairs = 1, []
        while i < len(tokens):
            if tokens[i] != "key": raise Exception("createdictionary: expected 'key <k> value <v>' pairs")
            if i + 1 >= len(tokens): raise Exception("createdictionary: missing key name")
            key = tokens[i + 1]; i += 2
            if i >= len(tokens) or tokens[i] != "value": raise Exception(f"createdictionary: key '{key}' missing 'value'")
            i += 1; vt = []
            while i < len(tokens) and tokens[i] != "key": vt.append(tokens[i]); i += 1
            if not vt: raise Exception(f"createdictionary: key '{key}' missing a value")
            ve = repr(join_tok(vt[1:])) if vt[0] == "text" else compile_builtin(vt) if vt[0] in ALL_BUILTINS else repr(join_tok(vt))
            pairs.append(f"{repr(key)}: {ve}")
        if not pairs: raise Exception("createdictionary requires at least one key/value pair")
        return "{" + ", ".join(pairs) + "}"

    # ── Special ──
    if fn in ("clearscreen", "clear"):
        return "os.system('cls' if os.name == 'nt' else 'clear')"
    if fn in ("exitprogram", "exit"):
        return "sys.exit()"
    if fn == "currenttime":
        return "datetime.datetime.now().strftime('%H:%M:%S')"
    if fn == "currentdate":
        return "datetime.datetime.now().strftime('%Y-%m-%d')"
    if fn == "currenttimestamp":
        return "str(datetime.datetime.now().timestamp())"

    raise Exception(f"Unknown function: '{fn}'")


# ─── Condition compiler ──────────────────────────────────────────────────────

def compile_cond(cond_line: str) -> str:
    line = cond_line.rstrip()

    if line.endswith(":"):
        line = line[:-1].rstrip()

    if line.endswith(" is true"):
        line = line[:-len(" is true")].strip()
    elif line.endswith(" is false"):
        expr = line[:-len(" is false")].strip()
        if not expr:
            raise Exception("Empty condition before 'is false'")
        return f"not ({expr})"

    if not line:
        raise Exception("Missing condition")

    return line


# ─── Input compiler ──────────────────────────────────────────────────────────

def compile_input(tokens: list[str]) -> tuple[str, bool, str]:
    if len(tokens) < 2:
        raise Exception("input syntax: input [type] <variable> [prompt text <message>]")
    typed = None
    idx = 1
    if tokens[idx] in ("number", "integer", "float", "text", "boolean"):
        typed = tokens[idx]; idx += 1
    if idx >= len(tokens):
        raise Exception("input: missing variable name")
    var = tokens[idx]
    if not var.isidentifier():
        raise Exception(f"Invalid variable name '{var}'")
    idx += 1
    prompt = repr("")
    if idx < len(tokens):
        if tokens[idx] != "prompt":
            raise Exception("input: use 'prompt' before the message")
        pt = tokens[idx + 1:]
        if not pt:
            raise Exception("input prompt: missing text")
        ptxt = join_tok(pt[1:]) if pt[0] == "text" else join_tok(pt)
        if ptxt and not ptxt.endswith(" "):
            ptxt += " "
        prompt = repr(ptxt)
    raw = f"input({prompt})"
    helper = False
    if typed in ("number", "integer"):
        val = f"int({raw})"
    elif typed == "float":
        val = f"float({raw})"
    elif typed == "boolean":
        val = f"_dsl_parse_boolean({raw})"
        helper = True
    else:
        val = raw
    return f"{var} = {val}", helper, var


# ─── Assignment helpers ───────────────────────────────────────────────────────

def should_keep_expr(toks: list[str], known: set[str], raw: str = "") -> bool:
    if any(t in EXPR_OPS for t in toks):
        return True
    if any(t in known for t in toks):
        return True
    # Check the raw string for structural patterns (brackets, parens, function calls)
    raw_s = raw.strip()
    if raw_s and (raw_s.startswith(("[", "{", "(")) or "(" in raw_s or ")" in raw_s):
        return True
    if len(toks) != 1:
        return False
    t = toks[0]
    lo = t.lower()
    if lo in LITERAL_KW:
        return True
    if is_numeric(t):
        return True
    if t.startswith(("[", "{", "(")) or "(" in t or ")" in t:
        return True
    return False


def compile_assign(lhs: str, rhs_raw: str, rhs_tok: list[str], rand_used: bool, known: set[str], unquoted_text: bool = False) -> tuple[str, bool]:
    if not rhs_tok: raise Exception("Assignment is missing a value")
    if is_quoted(rhs_raw):
        rhs = rhs_raw
        if re.search(r'\{[a-zA-Z_]\w*\}', rhs_raw[1:-1]):
            rhs = "f" + rhs_raw
    elif rhs_tok[0] == "random":
        rhs = compile_random(rhs_tok); rand_used = True
    elif rhs_tok[0] in ALL_BUILTINS:
        rhs = compile_builtin(rhs_tok)
    else:
        nt = norm_bools(rhs_tok)
        raw_s = rhs_raw.strip()
        # If the raw RHS has brackets/parens, use raw string to preserve quotes
        if raw_s.startswith(("[", "{", "(")) or ("(" in raw_s and ")" in raw_s):
            rhs = rhs_raw
        elif should_keep_expr(rhs_tok, known, rhs_raw): rhs = join_tok(nt)
        elif unquoted_text: rhs = repr(join_tok(rhs_tok))
        else: rhs = join_tok(nt)
    return f"{lhs} = {rhs}", rand_used


def compile_typed_assign(typ: str, var: str, raw: str, toks: list[str], rand_used: bool) -> tuple[str, bool]:
    if not toks: raise Exception("Typed assignment is missing a value")
    if is_quoted(raw): ve = raw
    elif toks[0] == "random": ve = compile_random(toks); rand_used = True
    elif toks[0] == "text": ve = repr(join_tok(toks[1:]))
    elif toks[0] in ALL_BUILTINS: ve = compile_builtin(toks)
    else:
        ve = join_tok(norm_bools(toks))
        if typ == "text" and len(toks) == 1 and toks[0].isidentifier(): ve = toks[0]
        elif typ == "text": ve = repr(join_tok(toks))
    if typ == "float": ve = f"float({ve})"
    elif typ in ("number", "integer"): ve = f"int({ve})"
    elif typ == "boolean":
        lo = ve.lower()
        if lo == "true": ve = "True"
        elif lo == "false": ve = "False"
        elif any(t in EXPR_OPS for t in toks) or toks[0] in BOOL_FUNCS: ve = f"bool({ve})"
        elif toks[0] != "random": raise Exception("boolean accepts true/false or boolean expressions")
    return f"{var} = {ve}", rand_used


# ─── Main compiler ───────────────────────────────────────────────────────────

def compile_language(source: str) -> str:
    out: list[str] = []
    indent = 0
    ln = 0
    rand_used = time_used = bool_helper = False
    known: set[str] = set()
    user_funcs: set[str] = set()
    ind = lambda: "    " * indent

    for raw in source.splitlines():
        ln += 1
        code = strip_comment(raw.rstrip("\n")).rstrip()
        code = preprocess_line(code)  # English-like syntax → core syntax
        s = code.strip()
        if not s: continue
        tokens = tokenize(s)
        if not tokens: continue

        try:
            lo = s.lower()

            # ── end / stop program ──
            if lo in ("end program", "stop program"):
                out.append(ind() + "sys.exit()"); continue

            # ── end / stop ──
            if lo in ("end", "stop"):
                indent -= 1
                if indent < 0: raise EasyError(ln, raw, "Unmatched 'stop' — there's no open block to close.", "Make sure every if/while/for/function/check has a matching 'stop'.")
                continue

            # ── else if / elif ──
            if lo.startswith("else if ") or lo.startswith("elif "):
                if indent <= 0: raise EasyError(ln, raw, "'else if' must come after an if block.")
                start = 8 if lo.startswith("else if ") else 5
                cond = compile_cond(s[start:])
                indent -= 1; out.append(ind() + f"elif {cond}:"); indent += 1; continue

            # ── else ──
            if lo in ("else", "else:"):
                if indent <= 0: raise EasyError(ln, raw, "'else' must come after an if/elif block.")
                indent -= 1; out.append(ind() + "else:"); indent += 1; continue

            # ── if ──
            if s.startswith("if "):
                cond = compile_cond(s[3:])
                out.append(ind() + f"if {cond}:"); indent += 1; continue

            # ── while ──
            if s.startswith("while "):
                wl = s[6:].rstrip()
                if wl.endswith(" do"): wl = wl[:-3].rstrip()
                out.append(ind() + f"while {compile_cond(wl)}:"); indent += 1; continue

            # ── do...while ──
            if lo in ("do", "do:"):
                out.append(ind() + "while True:"); indent += 1; continue

            # ── for ──
            if s.startswith("for "):
                if len(tokens) != 5 or tokens[2] != "to" or tokens[4] != "do":
                    raise EasyError(ln, raw, "for syntax: for <start> to <end> do", "Example: for 1 to 10 do")
                out.append(ind() + f"for i in range({tokens[1]}, {tokens[3]} + 1):"); known.add("i"); indent += 1; continue

            # ── foreach ──
            if tokens[0] == "foreach":
                if len(tokens) < 4 or tokens[2] != "in":
                    raise EasyError(ln, raw, "foreach syntax: foreach <item> in <collection>:", "Example: foreach x in myList:")
                item = tokens[1]; collection = tokens[3].rstrip(":")
                out.append(ind() + f"for {item} in {collection}:"); known.add(item); indent += 1; continue

            # ── repeat ──
            if tokens[0] == "repeat":
                if len(tokens) not in (3, 4) or tokens[2] != "times":
                    raise EasyError(ln, raw, "repeat syntax: repeat <count> times", "Example: repeat 5 times")
                out.append(ind() + f"for _ in range(int({tokens[1]})):"); indent += 1; continue

            # ── function ──
            if tokens[0] == "function":
                if len(tokens) < 2:
                    raise EasyError(ln, raw, "function syntax: function name(args):", "Example: function greet(name):")
                sig = s[len("function"):].strip().rstrip(":")
                # Parse name and params
                if "(" in sig:
                    name = sig[:sig.index("(")].strip()
                    params = sig[sig.index("("):]
                else:
                    name = sig.strip()
                    params = "()"
                if not name.isidentifier():
                    raise EasyError(ln, raw, f"Invalid function name '{name}'.")
                out.append(ind() + f"def {name}{params}:"); user_funcs.add(name); indent += 1; continue

            # ── return ──
            if tokens[0] == "return":
                if len(tokens) == 1:
                    out.append(ind() + "return"); continue
                expr = s[len("return"):].strip()
                out.append(ind() + f"return {expr}"); continue

            # ── try ──
            if lo in ("try", "try:"):
                out.append(ind() + "try:"); indent += 1; continue

            # ── catch ──
            if lo.startswith("catch"):
                if indent <= 0: raise EasyError(ln, raw, "'catch' must come after a try block.")
                indent -= 1
                parts = s.split(None, 1)
                err_var = parts[1].rstrip(":") if len(parts) > 1 else "e"
                if err_var and err_var != ":":
                    out.append(ind() + f"except Exception as {err_var}:"); known.add(err_var)
                else:
                    out.append(ind() + "except Exception as _err:")
                indent += 1; continue

            # ── print ──
            if tokens[0] == "print":
                expr_raw = s[len("print"):].strip()
                et = tokens[1:]
                if not et: raise EasyError(ln, raw, "print needs something to print!", "Example: print \"Hello\" or print myVar")
                if is_quoted(expr_raw):
                    if re.search(r'\{[a-zA-Z_]\w*\}', expr_raw[1:-1]):
                        oc = f"print(f{expr_raw})"
                    else:
                        oc = f"print({expr_raw})"
                elif len(et) == 1 and et[0] in ("currenttime", "currentdate", "currenttimestamp"):
                    oc = f"print({compile_builtin(et)})"
                elif et[0] == "text":
                    oc = f"print({repr(join_tok(et[1:]))})"
                elif et[0] == "storage":
                    v = join_tok(et[1:]).strip()
                    if not v: raise EasyError(ln, raw, "print storage requires a variable name")
                    oc = f"print({v})"
                elif et[0] == "random":
                    oc = f"print({compile_random(et)})"; rand_used = True
                elif et[0] in ALL_BUILTINS:
                    oc = f"print({compile_builtin(et)})"
                else:
                    oc = f"print({join_tok(norm_bools(et))})"
                out.append(ind() + oc); continue

            # ── say ──
            if tokens[0] == "say":
                lit = s[len("say"):].strip()
                if not lit: raise EasyError(ln, raw, "say needs text to print!", "Example: say Hello World")
                if is_quoted(lit):
                    if re.search(r'\{[a-zA-Z_]\w*\}', lit[1:-1]):
                        out.append(ind() + f"print(f{lit})")
                    else:
                        out.append(ind() + f"print({lit})")
                else:
                    if re.search(r'\{[a-zA-Z_]\w*\}', lit):
                        out.append(ind() + f'print(f"{lit}")')
                    else:
                        out.append(ind() + f"print({repr(lit)})")
                continue

            # ── storage (legacy) ──
            if tokens[0] == "storage":
                if len(tokens) < 5: raise EasyError(ln, raw, "storage syntax: storage <type> <name> = <value>", "Tip: Use simpler syntax instead: let name = value")
                typ = tokens[1].lower(); var = tokens[2]
                if typ not in ALLOWED_TYPES: raise EasyError(ln, raw, f"Unknown type '{typ}'. Allowed: {', '.join(sorted(ALLOWED_TYPES))}")
                if not var.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{var}'.")
                if tokens[3] != "=": raise EasyError(ln, raw, "Missing '=' in storage command.")
                er = s.split("=", 1)[1].strip(); et = tokens[4:]
                al, rand_used = compile_typed_assign(typ, var, er, et, rand_used)
                out.append(ind() + al); known.add(var); continue

            # ── typed shorthand: number x = 5 ──
            if tokens[0] in ALLOWED_TYPES and len(tokens) >= 4 and tokens[2] == "=":
                typ = tokens[0].lower(); var = tokens[1]
                if not var.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{var}'.")
                er = s.split("=", 1)[1].strip(); et = tokens[3:]
                al, rand_used = compile_typed_assign(typ, var, er, et, rand_used)
                out.append(ind() + al); known.add(var); continue

            # ── let ──
            if tokens[0] == "let":
                body = s[len("let"):].strip()
                if "=" not in body: raise EasyError(ln, raw, "let syntax: let <name> = <value>", "Example: let greeting = Hello World")
                lhs, rhs = body.split("=", 1); lhs = lhs.strip(); rhs_raw = rhs.strip(); rhs_tok = tokenize(rhs_raw)
                if not lhs or not lhs.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{lhs}'.")
                al, rand_used = compile_assign(lhs, rhs_raw, rhs_tok, rand_used, known, unquoted_text=True)
                out.append(ind() + al); known.add(lhs); continue

            # ── input ──
            if tokens[0] == "input":
                asn, hu, iv = compile_input(tokens)
                bool_helper = bool_helper or hu
                out.append(ind() + asn); known.add(iv); continue

            # ── sleep ──
            if tokens[0] == "sleep":
                if len(tokens) != 2: raise EasyError(ln, raw, "sleep syntax: sleep <seconds>", "Example: sleep 2")
                out.append(ind() + f"time.sleep({tokens[1]})"); time_used = True; continue

            # ── wait ──
            if tokens[0] == "wait":
                if len(tokens) != 3 or tokens[2] not in ("ms", "milliseconds"):
                    raise EasyError(ln, raw, "wait syntax: wait <ms> ms", "Example: wait 500 ms")
                out.append(ind() + f"time.sleep(({tokens[1]}) / 1000)"); time_used = True; continue

            # ── assert ──
            if tokens[0] == "assert":
                if len(tokens) < 2: raise EasyError(ln, raw, "assert needs a condition.", "Example: assert x > 0")
                out.append(ind() + f"assert {join_tok(norm_bools(tokens[1:]))}"); continue

            # ── compound assignment (+=, -=, *=, /=) ──
            if len(tokens) >= 3 and tokens[1] in COMPOUND_OPS:
                var = tokens[0]; op = tokens[1]; val = join_tok(tokens[2:])
                out.append(ind() + f"{var} {op} {val}"); known.add(var); continue

            # ── bare assignment (x = ...) ──
            if "=" in s and not s.startswith(("if ", "while ", "for ", "print ", "storage ", "let ", "variable ", "function ", "foreach ")):
                lhs, rhs = s.split("=", 1); lhs = lhs.strip(); rhs_raw = rhs.strip(); rhs_tok = tokenize(rhs_raw)
                if not lhs: raise EasyError(ln, raw, "Assignment is missing a variable name on the left.")
                al, rand_used = compile_assign(lhs, rhs_raw, rhs_tok, rand_used, known)
                out.append(ind() + al)
                if lhs.isidentifier(): known.add(lhs)
                continue

            # ── call user function ──
            ft = tokens[0]
            st = tokens[1] if len(tokens) > 1 else None

            # Method-style list ops: myList.append(...)
            if st in LIST_FUNCS:
                expr_t = [st, "array", ft] + tokens[2:]
                out.append(ind() + compile_builtin(expr_t)); continue
            if ft in LIST_FUNCS:
                out.append(ind() + compile_builtin(tokens)); continue
            if ft in ALL_BUILTINS:
                out.append(ind() + compile_builtin(tokens)); continue

            # clear screen / exit program (two-word commands)
            if ft == "clear" and st == "screen":
                out.append(ind() + compile_builtin(["clearscreen"])); continue
            if ft == "exit" and st == "program":
                out.append(ind() + compile_builtin(["exitprogram"])); continue

            # ── function call (bare name with parens or known function) ──
            if "(" in ft and ft.endswith(")"):
                out.append(ind() + s); continue
            if ft in user_funcs:
                out.append(ind() + s); continue

            # ── while condition for do...while (special) ──
            if ft == "while" and indent > 0:
                # This handles the end of a do...while
                cond = compile_cond(s[6:].rstrip())
                indent -= 1
                out.append(ind() + "    " + f"if not ({cond}):")
                out.append(ind() + "    " + "    break")
                continue

            raise EasyError(ln, raw, f"Unknown command: '{s}'.", None)

        except EasyError:
            raise
        except Exception as exc:
            raise EasyError(ln, raw, str(exc))

    if indent != 0:
        raise EasyError(ln, "", "Unclosed block — you're missing one or more 'end' statements.", "Make sure every if/while/for/function/try block has a matching 'end'.")

    hdr = ["import math", "import sys", "import datetime", "import os"]
    if rand_used: hdr.append("import random")
    if time_used: hdr.append("import time")
    if bool_helper:
        hdr.extend(["", "def _dsl_parse_boolean(value):", "    n = str(value).strip().lower()",
                     "    if n in {'true', 't', 'yes', 'y', '1'}: return True",
                     "    if n in {'false', 'f', 'no', 'n', '0'}: return False",
                     '    raise ValueError("Invalid boolean. Use true/false.")'])
    return "\n".join(hdr + out)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def read_source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_file(path: str, content: str) -> None:
    t = Path(path); t.parent.mkdir(parents=True, exist_ok=True); t.write_text(content, encoding="utf-8")

def compile_file(path: str) -> tuple[str, str]:
    src = read_source(path); return src, compile_language(src)

def run_code(code: str) -> None:
    exec(code, {"__name__": "__main__"})


def render_commands() -> str:
    return f"""Easy Language v{VERSION} — Command Reference

VARIABLES
  let name = value              Create a variable (strings auto-detected)
  number x = 5                  Typed variable (number/text/boolean/float/array/dictionary)
  x += 1                        Compound assignment (+=, -=, *=, /=)

OUTPUT
  say Hello World               Print literal text
  print expression              Print any expression or variable
  print "Hello {{name}}"          String interpolation

CONDITIONS
  if x > 5:                     Simple condition (no 'is true' needed!)
      say big
  else if x > 0:                Else-if chain
      say small
  else:                         Else branch
      say zero
  end                           Close the block

LOOPS
  repeat 5 times                Repeat N times
  while x < 10:                 While loop
  for 1 to 10 do               Counted for loop
  foreach item in list:         Iterate over a collection
  end                           Close any loop

FUNCTIONS
  function greet(name):         Define a function
      say Hello
      print name
      return name               Optional return value
  end
  greet("World")                Call a function

ERROR HANDLING
  try:                          Try block
      risky code here
  catch error:                  Catch errors
      print error
  end

INPUT
  input name prompt text Name?  Ask for text input
  input number age prompt Age?  Ask for typed input

UTILITIES
  sleep 2                       Pause for seconds
  wait 500 ms                   Pause for milliseconds
  assert x > 0                  Assert a condition
  clear                         Clear the screen
  exit                          Exit the program
  length myList                 Get length (alias: len)
  keys myDict                   Get dictionary keys
  values myDict                 Get dictionary values
  random number 1 to 10         Random number
  random boolean                Random true/false
  currentdate / currenttime     Date and time
"""


def run_repl() -> int:
    print(_bold("Easy Language v3.0 REPL"))
    print("Type code, then :run. Commands: :run :show :python :clear :help :quit\n")
    buf: list[str] = []
    while True:
        try:
            line = input(_cyan("easy> ") if not buf else _dim("...  "))
        except (EOFError, KeyboardInterrupt):
            print(); break
        s = line.strip()
        if not s: continue
        if s in (":quit", ":q", "quit", "exit"): break
        if s == ":help": print("Commands: :run :show :python :clear :help :quit"); continue
        if s == ":show":
            if not buf: print("Buffer empty.")
            else:
                for i, l in enumerate(buf, 1): print(f"  {i:>3}: {l}")
            continue
        if s == ":clear": buf.clear(); print("Buffer cleared."); continue
        if s == ":python":
            if not buf: print("Buffer empty."); continue
            try: print(compile_language("\n".join(buf)))
            except EasyError as e: print(format_error(e, "\n".join(buf), "<repl>"), file=sys.stderr)
            continue
        if s == ":run":
            if not buf: print("Nothing to run."); continue
            src = "\n".join(buf)
            try: run_code(compile_language(src)); print(_dim("✓ Done."))
            except EasyError as e: print(format_error(e, src, "<repl>"), file=sys.stderr)
            except Exception as exc: print(_red(f"Runtime error: {exc}"), file=sys.stderr)
            continue
        buf.append(line)
    return 0


def handle_run(args) -> int:
    try:
        src, code = compile_file(args.input)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr)
        return 1
    except EasyError as e:
        print(format_error(e, read_source(args.input), args.input), file=sys.stderr)
        return 1
    if args.show_python:
        print(code)
    if args.save_python:
        write_file(args.save_python, code)
        print(f"Saved Python to {args.save_python}")
    try:
        run_code(code)
    except Exception as exc:
        if args.traceback:
            raise
        print(_red(f"✗ Runtime error: {exc}"), file=sys.stderr)
        return 1
    if not args.quiet:
        print(_dim(f"✓ '{args.input}' executed successfully."))
    return 0


def handle_compile(args) -> int:
    try:
        _, code = compile_file(args.input)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr)
        return 1
    except EasyError as e:
        print(format_error(e, read_source(args.input), args.input), file=sys.stderr)
        return 1
    out = args.output or (str(Path(args.input).with_suffix(".py")) if not args.stdout else None)
    if out:
        write_file(out, code)
        print(f"Compiled to {out}")
    if args.stdout:
        print(code)
    return 0


def handle_check(args) -> int:
    try:
        src, code = compile_file(args.input)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr)
        return 1
    except EasyError as e:
        print(format_error(e, read_source(args.input), args.input), file=sys.stderr)
        return 1
    print(f"✓ {args.input}: OK")
    if args.show_python: print(code)
    return 0


def handle_new(args) -> int:
    t = Path(args.path)
    if t.exists() and not args.force:
        print(_red(f"✗ File exists: {t}. Use --force to overwrite."), file=sys.stderr)
        return 1
    write_file(str(t), STARTER_TEMPLATE.format(filename=t.name))
    print(f"✓ Created {t}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="compiler.py", description="Easy Language v3.0 compiler & runner")
    p.add_argument("--version", action="version", version=f"Easy Language {VERSION}")
    sp = p.add_subparsers(dest="command")
    rp = sp.add_parser("run", help="Compile and run a .easy program")
    rp.add_argument("input", help="Path to .easy file")
    rp.add_argument("--show-python", action="store_true")
    rp.add_argument("--save-python", metavar="PATH")
    rp.add_argument("--quiet", action="store_true")
    rp.add_argument("--traceback", action="store_true")
    cp = sp.add_parser("compile", help="Compile .easy to Python")
    cp.add_argument("input")
    cp.add_argument("-o", "--output")
    cp.add_argument("--stdout", action="store_true")
    ck = sp.add_parser("check", help="Validate .easy syntax")
    ck.add_argument("input")
    ck.add_argument("--show-python", action="store_true")
    sp.add_parser("repl", help="Interactive REPL")
    sp.add_parser("commands", help="Show command reference")
    np = sp.add_parser("new", help="Create starter .easy file")
    np.add_argument("path")
    np.add_argument("--force", action="store_true")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmds = {"run", "compile", "check", "repl", "commands", "new"}
    if argv and argv[0] not in cmds and not argv[0].startswith("-"):
        argv = ["run"] + argv
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return handle_run(args)
    if args.command == "compile":
        return handle_compile(args)
    if args.command == "check":
        return handle_check(args)
    if args.command == "repl":
        return run_repl()
    if args.command == "commands":
        print(render_commands())
        return 0
    if args.command == "new":
        return handle_new(args)
    build_parser().print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
