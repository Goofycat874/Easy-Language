"""Easy Language — a beginner-friendly programming language that compiles to Python."""

import argparse
import ast
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

VERSION = "3.2.0"

# ─── Color helpers (ANSI) ────────────────────────────────────────────────────

_COLOR_SUPPORT = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR_SUPPORT else text

def _red(t: str) -> str: return _c("1;31", t)
def _yellow(t: str) -> str: return _c("1;33", t)
def _cyan(t: str) -> str: return _c("36", t)
def _dim(t: str) -> str: return _c("2", t)
def _bold(t: str) -> str: return _c("1", t)

# ─── Error classes ────────────────────────────────────────────────────────────

KNOWN_KEYWORDS = [
    "if", "else", "elif", "end", "stop", "while", "for", "foreach", "repeat",
    "print", "say", "let", "variable", "input", "sleep", "wait", "assert", "function",
    "return", "try", "catch", "check", "error", "do", "number", "text", "boolean", "float",
    "integer", "array", "dictionary", "storage", "clear", "exit",
    "break", "continue", "skip", "class", "use", "import", "ask", "add", "sort",
    "shuffle", "python", "fetch", "fetchjson", "then", "each", "forever", "until",
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
        self.runtime = False  # True for errors raised while the program was running
        super().__init__(f"Line {line_num}: {message}")


def format_error(err: EasyError, source: str, filename: str) -> str:
    """Produce a beautiful, colorized error message with context lines."""
    lines = source.splitlines()
    ln = err.line_num
    parts: list[str] = []

    kind = "Runtime error" if err.runtime else "Error"
    parts.append(_red(f"✗ {kind} in {filename}, line {ln}"))
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
    if not hint and err.line_text and not err.runtime:
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
SPECIAL_FUNCS = {"fetch", "fetchjson", "parsejson", "tojson", "text", "mod", "log", "clearscreen", "exitprogram", "currenttime", "currentdate", "currenttimestamp", "clear", "exit"}

ALL_BUILTINS = set().union(
    LIST_FUNCS, DICT_FUNCS, BOOL_FUNCS, MATH_FUNCS, FILE_FUNCS,
    TYPE_FUNCS, AGG_FUNCS, TEXT_FUNCS, CREATE_FUNCS, SPECIAL_FUNCS,
)

EXPR_OPS = {"+", "-", "*", "/", "%", "//", "**", "<", ">", "<=", ">=", "==", "!=", "and", "or", "not"}
LITERAL_KW = {"true", "false", "none"}
COMPOUND_OPS = {"+=", "-=", "*=", "/=", "%=", "**="}

# English word → operator mappings (applied during preprocessing)
WORD_OPS = {
    "plus": "+", "minus": "-", "times": "*",
    "modulo": "%", "power": "**",
}

STARTER_TEMPLATE = '''# Easy Language — Starter
# Run it:      python compiler.py run {filename}
# See Python:  python compiler.py explain {filename}
# All syntax:  python compiler.py commands

# --- Talk to the user ---
ask "What's your name?" into name
say Nice to meet you, {name}!
ask number "How old are you?" into age

# --- Conditions read like English ---
if age is at least 18 then
    say You are an adult
else
    say You are a minor ({18 - age} years to go)
stop

# --- Lists ---
let fruits = ["apple", "banana", "cherry"]
add "mango" to fruits
sort fruits
for each fruit in fruits
    say I like {fruit}
stop

# --- Loops & math ---
variable total is 0
for n from 1 to 10 step 3
    total += n
stop
say The total is {total} and half of it is {total / 2:.1f}

# --- Functions ---
function greet(who) then
    return "Hello, {who}!"
stop
print greet(name)

# --- Error handling ---
check then
    variable bad is 100 / 0
error e then
    say Oops, something went wrong: {e}
stop

say Today is {currentdate} at {currenttime}
'''


# Small Python helpers injected into compiled output only when the program uses them.
RUNTIME_HELPERS = {
    "_easy_range": (
        "def _easy_range(start, stop, step=1):\n"
        "    if step == 0: raise ValueError('step cannot be 0')\n"
        "    return range(start, stop + (1 if step > 0 else -1), step)"
    ),
    "_easy_number": (
        "def _easy_number(prompt):\n"
        "    while True:\n"
        "        text = input(prompt).strip()\n"
        "        try: return int(text)\n"
        "        except ValueError: pass\n"
        "        try: return float(text)\n"
        "        except ValueError: print('  That is not a number, try again.')"
    ),
    "_easy_fetch": (
        "def _easy_fetch(url):\n"
        "    import urllib.request\n"
        "    req = urllib.request.Request(url, headers={'User-Agent': 'EasyLanguage'})\n"
        "    with urllib.request.urlopen(req, timeout=15) as r:\n"
        "        return r.read().decode('utf-8', 'replace')"
    ),
}


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
    return ["True" if t.lower() == "true" else "False" if t.lower() == "false" else "None" if t.lower() == "none" else t for t in tokens]


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


# ─── String masking (so word-rewrites never touch text inside quotes) ───────

_STR_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

def mask_strings(s: str) -> tuple[str, list[str]]:
    store: list[str] = []
    def sub(m: re.Match) -> str:
        store.append(m.group(0))
        return f"\x00{len(store) - 1}\x00"
    return _STR_RE.sub(sub, s), store

def unmask_strings(s: str, store: list[str]) -> str:
    return re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], s)

def normalize_literals(s: str) -> str:
    """true/false/none (any case) → True/False/None, outside of quotes."""
    masked, store = mask_strings(s)
    masked = re.sub(r"\b(true|false|none)\b", lambda m: m.group(1).capitalize(), masked, flags=re.I)
    return unmask_strings(masked, store)


# ─── String interpolation: "Hello {name}", "{score + 1}", "{price:.2f}" ──────

