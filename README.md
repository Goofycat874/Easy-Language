# Easy Language

A programming language that reads like English and compiles to Python.
Easy enough for a first program, powerful enough that you never hit a wall —
anything Python can do, Easy can do.

```
ask "What's your name?" into name
say Hello, {name}!

let fruits = ["apple", "banana"]
add "mango" to fruits
for each fruit in fruits
    if fruit starts with "m" then
        say {fruit} is my favourite
    stop
stop
```

## Quick start

Needs Python 3.10+. No installs.

```bash
python compiler.py new hello.easy      # create a starter program
python compiler.py run hello.easy      # run it   (or just: python compiler.py hello.easy)
python compiler.py explain hello.easy  # see the Python behind every line
python compiler.py                     # open the REPL
python compiler.py commands            # full cheat sheet
```

| Command | What it does |
| --- | --- |
| `run file.easy` | Compile and run (`--show-python`, `--save-python PATH`, `--traceback`) |
| `explain file.easy` | Each Easy line next to the Python it becomes |
| `check file.easy` | Validate syntax without running |
| `compile file.easy` | Write the `.py` file |
| `repl` | Interactive session — runs as soon as a block is complete, keeps your variables |
| `new file.easy` | Starter template |

## The language in one page

**Blocks** open with a line (optionally ending in `then`) and close with `stop`.

```
let name = Sam                 # text needs no quotes
variable age is 20             # more English
x += 1                         # also -= *= /= %= **=
say Total: {price * qty}       # {anything} is calculated
say Pi is {pi:.2f}             # with number formatting
ask number "How old?" into age # re-asks until it's a number
```

**Conditions read like English**

```
if age is at least 18 and name is not "Bob" then
if score is greater than 90        if basket is empty
if fruits contains "apple"         if word starts with "Hi"
else if ... / else
```
Also `is less than`, `is at most`, `equals`, `is in`, `does not contain`, `ends with`.

**Loops**

```
repeat 5 times            repeat forever
while x < 10              for 1 to 10                  (counter is i)
for n from 1 to 10 step 2 for each item in list
break        continue (or skip)
```

**Lists & dictionaries**

```
let items = [3, 1, 2]     add 4 to items      remove 3 from items
sort items descending     shuffle items       random item items
let d = {"a": 1}          say {d["a"]} / {length items} / {keys d}
```

**Functions & classes** (`self` is automatic; `my.` is a friendlier `self.`)

```
function add(a, b)
    return a + b
stop

class Dog extends Animal
    function init(name)
        my.name = name
    stop
    function speak()
        say {my.name} says woof
    stop
stop
```

**Errors**

```
check
    let x = 10 / 0
error e
    say Caught: {e}
stop
assert x > 0, "x must be positive"
```

**Power tools** — this is what makes Easy more than a toy

```
use json                          # import ANY Python module
use sqrt from math
let page = fetch "https://example.com"
let data = fetchjson "https://api.example.com/items"
say {tojson data}                 # also: parsejson
python print([x * x for x in range(5)])   # one line of raw Python
```

## Friendly errors

Mistakes point at *your* line, in plain English — including mistakes that only
show up while the program runs:

```
✗ Runtime error in game.easy, line 12

      11 │ stop
  ▸   12 │ say Score: {scroe}
      13 │

  'scroe' doesn't exist yet.
  💡 Did you mean 'score'?
```

## Examples & tests

`examples/` has small programs from hello-world up to classes, web APIs and
raw Python. Run the test suite with:

```bash
python -m unittest discover -s tests -v
```
