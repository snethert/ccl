"""Apply a unified patch only when every context line and count matches."""
import re

def apply(result, patch):
    result = dict(result)
    lines = patch.read_text().splitlines(keepends=True)
    i = 0
    while i < len(lines):
        assert lines[i].startswith('--- a/')
        name = lines[i][6:].strip()
        assert lines[i + 1] == '+++ b/' + name + '\n' and name in result
        old, output, cursor = result[name].splitlines(keepends=True), [], 0
        i += 2
        while i < len(lines) and lines[i].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[i])
            assert match, lines[i]
            start, removed, added = int(match[1]) - 1, int(match[2] or 1), int(match[4] or 1)
            assert start >= cursor
            output.extend(old[cursor:start]); cursor = start; i += 1
            before = after = 0
            while i < len(lines) and not lines[i].startswith(('@@ ', '--- a/')):
                mark, body = lines[i][0], lines[i][1:]
                assert mark in ' +-'
                if mark in ' -':
                    assert old[cursor] == body, (name, cursor)
                    cursor += 1; before += 1
                if mark in ' +':
                    output.append(body); after += 1
                i += 1
            assert (before, after) == (removed, added)
        output.extend(old[cursor:]); result[name] = ''.join(output)
    return result

