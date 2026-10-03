"""Tests for Easy Language. Run with:  python -m unittest discover -s tests -v"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import compiler as easy  # noqa: E402


def run(src: str, stdin: str = "") -> str:
    """Compile and run Easy source, returning everything it printed."""
    code, _ = easy.compile_source(src)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), mock.patch("sys.stdin", io.StringIO(stdin)):
        easy.run_code(code)
    return out.getvalue()


def lines(src: str, stdin: str = "") -> list[str]:
    return run(src, stdin).splitlines()


class Basics(unittest.TestCase):
    def test_variable_and_print(self):
        self.assertEqual(lines('variable name is "meow"\nprint name'), ["meow"])

    def test_say_literal_and_unquoted_text(self):
        self.assertEqual(lines("say Hello World"), ["Hello World"])
        self.assertEqual(lines("let w = hello world\nprint w"), ["hello world"])

    def test_math_words(self):
        self.assertEqual(lines("variable x is 10\nvariable y is x plus 5 times 2\nprint y"), ["20"])

    def test_booleans_and_none_literals(self):
        self.assertEqual(lines("let done = true\nif done == true then\n say ok\nstop"), ["ok"])
        self.assertEqual(lines("let n = none\nprint n"), ["None"])

    def test_comments(self):
        self.assertEqual(lines("say hi # trailing\n// whole line\nsay bye"), ["hi", "bye"])

    def test_repeat_and_compound(self):
        self.assertEqual(lines("let t = 0\nrepeat 3 times\n t += 2\nstop\nprint t"), ["6"])

    def test_check_error(self):
        src = "check then\n let x = 1 / 0\nerror e then\n say caught\nstop"
        self.assertEqual(lines(src), ["caught"])

    def test_dictionary_values_keep_types(self):
        out = run("let d = createdictionary key a value 1 key b value hi\nprint d")
        self.assertEqual(out.strip(), "{'a': 1, 'b': 'hi'}")


class Interpolation(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(lines("let n = Sam\nsay Hi {n}!"), ["Hi Sam!"])

    def test_expressions(self):
        self.assertEqual(lines("let x = 5\nsay x+1 is {x + 1}"), ["x+1 is 6"])

    def test_format_spec(self):
        self.assertEqual(lines("let p = 3.14159\nsay {p:.2f}"), ["3.14"])

    def test_json_like_text_is_untouched(self):
        self.assertEqual(lines('say {"a": 1} is json'), ['{"a": 1} is json'])

    def test_quoted_and_let(self):
        self.assertEqual(lines('let n = 2\nlet s = "n is {n}"\nprint s\nprint "double {n * 2}"'), ["n is 2", "double 4"])

    def test_easy_builtins_inside_braces(self):
        self.assertEqual(lines("let a = [1, 2, 3]\nsay {length a} items"), ["3 items"])
        self.assertEqual(len(lines("say {currentdate}")[0]), 10)

    def test_return_interpolation(self):
        self.assertEqual(lines('function g(n) then\n return "Hi {n}"\nstop\nprint g("Bo")'), ["Hi Bo"])


class Conditions(unittest.TestCase):
    def check(self, cond, expected, setup="let x = 5\nlet name = Sam\nlet items = [1, 2]\nlet empty = []\n"):
        src = f"{setup}if {cond} then\n say yes\nelse\n say no\nstop"
        self.assertEqual(lines(src), ["yes" if expected else "no"], cond)

    def test_natural_comparisons(self):
        self.check("x is greater than 3", True)
        self.check("x is more than 5", False)
        self.check("x is less than 3", False)
        self.check("x is at least 5", True)
        self.check("x is at most 4", False)
        self.check("x is 5", True)
        self.check("x equals 5", True)
        self.check("x is not 5", False)
        self.check("x is not equal to 6", True)

    def test_text_and_membership(self):
        self.check('name is "Sam"', True)
        self.check('name is "Sam and Alex"', False)  # words inside quotes are never rewritten
        self.check("items contains 2", True)
        self.check("items does not contain 2", False)
        self.check("2 is in items", True)
        self.check('name starts with "S"', True)
        self.check('name ends with "z"', False)

    def test_empty(self):
        self.check("empty is empty", True)
        self.check("items is not empty", True)

    def test_logic(self):
        self.check("x is 5 and name is \"Sam\"", True)
        self.check("x is 1 or name is \"Sam\"", True)
        self.check("not x is 5", False)

    def test_legacy_is_true_false(self):
        self.check("x > 3 is true", True)
        self.check("x > 3 is false", False)

    def test_while_natural(self):
        self.assertEqual(lines("let x = 0\nwhile x is less than 3\n x += 1\nstop\nprint x"), ["3"])


class Loops(unittest.TestCase):
    def test_for_to(self):
        self.assertEqual(lines("for 1 to 3 do\n print i\nstop"), ["1", "2", "3"])

    def test_for_from_step(self):
        self.assertEqual(lines("for n from 1 to 10 step 4\n print n\nstop"), ["1", "5", "9"])
        self.assertEqual(lines("for n from 3 to 1 step -1\n print n\nstop"), ["3", "2", "1"])

    def test_for_each(self):
        self.assertEqual(lines("for each f in [1, 2]\n print f\nstop"), ["1", "2"])
        self.assertEqual(lines("foreach f in [1, 2] then\n print f\nstop"), ["1", "2"])

    def test_break_continue_forever(self):
        src = "let n = 0\nrepeat forever\n n += 1\n if n is 2 then\n  skip\n stop\n if n is 4 then\n  break\n stop\n print n\nstop"
        self.assertEqual(lines(src), ["1", "3"])


class Lists(unittest.TestCase):
    def test_add_remove_sort_shuffle(self):
        src = 'let l = [3, 1]\nadd 2 to l\nremove 3 from l\nsort l descending\nprint l\nshuffle l\nprint length l'
        self.assertEqual(lines(src), ["[2, 1]", "2"])

    def test_add_text_and_variable(self):
        self.assertEqual(lines('let l = []\nlet v = 9\nadd v to l\nadd "hi" to l\nprint l'), ["[9, 'hi']"])

    def test_random_item(self):
        self.assertEqual(lines("let l = [7]\nprint random item l"), ["7"])


class ClassesAndModules(unittest.TestCase):
    CLASSES = (
        "class Animal\n function init(name) then\n  my.name = name\n stop\n"
        " function speak() then\n  say {my.name} is quiet\n stop\nstop\n"
        "class Dog extends Animal\n function speak() then\n  say {my.name} barks\n stop\nstop\n"
    )

    def test_classes_and_inheritance(self):
        self.assertEqual(lines(self.CLASSES + 'let d = Dog("Rex")\nd.speak()'), ["Rex barks"])
        self.assertEqual(lines(self.CLASSES + 'let a = Animal("Tom")\na.speak()'), ["Tom is quiet"])

    def test_top_level_function_unaffected_by_class(self):
        self.assertEqual(lines(self.CLASSES + "function f(x) then\n return x\nstop\nprint f(4)"), ["4"])

    def test_use_and_json(self):
        self.assertEqual(lines('use json\nuse sqrt from math\nprint json.dumps([1])\nprint sqrt(9)'), ["[1]", "3.0"])
        self.assertEqual(lines('let d = parsejson \'{"x": [1, 2]}\'\nprint d["x"][1]\nprint tojson [1]'), ["2", "[", "  1", "]"])

    def test_python_passthrough(self):
        self.assertEqual(lines("python print(sum(range(4)))"), ["6"])

    def test_assert_message(self):
        with self.assertRaises(AssertionError) as cm:
            run('assert 1 > 2, "nope"')
        self.assertIn("nope", str(cm.exception))


class Input(unittest.TestCase):
    def test_ask_text(self):
        self.assertEqual(run('ask "Name?" into n\nprint n', "Sam\n"), "Name? Sam\n")

    def test_ask_number_int_and_float(self):
        self.assertEqual(lines('ask number "n" into a\nprint a + 1', "4\n")[-1].split()[-1], "5")
        self.assertEqual(lines('ask number "n" into a\nprint a + 1', "1.5\n")[-1].split()[-1], "2.5")

    def test_classic_input_still_works(self):
        self.assertEqual(lines("input name prompt text Name?\nprint name", "Bo\n")[-1].split()[-1], "Bo")


class Errors(unittest.TestCase):
    def test_compile_error_has_line(self):
        with self.assertRaises(easy.EasyError) as cm:
            easy.compile_source("say hi\nfrobnicate now")
        self.assertEqual(cm.exception.line_num, 2)

    def test_unmatched_stop(self):
        with self.assertRaises(easy.EasyError):
            easy.compile_source("stop")

    def test_unclosed_block_is_incomplete(self):
        with self.assertRaises(easy.IncompleteBlock):
            easy.compile_source("if 1 > 0 then\n say hi")

    def test_runtime_error_maps_to_easy_line_inside_function(self):
        src = "function d(a, b) then\n return a / b\nstop\nsay start\nprint d(1, 0)"
        code, linemap = easy.compile_source(src)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                easy.run_code(code)
        except Exception as exc:
            self.assertEqual(easy.easy_line_of(exc, linemap), 2)
            msg, hint = easy.friendly_error(exc, {})
            self.assertIn("divide by zero", msg)
        else:
            self.fail("expected ZeroDivisionError")

    def test_name_error_suggests_close_match(self):
        msg, hint = easy.friendly_error(NameError("x", name="scroe"), {"score": 1})
        self.assertIn("score", hint)


class Tooling(unittest.TestCase):
    def test_linemap_aligned(self):
        code, linemap = easy.compile_source("say a\nsay b")
        self.assertEqual(len(code.splitlines()), len(linemap))
        self.assertEqual(linemap[-2:], [1, 2])

    def test_starter_template_compiles_and_runs(self):
        src = easy.STARTER_TEMPLATE.replace("{filename}", "x.easy")
        out = run(src, "Sam\n30\n")
        self.assertIn("Nice to meet you, Sam!", out)
        self.assertIn("You are an adult", out)
        self.assertIn("I like mango", out)

    def test_every_example_compiles(self):
        ex = os.path.join(os.path.dirname(__file__), "..", "examples")
        if os.path.isdir(ex):
            for f in sorted(os.listdir(ex)):
                if f.endswith(".easy"):
                    with open(os.path.join(ex, f), encoding="utf-8") as fh:
                        easy.compile_source(fh.read())

    def test_helpers_only_added_when_used(self):
        self.assertNotIn("_easy_range", easy.compile_language("say hi"))
        self.assertIn("def _easy_range", easy.compile_language("for n from 1 to 3\n say n\nstop"))

    def test_cli_main(self):
        self.assertEqual(easy.main(["commands"]), 0)


if __name__ == "__main__":
    unittest.main()
