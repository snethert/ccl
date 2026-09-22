"""Ensure the new observers distinguish identity and pre-call input state."""
from pathlib import Path
import json, subprocess, sys
HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
source = (out / 'check.mjs').read_text()
needle = "JSON.parse(fs.readFileSync(dir+'/compiled/native.json')),rows=[];"
assert source.count(needle) == 1
faults = [
    ('missing-backpointer', 'INSTANCE-SLOTS',
     "native.forEach(r=>r.args.forEach(x=>{if(x.instance)x.instance.backpointer=false;}));"),
    ('post-call-input', 'MULTI-METHOD-INDEX',
     "native.forEach(r=>{r.args=r.after;});"),
]
rows = []
for name, definition, mutation in faults:
    selected = ("JSON.parse(fs.readFileSync(dir+'/compiled/native.json'))"
                f".filter(r=>r.definition==={json.dumps(definition)}),rows=[];" + mutation)
    path = out / (name + '.mjs')
    path.write_text(source.replace(needle, selected))
    result = subprocess.run(['/usr/local/bin/node', path, out, out / (name + '.json')],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    (out / (name + '.log')).write_text(result.stdout)
    assert result.returncode and 'AssertionError' in result.stdout and definition in result.stdout, name
    assert 'RuntimeError: memory access' not in result.stdout, name
    rows.append(dict(name=name, definition=definition, rejected=True))
(out / 'clos-controls.json').write_text(json.dumps(dict(status='PASS', rows=rows), indent=2)+'\n')
print('PASS: two transport faults rejected by the new execution cases')