_FORMAT_SPEC_RE = re.compile(r"^(?:[^{}]?[<>=^])?[+\- ]?#?0?\d*[,_]?(?:\.\d+)?[bcdeEfFgGnosxX%]?$")

def _parse_interp_field(field: str) -> tuple[str, str | None] | None:
    """Return (expression, format_spec) if `field` is a valid {…} body, else None."""
    def valid(expr: str) -> bool:
        try:
            ast.parse(expr.strip(), mode="eval")
            return True
        except SyntaxError:
            return False
    stripped = field.strip()
    if stripped in ("currentdate", "currenttime", "currenttimestamp"):
        return compile_builtin([stripped]), None
    if stripped and valid(field):
        return stripped, None
    # Easy-style call inside braces, e.g. {length items} or {random number 1 to 6}
    words = tokenize(stripped) if stripped else []
    if len(words) > 1 and (words[0] in ALL_BUILTINS or words[0] == "random"):
        try:
            return (compile_random(words) if words[0] == "random" else compile_builtin(words)), None
        except Exception:
            pass
    depth, quote, cut = 0, "", -1
    for i, ch in enumerate(field):
        if quote:
            if ch == quote: quote = ""
        elif ch in "\"'": quote = ch
        elif ch in "([{": depth += 1
        elif ch in ")]}": depth -= 1
        elif ch == ":" and depth == 0: cut = i
    if cut > 0:
        expr, spec = field[:cut].strip(), field[cut + 1:]
        if spec and _FORMAT_SPEC_RE.match(spec) and valid(expr):
            node = ast.parse(expr, mode="eval").body
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                return expr, spec
    return None

def has_interp(text: str) -> bool:
    return any(_parse_interp_field(m.group(1)) for m in re.finditer(r"\{([^{}]+)\}", text))

def compile_interp(text: str) -> str:
    """Turn text containing {expr} / {expr:fmt} into a Python string expression."""
    parts: list[str] = []
    pos = 0
    for m in re.finditer(r"\{([^{}]+)\}", text):
        parsed = _parse_interp_field(m.group(1))
        if not parsed:
            continue
        if m.start() > pos: parts.append(repr(text[pos:m.start()]))
        expr, spec = parsed
        parts.append(f"format({expr}, {spec!r})" if spec else f"str({expr})")
        pos = m.end()
    if not parts: return repr(text)
    if pos < len(text): parts.append(repr(text[pos:]))
    return "(" + " + ".join(parts) + ")"

def string_literal_value(raw: str) -> str | None:
    """If `raw` is exactly one Python-style string literal, return its value."""
    raw = raw.strip()
    if not is_quoted(raw): return None
    try:
        node = ast.parse(raw, mode="eval").body
    except SyntaxError:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return node.value
    return None

def str_expr(raw: str) -> str | None:
    """Compile a quoted string (with optional {interpolation}); None if `raw` isn't one."""
    val = string_literal_value(raw)
    if val is None: return None
    return compile_interp(val) if has_interp(val) else raw.strip()


# ─── Natural-language conditions ─────────────────────────────────────────────

_PHRASES = [
    (r"\s+is\s+greater\s+than\s+or\s+equal\s+to\s+", " >= "),
    (r"\s+is\s+less\s+than\s+or\s+equal\s+to\s+", " <= "),
    (r"\s+is\s+(?:greater|bigger|more)\s+than\s+", " > "),
    (r"\s+is\s+(?:less|smaller|fewer)\s+than\s+", " < "),
    (r"\s+is\s+at\s+least\s+", " >= "),
    (r"\s+is\s+at\s+most\s+", " <= "),
    (r"\s+is\s+not\s+equal\s+to\s+", " != "),
    (r"\s+is\s+equal\s+to\s+", " == "),
    (r"\s+equals\s+", " == "),
    (r"\s+is\s+not\s+in\s+", " not in "),
    (r"\s+is\s+in\s+", " in "),
    (r"\s+is\s+not\s+(?!None\b)", " != "),
]

def _natural_clause(c: str) -> str:
    neg = False
    m = re.match(r"^\s*not\s+(.*)$", c)
    if m: neg, c = True, m.group(1)
    for pat, rep in _PHRASES:
        c = re.sub(pat, rep, c)
    m = re.match(r"^(.*?)\s+is\s+(not\s+)?empty\s*$", c)
    if m: c = f"len({m.group(1)}) {'>' if m.group(2) else '=='} 0"
    m = re.match(r"^(.*?)\s+(does\s+not\s+contain|contains)\s+(.*)$", c)
    if m: c = f"{m.group(3)} {'not in' if m.group(2).startswith('does') else 'in'} {m.group(1)}"
    m = re.match(r"^(.*?)\s+(starts|ends)\s+with\s+(.*)$", c)
    if m: c = f"({m.group(1)}).{m.group(2)[:-1]}swith({m.group(3)})"
    c = re.sub(r"\s+is\s+(?!None\b)", " == ", c)
    return f"not ({c})" if neg else c

def natural_condition(expr: str) -> str:
    masked, store = mask_strings(expr)
    masked = re.sub(r"\b(true|false|none)\b", lambda m: m.group(1).capitalize(), masked, flags=re.I)
    parts = re.split(r"(\s+(?:and|or)\s+)", masked)
    for i in range(0, len(parts), 2):
        parts[i] = _natural_clause(parts[i])
    return unmask_strings("".join(parts), store)


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
    if tokens[1] in ("item", "pick", "from") and len(tokens) >= 3:
        return f"random.choice({join_tok(tokens[2:])})"
    raise Exception(f"Unknown random type '{tokens[1]}'. Use number, text, or boolean.")


def _two_args(tokens: list[str], name: str) -> tuple[str, str]:
    raw = join_tok(tokens)
    parts = [p.strip() for p in raw.split(",") if p.strip()] if "," in raw else [p.strip() for p in tokens if p.strip()]
    if len(parts) != 2:
        raise Exception(f"{name} requires exactly 2 arguments")
    return parts[0], parts[1]


