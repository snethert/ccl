"""Small proposal over the integrated audit-149 compiler; no runtime change."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKET = ROOT.parent / 'ccl-evidence/2026-09-21-stage1-bootstrap-witnesses-r1/execution/compiled/proposal'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'
PRIMS = 'level-0/WASM32/w32-prims.lisp'


def generate():
    text = (ROOT / BACKEND).read_text()
    line = "          ((eq name 'ccl::assq) (bootstrap-assq forms))\n"
    assert text.count(line) == 1
    text = text.replace(line, '')
    start = text.index('(defun bootstrap-assq (forms)')
    end = text.index('(defun bootstrap-logical-call', start)
    text = text[:start] + text[end:]
    line = "        (ccl::*nx1-alphatizers* (bootstrap-alphatizers)))"
    assert text.count(line) == 1
    text = text.replace(line, "        (*macroexpand-hook* (bootstrap-macroexpand-hook))\n" + line)
    start = text.index('(defun bootstrap-alphatizers ()')
    return text[:start] + (HERE / 'handler-admission.lisp').read_text() + '\n' + text[start:]


def source_files(src):
    result = {row['path']: (ROOT / row['path']).read_text()
              for key in ('added', 'modified')
              for row in json.loads((PACKET / 'unit.json').read_text())[key]
              if row['path'].startswith('level-0/')}
    result[PRIMS] += '\n' + (HERE / 'assq.lisp').read_text()
    return result


def proposal(src, out):
    shutil.copytree(PACKET, out)
    manifest = json.loads((out / 'unit.json').read_text())
    changed = {BACKEND: generate(), **source_files(src)}
    for row in manifest['added'] + manifest['modified']:
        p = out / 'files' / row['path']
        p.write_bytes(changed[row['path']].encode() if row['path'] in changed
                      else (ROOT / row['path']).read_bytes())
        row['sha256' if 'sha256' in row else 'after'] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / 'unit.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def runtime_files():
    return {name: (ROOT / 'runtime/wasm32' / name).read_text()
            for name in ('collector.c', 'collector-owner.mjs')}
