"""Controls for the source-coverage lexer and analysis.

Positive cases must pass and every control must reject. The load-bearing
claim of this deliverable is a set of surface counts, so a lexer that
miscounts must fail here rather than silently shift a published number.

Exit status 0 = all positive cases passed and all controls rejected.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexer import scan, LexError  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

passed = []
failed = []


def case(name, ok, detail=""):
    (passed if ok else failed).append(name)
    print("  %-52s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "  <- " + detail))


def expect(name, text, **want):
    try:
        got = scan(text)
    except LexError as e:
        case(name, False, "unexpected LexError: %s" % e)
        return
    bad = {k: (v, got[k]) for k, v in want.items() if got[k] != v}
    case(name, not bad, "want/got %r" % bad)


def reject(name, text):
    try:
        scan(text)
    except LexError:
        case(name, True)
        return
    case(name, False, "accepted input that must be rejected")


print("positive lexical cases")
expect("plain top-level forms", "(a)\n(b)\n(c)\n", forms=3)
expect("nested forms are not top-level", "(a (b (c)))\n", forms=1, max_depth=3)
expect("paren inside string literal", '(a "))))")\n', forms=1)
expect("escaped quote inside string", '(a "say \\" here")\n(b)\n', forms=2)
expect("paren as character literal", "(a #\\( #\\) )\n(b)\n", forms=2)
expect("named character literal", "(a #\\Space #\\Newline)\n", forms=1)
expect("line comment hides parens", "(a) ; ((((\n(b)\n", forms=2)
expect("block comment hides parens", "#| (((( |#\n(a)\n", forms=1)
expect("nested block comment", "#| #| ( |# |#\n(a)\n", forms=1)
expect("multiple-escape symbol", "(a |))sym(( | b)\n", forms=1)
expect("reader conditional counted at depth 0", "#+x (a)\n(b)\n",
       forms=2, reader_cond=1, reader_cond_top=1)
expect("reader conditional counted when nested", "(a #+x b)\n",
       forms=1, reader_cond=1, reader_cond_top=0)
expect("read-time eval counted", "(a #.(b) #.(c))\n", forms=1, read_eval=2)
expect("semicolon inside string is not a comment", '(a ";") (b)\n', forms=2)

# Regressions. Both were real failures of the first lexer against pristine U1
# source, found by the whole-corpus strictness control below, not by design.
expect("escaped bar inside |sym| (l1-reader.lisp:2886)",
       "(nfunction |#\\|-reader| (lambda () 1))\n(b)\n", forms=2)
expect("bar-quoted sharpsign symbols (parse-ffi.lisp:1012)",
       "(|#| |##|)\n(b)\n", forms=2)
expect("single-escape outside bars", "(a b\\(c d)\n", forms=1)

print("\nrejection controls (a permissive lexer fails these)")
reject("unterminated string", '(a "no close\n')
reject("unterminated block comment", "#| open forever\n(a)\n")
reject("unterminated escaped symbol", "(a |no close\n")
reject("unbalanced close paren", "(a))\n")
reject("unbalanced open paren at EOF", "(a (b)\n")

print("\nagreement with the reviewed first source traversal")
# doc/WASM/stage0/source-traversal.md publishes 16 top-level forms accounted
# for through EOF in pristine U1 lib/dumplisp.lisp. An independent lexer that
# does not reproduce that number invalidates every other count here.
dump = os.path.join(ROOT, "lib", "dumplisp.lisp")
try:
    got = scan(open(dump, encoding="utf-8", errors="strict").read())["forms"]
    case("lib/dumplisp.lisp == 16 forms (source-traversal.md)", got == 16,
         "got %d" % got)
except (OSError, LexError) as e:
    case("lib/dumplisp.lisp == 16 forms (source-traversal.md)", False, str(e))

print("\nwhole-corpus strictness")
# Every analysed file must lex strictly. A file that needs the permissive
# path is a lexer gap, not a file to silently drop from the denominator.
bad = []
for sub in ("level-0", "level-1", "lib", "library", "compiler", "xdump", "tools"):
    for dp, _dn, fn in os.walk(os.path.join(ROOT, sub)):
        for f in fn:
            if not f.endswith(".lisp"):
                continue
            p = os.path.join(dp, f)
            try:
                scan(open(p, encoding="utf-8", errors="replace").read())
            except LexError as e:
                bad.append("%s: %s" % (os.path.relpath(p, ROOT), e))
case("all .lisp sources lex strictly", not bad,
     "%d file(s), first: %s" % (len(bad), bad[0] if bad else ""))

print("\nanalysis determinism")
out = [subprocess.run([sys.executable, os.path.join(HERE, "analyze.py"),
                       "--root", ROOT, "--stdout"],
                      capture_output=True, text=True).stdout for _ in range(2)]
case("two runs produce identical JSON", out[0] == out[1] and bool(out[0].strip()),
     "runs differ or produced no output")

print("\n%d passed, %d failed" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