def _text_or_expr(tok: str) -> str:
    """Quotes are already stripped from builtin arguments: variables/attributes stay code, the rest is text."""
    return tok if re.fullmatch(r"[A-Za-z_][\w.]*(\(.*\))?(\[.*\])*", tok) else repr(tok)


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
            if vt[0] == "text": ve = repr(join_tok(vt[1:]))
            elif vt[0] in ALL_BUILTINS: ve = compile_builtin(vt)
            elif len(vt) == 1 and (is_numeric(vt[0]) or vt[0].lower() in LITERAL_KW): ve = norm_bools(vt)[0]
            else: ve = repr(join_tok(vt))
            pairs.append(f"{repr(key)}: {ve}")
        if not pairs: raise Exception("createdictionary requires at least one key/value pair")
        return "{" + ", ".join(pairs) + "}"

    # ── Web & JSON ──
    if fn == "fetch":
        if len(tokens) != 2: raise Exception("fetch syntax: fetch <url>")
        return f"_easy_fetch({_text_or_expr(tokens[1])})"
    if fn == "fetchjson":
        if len(tokens) != 2: raise Exception("fetchjson syntax: fetchjson <url>")
        return f"json.loads(_easy_fetch({_text_or_expr(tokens[1])}))"
    if fn == "parsejson":
        if len(tokens) != 2: raise Exception("parsejson requires one argument")
        return f"json.loads({_text_or_expr(tokens[1])})"
    if fn == "tojson":
        if len(tokens) != 2: raise Exception("tojson requires one argument")
        return f"json.dumps({tokens[1]}, indent=2)"

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
    if line.endswith(":"): line = line[:-1].rstrip()
    if line.endswith(" is true"): line = line[:-len(" is true")].strip()
    elif line.endswith(" is false"):
        expr = line[:-len(" is false")].strip()
        if not expr: raise Exception("Empty condition before 'is false'")
        return f"not ({natural_condition(expr)})"
    if not line: raise Exception("Missing condition")
    return natural_condition(line)


# ─── Input compiler ──────────────────────────────────────────────────────────

def compile_input(tokens: list[str]) -> tuple[str, bool, str]:
    if len(tokens) < 2:
        raise Exception("input syntax: input [type] <variable> [prompt text <message>]")
    typed = None; idx = 1
    if tokens[idx] in ("number", "integer", "float", "text", "boolean"):
        typed = tokens[idx]; idx += 1
    if idx >= len(tokens): raise Exception("input: missing variable name")
    var = tokens[idx]
    if not var.isidentifier(): raise Exception(f"Invalid variable name '{var}'")
    idx += 1
    prompt = repr("")
    if idx < len(tokens):
        if tokens[idx] != "prompt": raise Exception("input: use 'prompt' before the message")
        pt = tokens[idx + 1:]
        if not pt: raise Exception("input prompt: missing text")
        ptxt = join_tok(pt[1:]) if pt[0] == "text" else join_tok(pt)
        if ptxt and not ptxt.endswith(" "): ptxt += " "
        prompt = repr(ptxt)
    raw = f"input({prompt})"
    helper = False
    if typed in ("number", "integer"): val = f"int({raw})"
    elif typed == "float": val = f"float({raw})"
    elif typed == "boolean": val = f"_dsl_parse_boolean({raw})"; helper = True
    else: val = raw
    return f"{var} = {val}", helper, var


# ─── Assignment helpers ───────────────────────────────────────────────────────

def should_keep_expr(toks: list[str], known: set[str], raw: str = "") -> bool:
    if any(t in EXPR_OPS for t in toks): return True
    if any(t in known for t in toks): return True
    # Check the raw string for structural patterns (brackets, parens, function calls)
    raw_s = raw.strip()
    if raw_s and (raw_s.startswith(("[", "{", "(")) or "(" in raw_s or ")" in raw_s): return True
    if len(toks) != 1: return False
    t = toks[0]; lo = t.lower()
    if lo in LITERAL_KW: return True
    if is_numeric(t): return True
    if t.startswith(("[", "{", "(")) or "(" in t or ")" in t: return True
    return False


def compile_assign(lhs: str, rhs_raw: str, rhs_tok: list[str], rand_used: bool, known: set[str], unquoted_text: bool = False) -> tuple[str, bool]:
    if not rhs_tok: raise Exception("Assignment is missing a value")
    if is_quoted(rhs_raw):
        rhs = str_expr(rhs_raw) or rhs_raw
    elif unquoted_text and has_interp(rhs_raw) and not rhs_raw.lstrip().startswith(("[", "{", "(")):
        rhs = compile_interp(rhs_raw)
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
        elif should_keep_expr(rhs_tok, known, rhs_raw): rhs = normalize_literals(rhs_raw)
        elif unquoted_text: rhs = repr(join_tok(rhs_tok))
        else: rhs = normalize_literals(rhs_raw)
    return f"{lhs} = {rhs}", rand_used


def compile_typed_assign(typ: str, var: str, raw: str, toks: list[str], rand_used: bool) -> tuple[str, bool]:
    if not toks: raise Exception("Typed assignment is missing a value")
    if is_quoted(raw): ve = str_expr(raw) or raw
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

class IncompleteBlock(EasyError):
    """Raised when the source ends while a block is still open (the REPL uses this to keep reading)."""


def _strip_block_end(s: str) -> str:
    """Drop a trailing ':' and/or 'do' from a block header."""
    s = s.rstrip().rstrip(":").rstrip()
    if s.endswith(" do"): s = s[:-3].rstrip()
    return s.rstrip(":").rstrip()


