"""Bind every snapshot callback without rewriting historical selections.

Classification never supplies a closure proof. Final bootstrap admission still
needs implementation or exclusion records for every selected dependency.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
SELECTION=ROOT/'tests/wasm/stage1/startup-resets/selection.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# class, disposition, consumer/routing obligation. Existing selected literals
# and the five accepted configuration effects are derived separately below.
OPEN={
 0:('RT','REPLACEMENT_PROPOSED','Port GCTIME to collector statistics; join its generated consumer and owner into bootstrap.'),
 1:('RT','NO_LIVE_LISP_READER','Native kernel writes this buffer; the sole Lisp read is disabled by NOT-ANY-MORE. Prove native GC path excluded from selected image.'),
 2:('RT','REPLACEMENT_REQUIRED','Route consumers of kernel locks to D5 owner/coordination operations.'),
 3:('EXCL','EXCLUSION_REQUIRED','Exclude or replace native SELECT and its bitmap consumer in linux-files.lisp.'),
 4:('EXCL','EXCLUSION_REQUIRED','Exclude or replace native EXECVP descriptor-closing path; no invented descriptor-table limit.'),
 10:('HOST','NO_LIVE_LISP_READER','Only its definition refers to this symbol; no native timeval object in the port. Recheck selected compiled consumers.'),
 12:('RT','DEFERRED','LL20 initial-thread/TCR materialization and owner identity required.'),
 18:('DEFER','DEFERRED','Periodic tasks and interactive-stream flushing require scheduler/stream implementations.'),
 19:('HOST','IMPLEMENTATION_REQUIRED','Publish the owner-provided image namespace name.'),
 20:('HOST','IMPLEMENTATION_REQUIRED','Publish the owner-provided argument list as Lisp strings.'),
 21:('HOST','IMPLEMENTATION_REQUIRED','Publish a non-NIL home pathname under both providers.'),
 23:('HOST','IMPLEMENTATION_REQUIRED','Initialize HOME: and CCL: after the home pathname, in registry order.'),
 26:('RT','REVIEWED_PROPOSAL','Join reviewed RESET-WINNERS with complete poisoned publication control.'),
 27:('DEFER','WITHDRAWN_IMPLEMENTATION','Native interface database not loaded (outline §05). Require absent subsystem or no live handles; metadata need not be empty.'),
 30:('DEFER','DEFERRED','Static cons facility unscoped; no native-global pointer may survive image construction.'),
 31:('DEFER','DEFERRED','As ordinal 30: static cons free-list pointer excluded or replaced.'),
 32:('DEFER','DEFERRED','Saved application process revival belongs to image lifecycle/scheduler work.'),
}
def classify():
 selection=json.loads(SELECTION.read_text());rows=[]
 for r in selection['callbacks']:
  key=f"{r['group']}:{r['ordinal']}"
  if r['disposition']=='SELECTED_LITERAL_RESET':kind,status,owed='RT','ACCEPTED_EFFECT','Bind retained generated reset and completion into final bootstrap.'
  elif r['group']=='user_pointers' or r['ordinal'] in (6,8,9,13):kind,status,owed='HOST','ACCEPTED_EFFECT','Bind configuration R2 effect; cold/warm CPU cache and full-TCR checks.'
  else:kind,status,owed=OPEN[r['ordinal']]
  rows.append(dict(key=key,**{n:r[n] for n in ('group','ordinal','function','name','source','position')},classification=kind,providers={p:status for p in ('browser','node')},obligation=owed,closure='NOT_ESTABLISHED'))
 assert len(rows)==35 and len({r['key'] for r in rows})==35
 return dict(version=1,snapshot=selection['snapshot'],selection={'path':str(SELECTION.relative_to(ROOT)),'sha256':sha(SELECTION)},order='system_pointers ascending ordinal, then user_pointers ascending ordinal',callbacks=rows,scope='Callback snapshot only; 167-unit definition bodies, loader prerequisites and condition activation remain separate LL15 dependencies.')

def validate(manifest):
 if manifest!=classify():raise ValueError('classification identity or omitted callback')
 return {'callbacks':35,'accepted_effects':sum(r['providers']['browser']=='ACCEPTED_EFFECT' for r in manifest['callbacks']),
         'closure':'NOT_ESTABLISHED','scope':manifest['scope']}

if __name__=='__main__':
 path=Path(__file__).with_name('classification.json');path.write_text(json.dumps(classify(),indent=2)+'\n')
