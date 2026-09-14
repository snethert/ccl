"""Minimal Common Lisp surface lexer for static source accounting.

This is deliberately *not* a reader. It resolves only the lexical structure
needed to count top-level forms and locate reader conditionals and read-time
evaluation sites: string literals, character literals, block and line comments,
multiple-escape symbols, and parenthesis depth.

It does not expand macros, evaluate ``#.``, select ``#+``/``#-`` branches or
resolve packages. Every count it produces is a surface count of pristine U1
source text, not a statement about what the compiler or loader does with it.
"""

import re

_HEAD = re.compile(r"\(\s*([^\s()'`,;\"]+)")


class LexError(ValueError):
    """Raised when the input cannot be lexed unambiguously."""


def scan(text, strict=True):
    """Lex ``text`` and return a dict of surface facts.

    Keys:
      ``forms``            top-level (depth-0) list forms
      ``heads``            the first token of each top-level list form
      ``reader_cond``      total ``#+``/``#-`` sites
      ``reader_cond_top``  ``#+``/``#-`` sites at depth 0
      ``read_eval``        total ``#.`` sites
      ``max_depth``        deepest parenthesis nesting reached

    With ``strict`` (the default) an unterminated string, block comment or
    escaped symbol, or a paren depth that closes below zero, raises
    ``LexError`` rather than returning a count derived from a guess.
    """
    i, n = 0, len(text)
    depth = max_depth = 0
    forms = reader_cond = reader_cond_top = read_eval = 0
    heads = []

    while i < n:
        c = text[i]

        if c == ";":
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue

        if c == "#" and text.startswith("#|", i):
            d, i = 1, i + 2
            while i < n and d:
                if text.startswith("#|", i):
                    d += 1
                    i += 2
                elif text.startswith("|#", i):
                    d -= 1
                    i += 2
                else:
                    i += 1
            if d and strict:
                raise LexError("unterminated #| block comment")
            continue

        # #\c, #\Space, #\( -- the character itself is never a delimiter.
        if c == "#" and text.startswith("#\\", i):
            i += 2
            if i < n:
                i += 1  # the character proper, whatever it is
                while i < n and (text[i].isalnum() or text[i] in "-_"):
                    i += 1
            elif strict:
                raise LexError("truncated #\\ character literal")
            continue

        if c == '"':
            i += 1
            closed = False
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    closed = True
                    break
                i += 1
            if not closed and strict:
                raise LexError("unterminated string literal")
            continue

        # Multiple-escape. Inside |...| a backslash is a single-escape, so
        # "\\|" is a literal bar and does not terminate the symbol. CCL relies
        # on this: level-1/l1-reader.lisp names a function |#\\|-reader|.
        if c == "|":
            i += 1
            closed = False
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "|":
                    i += 1
                    closed = True
                    break
                i += 1
            if not closed and strict:
                raise LexError("unterminated |escaped symbol|")
            continue

        # Single-escape outside bars: the next character is part of a symbol,
        # never a delimiter or a macro character.
        if c == "\\":
            i += 2
            continue

        if c == "#" and i + 1 < n and text[i + 1] in "+-":
            reader_cond += 1
            if depth == 0:
                reader_cond_top += 1
            i += 2
            continue

        if c == "#" and i + 1 < n and text[i + 1] == ".":
            read_eval += 1
            i += 2
            continue

        if c == "(":
            if depth == 0:
                forms += 1
                m = _HEAD.match(text, i)
                heads.append(m.group(1).lower() if m else "?")
            depth += 1
            max_depth = max(max_depth, depth)
            i += 1
            continue

        if c == ")":
            depth -= 1
            if depth < 0:
                if strict:
                    raise LexError("unbalanced close paren")
                depth = 0
            i += 1
            continue

        i += 1

    if strict and depth != 0:
        raise LexError("unbalanced open paren at EOF (depth %d)" % depth)

    return {
        "forms": forms,
        "heads": heads,
        "reader_cond": reader_cond,
        "reader_cond_top": reader_cond_top,
        "read_eval": read_eval,
        "max_depth": max_depth,
    }