def compile_source(source: str, known: set[str] | None = None, user_funcs: set[str] | None = None) -> tuple[str, list[int]]:
    """Compile Easy source. Returns (python_code, linemap) where linemap[i] is the
    Easy line that produced Python line i+1 (0 for generated header lines)."""
    out: list[str] = []
    omap: list[int] = []
    indent = 0
    ln = 0
    rand_used = time_used = bool_helper = False
    known = set() if known is None else known
    user_funcs = set() if user_funcs is None else user_funcs
    class_levels: set[int] = set()
    ind = lambda: "    " * indent

    def emit(text: str) -> None:
        out.append(text); omap.append(ln)

    for raw in source.splitlines():
        ln += 1
        code = strip_comment(raw.rstrip("\n")).rstrip()
        code = preprocess_line(code)  # English-like syntax → core syntax
        if class_levels:
            masked, store = mask_strings(code)
            code = unmask_strings(re.sub(r"\bmy\.", "self.", masked), store)
        s = code.strip()
        if not s: continue
        tokens = tokenize(s)
        if not tokens: continue

        try:
            lo = s.lower()

            # ── end / stop program ──
            if lo in ("end program", "stop program"):
                emit(ind() + "sys.exit()"); continue

            # ── end / stop ──
            if lo in ("end", "stop"):
                indent -= 1
                if indent < 0: raise EasyError(ln, raw, "Unmatched 'stop' — there's no open block to close.", "Make sure every if/while/for/function/check has a matching 'stop'.")
                class_levels.discard(indent)
                continue

            # ── else if / elif ──
            if lo.startswith("else if ") or lo.startswith("elif "):
                if indent <= 0: raise EasyError(ln, raw, "'else if' must come after an if block.")
                start = 8 if lo.startswith("else if ") else 5
                cond = compile_cond(s[start:])
                indent -= 1; emit(ind() + f"elif {cond}:"); indent += 1; continue

            # ── else ──
            if lo in ("else", "else:"):
                if indent <= 0: raise EasyError(ln, raw, "'else' must come after an if/elif block.")
                indent -= 1; emit(ind() + "else:"); indent += 1; continue

            # ── if ──
            if s.startswith("if "):
                cond = compile_cond(s[3:])
                emit(ind() + f"if {cond}:"); indent += 1; continue

            # ── while ──
            if s.startswith("while "):
                wl = s[6:].rstrip()
                if wl.endswith(" do"): wl = wl[:-3].rstrip()
                emit(ind() + f"while {compile_cond(wl)}:"); indent += 1; continue

            # ── do...while ──
            if lo in ("do", "do:"):
                emit(ind() + "while True:"); indent += 1; continue

            # ── break / continue ──
            if lo in ("break", "stop loop", "leave"):
                emit(ind() + "break"); continue
            if lo in ("continue", "skip", "next"):
                emit(ind() + "continue"); continue

            # ── for ──
            if s.startswith("for "):
                head = _strip_block_end(s)
                ft = tokenize(head)
                if len(ft) == 4 and ft[0] == "for" and ft[2] == "to":
                    emit(ind() + f"for i in range({ft[1]}, {ft[3]} + 1):"); known.add("i")
                elif len(ft) >= 6 and ft[2] == "from" and ft[4] == "to":
                    var = ft[1]; step = "1"
                    if len(ft) == 8 and ft[6] == "step": step = ft[7]
                    elif len(ft) != 6: raise EasyError(ln, raw, "for syntax: for <var> from <start> to <end> [step <n>]", "Example: for n from 1 to 10 step 2")
                    if not var.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{var}'.")
                    emit(ind() + f"for {var} in _easy_range({ft[3]}, {ft[5]}, {step}):"); known.add(var)
                elif len(ft) >= 4 and ft[1] == "each" and ft[3] == "in":
                    var = ft[2]
                    emit(ind() + f"for {var} in {head.split(' in ', 1)[1].strip()}:"); known.add(var)
                elif len(ft) >= 4 and ft[2] == "in":
                    var = ft[1]
                    emit(ind() + f"for {var} in {head.split(' in ', 1)[1].strip()}:"); known.add(var)
                else:
                    raise EasyError(ln, raw, "I didn't understand this 'for' loop.", "Try: for 1 to 10 | for n from 1 to 10 step 2 | for each item in list")
                indent += 1; continue

            # ── foreach ──
            if tokens[0] == "foreach":
                if len(tokens) < 4 or tokens[2] != "in":
                    raise EasyError(ln, raw, "foreach syntax: foreach <item> in <collection>:", "Example: foreach x in myList:")
                item = tokens[1]; collection = _strip_block_end(s).split(" in ", 1)[1].strip()
                emit(ind() + f"for {item} in {collection}:"); known.add(item); indent += 1; continue

            # ── repeat forever ──
            if lo in ("repeat forever", "repeat forever:", "forever"):
                emit(ind() + "while True:"); indent += 1; continue

            # ── repeat ──
            if tokens[0] == "repeat":
                if len(tokens) not in (3, 4) or tokens[2] != "times":
                    raise EasyError(ln, raw, "repeat syntax: repeat <count> times", "Example: repeat 5 times")
                emit(ind() + f"for _ in range(int({tokens[1]})):"); indent += 1; continue

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
                if (indent - 1) in class_levels:  # method: add self automatically
                    inner = params[1:-1].strip() if params.endswith(")") else ""
                    params = "(" + ", ".join(["self"] + ([inner] if inner else [])) + ")"
                    if name == "init": name = "__init__"
                else:
                    user_funcs.add(name)
                emit(ind() + f"def {name}{params}:"); indent += 1; continue

            # ── class ──
            if tokens[0] == "class":
                m = re.match(r"^class\s+(\w+)(?:\s+(?:extends|from)\s+(\w+))?$", _strip_block_end(s))
                if not m: raise EasyError(ln, raw, "class syntax: class Name [extends Other]", "Example: class Dog extends Animal")
                emit(ind() + f"class {m.group(1)}" + (f"({m.group(2)})" if m.group(2) else "") + ":")
                class_levels.add(indent); user_funcs.add(m.group(1)); indent += 1; continue

            # ── use / import ──
            if tokens[0] in ("use", "import"):
                m = re.match(r"^(?:use|import)\s+([\w., ]+?)\s+from\s+([\w.]+)$", s)
                if m: emit(ind() + f"from {m.group(2)} import {m.group(1)}"); continue
                m = re.match(r"^(?:use|import)\s+([\w.]+)(?:\s+as\s+(\w+))?$", s)
                if not m: raise EasyError(ln, raw, "use syntax: use <module> [as <name>]  or  use <thing> from <module>", "Example: use json | use sqrt from math")
                emit(ind() + f"import {m.group(1)}" + (f" as {m.group(2)}" if m.group(2) else "")); continue

            # ── python (raw passthrough for power users) ──
            if tokens[0] == "python" and len(tokens) > 1:
                emit(ind() + s[len("python"):].strip()); continue

            # ── ask "question" into var ──
            if tokens[0] == "ask":
                m = re.match(r"^ask\s+(?:(number|integer|float|boolean|text)\s+)?(.+?)\s+into\s+(\w+)$", s)
                if not m: raise EasyError(ln, raw, 'ask syntax: ask [number] "question" into <variable>', 'Example: ask number "How old are you?" into age')
                typ, prompt, var = m.groups()
                lit = string_literal_value(prompt)
                text = lit if lit is not None else prompt
                if not text.endswith((" ", "\n")): text += " "
                pe = compile_interp(text) if has_interp(text) else repr(text)
                raw_in = f"input({pe})"
                val = {"number": f"_easy_number({pe})", "integer": f"int({raw_in})", "float": f"float({raw_in})",
                       "boolean": f"_dsl_parse_boolean({raw_in})"}.get(typ or "", raw_in)
                bool_helper = bool_helper or typ == "boolean"
                emit(ind() + f"{var} = {val}"); known.add(var); continue

            # ── list helpers: add X to L | remove X from L | sort L | shuffle L ──
            m = re.match(r"^add\s+(.+?)\s+to\s+([\w.\[\]]+)$", s)
            if m:
                v, _ = compile_assign("_t", m.group(1), tokenize(m.group(1)), False, known, unquoted_text=True)
                emit(ind() + f"{m.group(2)}.append({v[len('_t = '):]})"); continue
            m = re.match(r"^remove\s+(.+?)\s+from\s+([\w.\[\]]+)$", s)
            if m:
                v, _ = compile_assign("_t", m.group(1), tokenize(m.group(1)), False, known, unquoted_text=True)
                emit(ind() + f"{m.group(2)}.remove({v[len('_t = '):]})"); continue
            m = re.match(r"^sort\s+([\w.\[\]]+)(\s+(?:descending|backwards|reverse))?$", s)
            if m:
                emit(ind() + f"{m.group(1)}.sort(" + ("reverse=True" if m.group(2) else "") + ")"); continue
            m = re.match(r"^shuffle\s+([\w.\[\]]+)$", s)
            if m:
                emit(ind() + f"random.shuffle({m.group(1)})"); continue

            # ── return ──
            if tokens[0] == "return":
                if len(tokens) == 1:
                    emit(ind() + "return"); continue
                expr = s[len("return"):].strip()
                emit(ind() + f"return {str_expr(expr) or normalize_literals(expr)}"); continue

            # ── try ──
            if lo in ("try", "try:"):
                emit(ind() + "try:"); indent += 1; continue

            # ── catch ──
            if lo.startswith("catch"):
                if indent <= 0: raise EasyError(ln, raw, "'catch' must come after a try block.")
                indent -= 1
                parts = s.split(None, 1)
                err_var = parts[1].rstrip(":") if len(parts) > 1 else "e"
                if err_var and err_var != ":":
                    emit(ind() + f"except Exception as {err_var}:"); known.add(err_var)
                else:
                    emit(ind() + "except Exception as _err:")
                indent += 1; continue

            # ── print ──
            if tokens[0] == "print":
                expr_raw = s[len("print"):].strip()
                et = tokens[1:]
                if not et: raise EasyError(ln, raw, "print needs something to print!", "Example: print \"Hello\" or print myVar")
                if is_quoted(expr_raw):
                    oc = f"print({str_expr(expr_raw) or expr_raw})"
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
                    oc = f"print({normalize_literals(expr_raw)})"
                emit(ind() + oc); continue

            # ── say ──
            if tokens[0] == "say":
                lit = s[len("say"):].strip()
                if not lit: raise EasyError(ln, raw, "say needs text to print!", "Example: say Hello World")
                if is_quoted(lit):
                    emit(ind() + f"print({str_expr(lit) or lit})")
                else:
                    emit(ind() + f"print({compile_interp(lit)})")
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
                emit(ind() + al); known.add(var); continue

            # ── typed shorthand: number x = 5 ──
            if tokens[0] in ALLOWED_TYPES and len(tokens) >= 4 and tokens[2] == "=":
                typ = tokens[0].lower(); var = tokens[1]
                if not var.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{var}'.")
                er = s.split("=", 1)[1].strip(); et = tokens[3:]
                al, rand_used = compile_typed_assign(typ, var, er, et, rand_used)
                emit(ind() + al); known.add(var); continue

            # ── let ──
            if tokens[0] == "let":
                body = s[len("let"):].strip()
                if "=" not in body: raise EasyError(ln, raw, "let syntax: let <name> = <value>", "Example: let greeting = Hello World")
                lhs, rhs = body.split("=", 1); lhs = lhs.strip(); rhs_raw = rhs.strip(); rhs_tok = tokenize(rhs_raw)
                if not lhs or not lhs.isidentifier(): raise EasyError(ln, raw, f"Invalid variable name '{lhs}'.")
                al, rand_used = compile_assign(lhs, rhs_raw, rhs_tok, rand_used, known, unquoted_text=True)
                emit(ind() + al); known.add(lhs); continue

            # ── input ──
            if tokens[0] == "input":
                asn, hu, iv = compile_input(tokens)
                bool_helper = bool_helper or hu
                emit(ind() + asn); known.add(iv); continue

            # ── sleep ──
            if tokens[0] == "sleep":
                if len(tokens) != 2: raise EasyError(ln, raw, "sleep syntax: sleep <seconds>", "Example: sleep 2")
                emit(ind() + f"time.sleep({tokens[1]})"); time_used = True; continue

            # ── wait ──
            if tokens[0] == "wait":
                if len(tokens) != 3 or tokens[2] not in ("ms", "milliseconds"):
                    raise EasyError(ln, raw, "wait syntax: wait <ms> ms", "Example: wait 500 ms")
                emit(ind() + f"time.sleep(({tokens[1]}) / 1000)"); time_used = True; continue

            # ── assert ──
            if tokens[0] == "assert":
                if len(tokens) < 2: raise EasyError(ln, raw, "assert needs a condition.", "Example: assert x > 0")
                cond, _, msg = s[len("assert"):].strip().partition(", ")
                emit(ind() + f"assert {compile_cond(cond)}" + (f", {msg}" if msg else "")); continue

            # ── compound assignment (+=, -=, *=, /=) ──
            if len(tokens) >= 3 and tokens[1] in COMPOUND_OPS:
                var = tokens[0]; op = tokens[1]; val = join_tok(tokens[2:])
                emit(ind() + f"{var} {op} {val}"); known.add(var); continue

            # ── bare assignment (x = ...) ──
            if "=" in s and not s.startswith(("if ", "while ", "for ", "print ", "storage ", "let ", "variable ", "function ", "foreach ")):
                lhs, rhs = s.split("=", 1); lhs = lhs.strip(); rhs_raw = rhs.strip(); rhs_tok = tokenize(rhs_raw)
                if not lhs: raise EasyError(ln, raw, "Assignment is missing a variable name on the left.")
                al, rand_used = compile_assign(lhs, rhs_raw, rhs_tok, rand_used, known)
                emit(ind() + al)
                if lhs.isidentifier(): known.add(lhs)
                continue

            # ── call user function ──
            ft = tokens[0]
            st = tokens[1] if len(tokens) > 1 else None

            # Method-style list ops: myList.append(...)
            if st in LIST_FUNCS:
                expr_t = [st, "array", ft] + tokens[2:]
                emit(ind() + compile_builtin(expr_t)); continue
            if ft in LIST_FUNCS:
                emit(ind() + compile_builtin(tokens)); continue
            if ft in ALL_BUILTINS:
                emit(ind() + compile_builtin(tokens)); continue

            # clear screen / exit program (two-word commands)
            if ft == "clear" and st == "screen":
                emit(ind() + compile_builtin(["clearscreen"])); continue
            if ft == "exit" and st == "program":
                emit(ind() + compile_builtin(["exitprogram"])); continue

            # ── function call (bare name with parens or known function) ──
            if "(" in ft and ft.endswith(")"):
                emit(ind() + s); continue
            if re.match(r"^[\w.]+\(.*\)$", s):  # e.g. dog.add(1, 2) or greet("a", "b")
                emit(ind() + s); continue
            if ft in user_funcs:
                emit(ind() + s); continue

            # ── while condition for do...while (special) ──
            if ft == "while" and indent > 0:
                # This handles the end of a do...while
                cond = compile_cond(s[6:].rstrip())
                indent -= 1
                emit(ind() + "    " + f"if not ({cond}):")
                emit(ind() + "    " + "    break")
                continue

            raise EasyError(ln, raw, f"Unknown command: '{s}'.", None)

        except EasyError:
            raise
        except Exception as exc:
            raise EasyError(ln, raw, str(exc))

    if indent != 0:
        raise IncompleteBlock(ln, "", "Unclosed block — you're missing one or more 'stop' statements.", "Make sure every if/while/for/function/class/check block has a matching 'stop'.")

    body = "\n".join(out)
    hdr = ["import math", "import sys", "import datetime", "import os"]
    for mod in ("random", "time", "json"):
        if re.search(rf"\b{mod}\.", body): hdr.append(f"import {mod}")
    if bool_helper:
        hdr.extend(["", "def _dsl_parse_boolean(value):", "    n = str(value).strip().lower()",
                    "    if n in {'true', 't', 'yes', 'y', '1'}: return True",
                    "    if n in {'false', 'f', 'no', 'n', '0'}: return False",
                    '    raise ValueError("Invalid boolean. Use true/false.")'])
    for name, helper in RUNTIME_HELPERS.items():
        if name in body:
            if "json" in helper and "import json" not in hdr: hdr.append("import json")
            hdr.extend(["", *helper.splitlines()])
    return "\n".join(hdr + out), [0] * len(hdr) + omap


def compile_language(source: str) -> str:
    """Compile Easy source to Python source."""
    return compile_source(source)[0]


# ─── CLI ──────────────────────────────────────────────────────────────────────

def read_source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_file(path: str, content: str) -> None:
    t = Path(path); t.parent.mkdir(parents=True, exist_ok=True); t.write_text(content, encoding="utf-8")

def compile_file(path: str) -> tuple[str, str]:
    src = read_source(path); return src, compile_language(src)

def run_code(code: str, namespace: dict | None = None) -> dict:
    """Execute compiled code. The file name '<easy>' lets us map tracebacks back to Easy lines."""
    ns = {"__name__": "__main__"} if namespace is None else namespace
    exec(compile(code, "<easy>", "exec"), ns)
    return ns


def friendly_error(exc: BaseException, ns: dict) -> tuple[str, str | None]:
    """Translate a Python exception into plain English plus a hint."""
    if isinstance(exc, ZeroDivisionError):
        return "You tried to divide by zero.", "Check the number you're dividing by before dividing."
    if isinstance(exc, NameError):
        name = getattr(exc, "name", None) or (re.search(r"'(.+?)'", str(exc)) or [None, "?"])[1]
        pool = [k for k in ns if not k.startswith("_")]
        close = difflib.get_close_matches(name, pool, n=1, cutoff=0.6)
        hint = f"Did you mean '{close[0]}'?" if close else f"Create it first, like:  let {name} = ..."
        return f"'{name}' doesn't exist yet.", hint
    if isinstance(exc, IndexError):
        return "That position isn't in the list.", "Lists start at 0, so the last item is at (length - 1)."
    if isinstance(exc, KeyError):
        return f"The dictionary has no key {exc}.", "Check the spelling, or add the key first."
    if isinstance(exc, FileNotFoundError):
        return f"I couldn't find the file '{exc.filename}'.", "Check the file name and the folder you're running from."
    if isinstance(exc, ValueError) and ("invalid literal" in str(exc) or "could not convert" in str(exc)):
        return "That text can't be turned into a number.", "Make sure the input only contains digits."
    if isinstance(exc, TypeError) and ("concatenate" in str(exc) or "unsupported operand" in str(exc)):
        return "You mixed two kinds of things (like text and a number).", 'Use interpolation instead:  say "Total: {n}"'
    if isinstance(exc, EOFError):
        return "The program asked for input, but there was none left.", None
    if isinstance(exc, AssertionError):
        return "An assert failed" + (f": {exc}" if str(exc) else "."), None
    if isinstance(exc, ModuleNotFoundError):
        return f"The module '{exc.name}' isn't installed.", f"Try:  pip install {str(exc.name).split('.')[0]}"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)) and not isinstance(exc, FileNotFoundError):
        return f"A network or file problem happened: {exc}", None
    return f"{type(exc).__name__}: {exc}", None


def easy_line_of(exc: BaseException, linemap: list[int]) -> int:
    """Innermost Easy source line involved in the exception's traceback (0 if unknown)."""
    line, tb = 0, exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<easy>" and 0 < tb.tb_lineno <= len(linemap) and linemap[tb.tb_lineno - 1]:
            line = linemap[tb.tb_lineno - 1]
        tb = tb.tb_next
    return line


def format_runtime_error(exc: BaseException, source: str, filename: str, linemap: list[int], ns: dict) -> str:
    msg, hint = friendly_error(exc, ns)
    line = easy_line_of(exc, linemap)
    if not line:
        return _red(f"✗ Runtime error: {msg}") + (f"\n  {_yellow('💡 ' + hint)}" if hint else "")
    lines = source.splitlines()
    err = EasyError(line, lines[line - 1] if line <= len(lines) else "", msg, hint)
    err.runtime = True
    return format_error(err, source, filename)


def render_commands() -> str:
    return f"""Easy Language {VERSION} — Command Reference
(run `python compiler.py explain file.easy` to see the Python each line becomes)

VARIABLES
  let name = value              Create a variable (text is auto-detected)
  variable age is 20            Same thing, more English
  number x = 5                  Typed variable (number/text/boolean/float/array/dictionary)
  x += 1                        Compound assignment (+= -= *= /= %= **=)

OUTPUT  (anything in {{braces}} is calculated!)
  say Hello World               Print literal text
  say Total: {{price * qty}}      Interpolate whole expressions
  say Pi is {{pi:.2f}}            Format numbers (2 decimals)
  print expression              Print any expression or variable

INPUT
  ask "Your name?" into name              Ask for text
  ask number "How old?" into age          Ask for a number (3 or 3.5)
  input name prompt text Name?            (classic syntax still works)

CONDITIONS  (write them like English)
  if age is at least 18 then
  if name is "Sam" or name is "Alex"
  if score is greater than 90 and not done
  if fruits contains "apple"          if text starts with "Hi"
  if basket is empty                  if x is not 5
  else if / else                      Chain branches
  stop                                Close any block

LOOPS
  repeat 5 times                      repeat forever
  while x < 10                        for 1 to 10                (uses i)
  for n from 1 to 10 step 2           for each item in list
  break    continue (or skip)

LISTS & DICTIONARIES
  let items = [1, 2, 3]               add 4 to items
  remove 2 from items                 sort items [descending]
  shuffle items                       random item items
  createdictionary key a value 1      length items / keys d / values d

FUNCTIONS & CLASSES
  function add(a, b)                  return a + b
  class Dog extends Animal
      function init(name)             (init = constructor, `self` is automatic)
          my.name = name              (`my.` is a friendly `self.`)
      function speak()
          say {{my.name}} says woof

ERRORS
  check ... error e ... stop          try / catch
  assert x > 0, "x must be positive"

POWER TOOLS
  use json / use sqrt from math       Import ANY Python module
  fetch "https://..."                 Download a web page / API response
  fetchjson "https://..."             Download JSON and get a ready-to-use value
  parsejson text / tojson data        JSON in and out
  python print(sum(range(10)))        Drop down to raw Python for one line
  readfile / writefile / appendfile   File I/O
  sleep 2 / wait 500 ms               Pauses
  currentdate / currenttime           Date and time
  random number 1 to 10               Random values
"""


def run_repl() -> int:
    print(_bold(f"Easy Language {VERSION} REPL") + _dim("  — type code, it runs as soon as a block is complete"))
    print(_dim("Commands: :help  :python (last compiled code)  :reset  :quit   |  just type `2 + 2` to evaluate\n"))
    ns: dict = {"__name__": "__main__"}
    known: set[str] = set()
    funcs: set[str] = set()
    last_py = ""
    buf: list[str] = []
    while True:
        try:
            line = input(_cyan("easy> ") if not buf else _dim("...   "))
        except EOFError:
            print(); break
        except KeyboardInterrupt:
            print(); buf.clear(); continue
        s = line.strip()
        if not buf:
            if not s: continue
            if s in (":quit", ":q", "quit", "exit"): break
            if s == ":help": print(render_commands()); continue
            if s == ":reset": ns, known, funcs, last_py = {"__name__": "__main__"}, set(), set(), ""; print("Fresh start."); continue
            if s == ":python": print(last_py or "Nothing compiled yet."); continue
        buf.append(line)
        src = "\n".join(buf)
        k2, f2 = set(known), set(funcs)
        try:
            code, linemap = compile_source(src, k2, f2)
        except IncompleteBlock:
            continue
        except EasyError as e:
            buf.clear()
            if "Unknown command" in e.message:  # maybe it's a plain expression: 2 + 2
                try:
                    value = eval(compile(s, "<repl>", "eval"), ns)
                    if value is not None: print(repr(value))
                    continue
                except Exception:
                    pass
            print(format_error(e, src, "<repl>"), file=sys.stderr); continue
        buf.clear()
        known, funcs, last_py = k2, f2, code
        try:
            run_code(code, ns)
        except KeyboardInterrupt:
            print(_dim("Stopped."))
        except SystemExit:
            break
        except Exception as exc:
            print(format_runtime_error(exc, src, "<repl>", linemap, ns), file=sys.stderr)
    return 0


def handle_run(args) -> int:
    try:
        src = read_source(args.input)
        code, linemap = compile_source(src)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr); return 1
    except EasyError as e:
        print(format_error(e, src, args.input), file=sys.stderr); return 1
    if args.show_python: print(code)
    if args.save_python: write_file(args.save_python, code); print(f"Saved Python to {args.save_python}")
    ns: dict = {"__name__": "__main__"}
    try:
        run_code(code, ns)
    except KeyboardInterrupt:
        print(_dim("\nStopped."), file=sys.stderr); return 130
    except Exception as exc:
        if args.traceback: raise
        print(format_runtime_error(exc, src, args.input, linemap, ns), file=sys.stderr); return 1
    if not args.quiet: print(_dim(f"✓ '{args.input}' executed successfully."))
    return 0


def handle_compile(args) -> int:
    try:
        _, code = compile_file(args.input)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr); return 1
    except EasyError as e:
        print(format_error(e, read_source(args.input), args.input), file=sys.stderr); return 1
    out = args.output or (str(Path(args.input).with_suffix(".py")) if not args.stdout else None)
    if out: write_file(out, code); print(f"Compiled to {out}")
    if args.stdout: print(code)
    return 0


def handle_check(args) -> int:
    try:
        src, code = compile_file(args.input)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr); return 1
    except EasyError as e:
        print(format_error(e, read_source(args.input), args.input), file=sys.stderr); return 1
    print(f"✓ {args.input}: OK")
    if args.show_python: print(code)
    return 0


def handle_explain(args) -> int:
    """Show each Easy line next to the Python it becomes — great for learning."""
    try:
        src = read_source(args.input)
        code, linemap = compile_source(src)
    except FileNotFoundError:
        print(_red(f"✗ File not found: {args.input}"), file=sys.stderr); return 1
    except EasyError as e:
        print(format_error(e, src, args.input), file=sys.stderr); return 1
    py_lines = code.splitlines()
    by_line: dict[int, list[str]] = {}
    for py, easy_ln in zip(py_lines, linemap):
        if easy_ln: by_line.setdefault(easy_ln, []).append(py)
    for n, text in enumerate(src.splitlines(), 1):
        if n in by_line:
            print(f"{_dim(f'{n:>4} │')} {_bold(text.rstrip())}")
            for py in by_line[n]: print(f"{_dim('     ╰─')} {_cyan(py.strip())}")
        elif text.strip():
            print(f"{_dim(f'{n:>4} │')} {_dim(text.rstrip())}")
    return 0


def handle_new(args) -> int:
    t = Path(args.path)
    if t.exists() and not args.force:
        print(_red(f"✗ File exists: {t}. Use --force to overwrite."), file=sys.stderr); return 1
    write_file(str(t), STARTER_TEMPLATE.replace("{filename}", t.name))
    print(f"✓ Created {t}"); return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="compiler.py", description=f"Easy Language {VERSION} compiler & runner")
    p.add_argument("--version", action="version", version=f"Easy Language {VERSION}")
    sp = p.add_subparsers(dest="command")
    rp = sp.add_parser("run", help="Compile and run a .easy program")
    rp.add_argument("input", help="Path to .easy file")
    rp.add_argument("--show-python", action="store_true")
    rp.add_argument("--save-python", metavar="PATH")
    rp.add_argument("--quiet", action="store_true")
    rp.add_argument("--traceback", action="store_true")
    cp = sp.add_parser("compile", help="Compile .easy to Python")
    cp.add_argument("input"); cp.add_argument("-o", "--output"); cp.add_argument("--stdout", action="store_true")
    ck = sp.add_parser("check", help="Validate .easy syntax")
    ck.add_argument("input"); ck.add_argument("--show-python", action="store_true")
    ep = sp.add_parser("explain", help="Show the Python behind every line")
    ep.add_argument("input")
    sp.add_parser("repl", help="Interactive REPL")
    sp.add_parser("commands", help="Show command reference")
    np = sp.add_parser("new", help="Create starter .easy file")
    np.add_argument("path"); np.add_argument("--force", action="store_true")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmds = {"run", "compile", "check", "explain", "repl", "commands", "new"}
    if argv and argv[0] not in cmds and not argv[0].startswith("-"):
        argv = ["run"] + argv
    args = build_parser().parse_args(argv)
    if args.command == "run": return handle_run(args)
    if args.command == "compile": return handle_compile(args)
    if args.command == "check": return handle_check(args)
    if args.command == "explain": return handle_explain(args)
    if args.command == "repl": return run_repl()
    if args.command == "commands": print(render_commands()); return 0
    if args.command == "new": return handle_new(args)
    if not argv: return run_repl()  # bare `python compiler.py` opens the REPL
    build_parser().print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
