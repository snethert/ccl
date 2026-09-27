# Startup execution plan (SEP-1)

Base: wasm2 `ba65583b` (P-3 final, READY 51.041 s). Scope: every cost that keeps
READY above the time the Lisp work itself needs, except guarded direct calls
(P-6/A-13), which stay excluded. This file is the only tracking record for the
plan; the executed diffs below are its evidence, not commits.

All runs: Node v25.6.1, `boot-final` + `final-bundles`, 32 MiB spaces,
`--timing` on, single runs, RAM disk, outputs deleted afterwards. Line numbers
are at `ba65583b`.

## 0. Evidence

### 0.1 Runs

| Run | Configuration | launch→READY | `lisp.run` | INSTALL-CODE | archive.admit | peak RSS |
|---|---|---:|---:|---:|---:|---:|
| base | `ba65583b` unchanged, from this worktree | 50.1 s | 40.8 s | 2.71 s | 2.23 s | 1.77 GiB |
| e1 | H-1 | 40.6 s | 31.5 s | 2.57 s | 2.21 s | 1.70 GiB |
| e2 | H-1 … H-5 | 34.5 s | 29.8 s | 0.91 s | 0.28 s | 1.66 GiB |
| e3 | e2 + archives relinked with C-3a/C-3b | 33.1 s | 28.4 s | 0.89 s | 0.30 s | 1.64 GiB |
| e0a | e2 + `--no-liftoff` | 98.8 s | 94.0 s | | | 2.47 GiB |
| e0b | e2 + `--wasm-tiering-budget=100000` | 35.4 s | 30.6 s | | | 2.83 GiB |

Every run reached READY with 81 returned loads, `boot0: true`, six collections.
e0a/e0b show that engine tiering is not a lever: forcing the optimizing tier
costs compile time and buys nothing; tiering earlier changes nothing.

### 0.2 Worker CPU at base (V8 sampling profile, 2 ms, 50.9 s sampled)

| Seconds | What |
|---:|---|
| 14.8 | compiled boot-tier bodies |
| 7.1 | compiled level-1 bodies |
| 7.6 | shared helpers: `stack_guard` 3.6, `resolve` 1.6, `object_base` 1.3 |
| 8.0 | LOAD observer around every boot function: `entered` 3.3, Wasm→JS transitions 3.0, wrapper 1.8 |
| 2.3 | JS SHA-256: per-function body digests 1.3, metadata digest 0.6, records 0.4 |
| 1.8 | `entries()` re-enumeration on every install |
| 3.0 | integer service: `new DataView` per access 1.2, buffer fetch 0.5, service Wasm 0.8 |
| 0.7 | timing journal `writeSync` per row |
| 0.6 | `structuredClone` of the 22 MB manifest |
| 0.5 | file client round trips (3,545 reads of 2 KiB) |

Hottest bodies (self time): `%FIND-PKG` 2.2 s, `REGISTER-ISTRUCT-CELL` 1.3 s,
`%SIMPLE-FASL-READ-BYTE` 1.2 s, l1-sort `MERGE-LISTS*` 1.2 s,
`%WASM-APPLICABLE-METHODS` 0.9 s, `MEMQ` 0.7 s, `%AREF1` 0.65 s.

### 0.3 The call census

Codex's traced witness (`final-ready/a.json`, identical workload) counts
**84,584,496 Lisp calls to READY**, 67.7 % in the boot tier. The largest:

| Calls | Function | Why it is a call |
|---:|---|---|
| 7,771,448 | `%AREF1` | untyped `aref` in the FASL byte reader and elsewhere |
| 5,776,554 | `%FASL-READ-BYTE` | funcall through `*fasl-api*` per byte |
| 5,776,554 | `%SIMPLE-FASL-READ-BYTE` | one call per FASL byte (5.75 MB) |
| 4,836,438 | `INSTANCE-SLOTS` | `declaim inline` not visible across files |
| 3,759,527 | `SEQUENCE-TYPE` | `seq-dispatch` inside `LENGTH`/`ELT` |
| 3,244,291 | `LISTP` | native compiler macro absent from the bootstrap set |
| 2,943,256 | `LENGTH` | ordinary call, dispatches through `SEQUENCE-TYPE` |
| 2,934,217 | `MEMQ` | ordinary call |
| 2,067,201 + 2,065,033 | `%CLASS-CPL`, `%INITED-CLASS-CPL` | per generic call |
| 1,587,402 | `NREVERSE` | per generic call (`SORT-METHODS`) |
| 1,580,031 + 1,214,955 | `CLASS-OF`, `%CLASS-OF-INSTANCE` | per generic call, per argument |
| 1,369,989 / 1,363,510 / 1,360,153 | `%FASL-DISPATCH`, `%EPUSHVAL`, `%FASL-EXPR` | one per FASL expression |
| 1,131,602 | `EQL-SPECIALIZER-P` | per generic call, per method |
| 1,124,606 / 950,982 / 894,885 / 494,717 | `INTEGERP`, `SYMBOLP`, `FIXNUMP`, `STRINGP` | native compiler macros absent |
| 690,749 | `REGISTER-ISTRUCT-CELL` | one per istruct cell reference in FASLs; `assq` over all cells |
| 613,127 / 439,296 | `%FASL-READ-COUNT`, `%FASL-READ-WORD` | byte loops |
| 395,796 × ~16 | `%WASM-STANDARD-GENERIC-CALL`, `%WASM-APPLICABLE-METHODS`, `ARGS-CPLS`, `SORT-METHODS`, `COMPUTE-METHOD-LIST`, `COMPUTE-ALLOWABLE-KEYWORDS-VECTOR`, … | no dispatch cache: every generic call recomputes applicability, sorts, and builds a combined closure |
| 230,476 | `%FIND-PKG` | one per package reference in FASLs; linear over packages × names with `aref` |

29.5 s of compiled code ÷ 84.6 M calls = 0.35 µs per call including its body.
Native CCL loads the same files in about one second because it makes a
fraction of these calls and each costs a few instructions. The plan therefore
cuts calls first (sections 2 and 3.1–3.2) and the cost of a call second (3.3–3.4).

### 0.4 After the executed changes (e3 profile, 33.5 s sampled)

Compiled Lisp 26.4 s (bodies 20.2, helpers 6.2), JS 4.3 s, integer service
1.4 s, idle 0.6 s. `%FIND-PKG` 2.0 s and `REGISTER-ISTRUCT-CELL` 1.2 s are the
two largest single bodies; `stack_guard` 2.5 s remains the largest helper.

## 1. Host side — executed, 50.1 s → 34.5 s

### H-1 Observer wraps every boot function (8.0 s)

`tests/wasm/stage1/loader-target/boot0.mjs` 429–446 instantiates the
`observe.wasm` wrapper around all 1,042 boot functions unconditionally; each
Lisp call then crosses into JS twice (`entered`, `returned`). Only four
functions feed the READY report: `%FASLOAD` (load events, handoff, completed
loads) and the three condition entries. Wrap those by default; `--trace` keeps
wrapping everything.

```js
// boot0.mjs, before the `for (const entry of installed.instances)` loop (429)
const codeOf = (pkg, name) => {
  const row = manifest.symbols.find(s => s.package === pkg && s.name === name); if (!row) return null;
  const fn = get(resolve(row.reference) + 6);
  return fn % 8 === 6 && get(fn - 6) === 1578 ? get(fn - 2) >>> 2 : null;
};
const observedCodes = new Set(workerData.trace ? codeSet.modules.map(m => m.code_id) :
  [['CCL', '%FASLOAD'], ['CCL', '%WASM-KERNEL-RESTART'], ['CCL', '%WASM-ERROR'], ['COMMON-LISP', 'INVOKE-DEBUGGER']]
    .map(([p, n]) => codeOf(p, n)).filter(Number.isInteger));
for (const entry of installed.instances) {
  const {record: row} = entry; let {instance} = entry;
  if (!observedCodes.has(row.code_id) && row.code_id !== workerData.inspectCode) {
    env.table.set(row.slot, instance.exports.entry); env.tail_table.set(row.slot, instance.exports.tail_entry); continue;
  }
  …existing wrapper path…
}
```

Measured: instrumentation `{modules: 1, instances: 3}` (INVOKE-DEBUGGER has no
boot definition), same 81 loads, READY 40.6 s. `terminalFailureChain` and
`recentFailures` now only see the wrapped functions on the ordinary path; the
traced path is unchanged. `retention-check.mjs` and the READY report's
instrumentation count expect 1,042 and must be updated to the selected set.

### H-2 `entries()` on every install (1.8 s + part of INSTALL-CODE)

`runtime/wasm32/target-load-session.mjs` 129–135 calls
`file.session.entries()` after each opcode-72 install; `code-archive.mjs` 186
rebuilds the entry list for every published unit of the file, so a file with
*n* units does *n²/2* entry constructions (l1-streams: 1,730 units). Return the
entries the install just published instead.

```js
// code-archive.mjs install(): return the published rows with the code id
   return {code:g.codeBase+unit.functions[0],published:entries(g,unit)};   // 160
   …the already-published branch returns {code:…,published:[]}              // 138
// target-code-service.mjs 64
    const installed = session.install(record[1], record, symbols);
    session.published?.(installed.published ?? []);
    return (installed.code ?? installed) * 4;
// target-load-session.mjs 101 and 129–135
    const session={install:…,entries:()=>archive.entries(token),published:rows=>{pending.newEntries=rows;}};
    …
    let entries;
    if(file.archive){entries=file.newEntries??[];file.newEntries=null;}
    else{entries=file.session.entries();v1Instances+=entries.length-file.installed;file.installed=entries.length;}
```

If Codex prefers to keep `install` returning a number (the archive checks call
it directly at `archive-check.mjs` 44–87 and `archive-controls.mjs` 98–100),
record the published rows on the session instead and expose
`entries(session, {newOnly: true})`; the measured effect is the same.

### H-3 JS digests and copies on the admission path (2.9 s)

- `code-archive.mjs` 96: `sha256(body)` in JS for all 10,891 function bodies
  (64 MB). The ranges are already bound to the parsed exports (`RANGE`, line
  93) and the full binary digest is verified natively; the per-body digest adds
  no binding. Replace with a shape check: `need(digest(row.body_sha256),'BODY_DIGEST')`.
  If the per-body binding is wanted, hash all bodies with one native
  `createHash` stream in Node and one `crypto.subtle.digest` per body in the
  async path; the loop as written is the cost.
- `boot0.mjs` 126: the 22 MB metadata digest in JS. Use the host hash
  (`createHash('sha256').update(new Uint8Array(message.metadata))`); the
  browser path already hashes asynchronously.
- `code-archive.mjs` 22: `structuredClone` of the manifest the receiver has
  just parsed and owns. Add `ownedManifest:true` from `target-load-session.mjs`
  61 and skip the clone when set.

### H-4 Integer service views (1.7 s)

`runtime/wasm32/integer-service.mjs` 14 builds `new DataView(memory.buffer)` on
every `get`/`set`; at launch the service is driven by `%STRING-HASH` (104,115 calls).
Keep one view per buffer identity:

```js
 let dv=new DataView(memory.buffer); // one view per buffer identity; growth replaces it
 const view=()=>dv.buffer===memory.buffer?dv:(dv=new DataView(memory.buffer)) …
```

The same pattern applies to `target-load-session.mjs` 71–72 and
`code-archive.mjs` 103 (`get`/`put` per access).

### H-5 Timing journal (0.7 s)

`startup-timing.mjs` 11 does one `writeSync` per row. Buffer 256 rows and flush
at checkpoints and `finish()`. This is measurement overhead, but the published
READY numbers include it.

### Gates to update with H-1…H-5

`archive-check.mjs`, `archive-controls.mjs` (install return shape or the
`newOnly` variant), `retention-check.mjs` and `ready-check.py` (instrumentation
instances 3, not 1,042), `archive-async-check.mjs` (no body-digest refusal
unless the native variant is kept). Identity gates only; no Wasm byte changes.

## 2. Lisp runtime — proposed, unexecuted

These change level-0 sources, so the boot image and every bundle rebuild. The
metric is the traced census (`--trace` witness) before and after: total calls
and the named counters below. Cross-compiler behaviour these rely on was
verified with a probe file: typed `aref` on a declared `(simple-array
(unsigned-byte 8) (*))` open-codes; untyped `aref`, `listp`, `fixnump`,
`symbolp`, `integerp`, `length` compile to calls; same-file `declaim inline`
expands.

### L-1 FASL byte path (`level-0/nfasload.lisp`) — 13.5 M calls → ≈0.5 M

Per byte today: `%fasl-read-byte` (1068) funcalls through `*fasl-api*` into
`%simple-fasl-read-byte` (96), which reads `(aref (svref buffer 0) index)`
untyped, so `%AREF1` is a third call. `%fasl-read-count` (136) and
`%fasl-read-word` (122) loop over that path; `%fasl-read-utf-8-string` (186)
reads symbol and string bytes the same way.

```lisp
;;; nfasload.lisp — wasm32 fast path. The API struct stays for the stream
;;; reader; the simple reader is recognised by identity and inlined.
#+wasm32-target
(defun %fasl-read-byte (s)
  (let* ((count (faslstate.bufcount s)))
    (declare (fixnum count))
    (if (and (> count 0) (eq (faslapi.fasl-read-byte *fasl-api*) #'%simple-fasl-read-byte))
      (let* ((buffer (faslstate.iobuffer s))
             (bytes (svref buffer 0))
             (index (svref buffer 1)))
        (declare (type (simple-array (unsigned-byte 8) (*)) bytes) (fixnum index))
        (setf (svref buffer 1) (the fixnum (1+ index))
              (faslstate.bufcount s) (the fixnum (1- count)))
        (aref bytes index))
      (funcall (faslapi.fasl-read-byte *fasl-api*) s))))

#+wasm32-target
(defun %simple-fasl-read-byte (s)
  (when (zerop (the fixnum (faslstate.bufcount s)))
    (%fasl-read-buffer s))
  (let* ((buffer (faslstate.iobuffer s))
         (bytes (svref buffer 0))
         (index (svref buffer 1)))
    (declare (type (simple-array (unsigned-byte 8) (*)) bytes) (fixnum index))
    (setf (svref buffer 1) (the fixnum (1+ index)))
    (decf (the fixnum (faslstate.bufcount s)))
    (aref bytes index)))

;;; Counts and words read whole from the buffer when it holds enough bytes.
#+wasm32-target
(defun %fasl-read-count (s)
  (let* ((buffer (faslstate.iobuffer s))
         (bytes (svref buffer 0))
         (index (svref buffer 1))
         (count (faslstate.bufcount s)))
    (declare (type (simple-array (unsigned-byte 8) (*)) bytes) (fixnum index count))
    (if (and (>= count 5) (eq (faslapi.fasl-read-byte *fasl-api*) #'%simple-fasl-read-byte))
      (let* ((val 0) (shift 0) (i index))
        (declare (fixnum val shift i))
        (loop
          (let* ((b (aref bytes i)))
            (declare (type (unsigned-byte 8) b))
            (incf i)
            (setq val (logior val (ash (logand b #x7f) shift)) shift (+ shift 7))
            (when (logbitp 7 b)
              (setf (svref buffer 1) i (faslstate.bufcount s) (- count (- i index)))
              (return val)))))
      (do* ((val 0) (shift 0 (+ shift 7)) (done nil)) (done val)
        (let* ((b (%fasl-read-byte s)))
          (declare (type (unsigned-byte 8) b))
          (setq done (logbitp 7 b) val (logior val (ash (logand b #x7f) shift))))))))
```

`%fasl-read-utf-8-string`'s `nextra = 0` branch becomes a `%copy-ivector-to-ivector`
of `nchars` bytes into the base string when the buffer holds them, otherwise the
existing loop; `%fasl-vreadstr` (232) already sizes the string.

The 29-bit fixnum arithmetic in `%fasl-read-count` stays within fixnum range for
the counts FASLs carry; Codex should keep the `(unsigned-byte 8)` declarations so
the backend's typed access (`bootstrap-typed-access`, backend 4366) applies.

### L-2 Package lookup (`nfasload.lisp` 391, 432) — 2.2 s

`%find-pkg` compares the name against every name of every package with `aref`
per character; `%fasl-vpackage` calls it 230,476 times at launch and the FASL
alternates among a handful of packages. Cache the last hit and verify it by a
single name comparison, so semantics under package renaming are unchanged.

```lisp
#+wasm32-target (defvar *fasl-package-cache* (cons nil nil)) ; (name-copy . package)
#+wasm32-target
(defun %fasl-find-pkg (str len)
  (declare (fixnum len))
  (let* ((cache *fasl-package-cache*) (name (car cache)) (p (cdr cache)))
    (if (and p (= len (the fixnum (length name)))
             (dotimes (i len t) (unless (eq (schar name i) (aref str i)) (return)))
             (memq p %all-packages%)
             (dolist (n (pkg.names p)) (when (and (= len (the fixnum (length n)))
                                                  (dotimes (i len t) (unless (eq (schar n i) (schar name i)) (return))))
                                         (return t))))
      p
      (let* ((found (%find-pkg str len)))
        (when found (setq *fasl-package-cache* (cons (%fasl-copystr str len) found)))
        found))))
;; %fasl-vpackage / %fasl-nvpackage: (%find-pkg str len) → (%fasl-find-pkg str len)
```

### L-3 istruct cell registration (`level-0/l0-pred.lisp` 1049, `nfasload.lisp` 912) — 1.3 s

`$fasl-istruct-cell` calls `register-istruct-cell` once per istruct reference
(690,749 at launch); each call is `assq` over the whole `*istruct-cells*` alist.
A small direct cache keeps the alist and its order untouched.

```lisp
#+wasm32-target (defvar *istruct-cell-cache* (make-array 16 :initial-element nil)) ; name, cell, name, cell…
#+wasm32-target
(defun register-istruct-cell (name)
  (let* ((cache *istruct-cell-cache*)
         (i (logand (ash (%%eqhash name) -3) 14)))
    (declare (fixnum i))
    (if (eq (%svref cache i) name)
      (%svref cache (1+ i))
      (let* ((cell (or (assq name *istruct-cells*)
                       (let* ((pair (cons name nil))) (push pair *istruct-cells*) pair))))
        (setf (%svref cache i) name (%svref cache (1+ i)) cell)
        cell))))
```

`%%eqhash` is the level-0 address hash; if it is not available before
`l0-hash`, use `(%svref cache 0)`/`(%svref cache 1)` as a one-entry cache with
the same shape.

### L-4 Generic-function dispatch cache (`level-0/WASM32/w32-prims.lisp` 535–585) — ≈16 M calls

`%wasm-standard-generic-call` recomputes applicable methods, sorts them, builds
the keyword vector and a fresh combined closure on every call: 395,796 generic
calls at launch, each ~16 supporting calls plus the sort. The file's own
comment says a cache can be added without changing the ABI. Key the cache on
the classes of the required arguments, store it in the entries region of the
existing dispatch table so `clear-gf-dispatch-table` (l1-dcode 662, run by
`compute-dcode` on every method or class change) invalidates it, and bypass it
for generic functions with EQL specializers.

```lisp
;;; w32-prims.lisp — dispatch cache in the gf dispatch table's entry region.
;;; Entry layout from %gf-dispatch-table-first-data: alternating key/value,
;;; key = list of the required arguments' classes, value = combined closure or
;;; effective method. clear-gf-dispatch-table resets the region to NIL.
(defun %wasm-gf-eql-specialized-p (gf)
  (dolist (m (%gf-methods gf) nil)
    (dolist (s (%method.specializers m))
      (when (typep s 'eql-specializer) (return-from %wasm-gf-eql-specialized-p t)))))

(defun %wasm-dispatch-cache-ref (dt classes)
  (let* ((i %gf-dispatch-table-first-data) (n (%gf-dispatch-table-size dt)))
    (declare (fixnum i n))
    (dotimes (j (ash n -1) nil)
      (let* ((key (%svref dt i)))
        (when (null key) (return nil))
        (when (do ((a key (cdr a)) (b classes (cdr b))) ((or (null a) (null b)) (and (null a) (null b)))
                (unless (eq (car a) (car b)) (return nil)))
          (return (%svref dt (1+ i)))))
      (incf i 2))))

(defun %wasm-dispatch-cache-set (dt classes value)
  (let* ((i %gf-dispatch-table-first-data) (n (%gf-dispatch-table-size dt)))
    (declare (fixnum i n))
    (dotimes (j (ash n -1))
      (when (null (%svref dt i))
        (setf (%svref dt i) classes (%svref dt (1+ i)) value)
        (return))
      (incf i 2))
    value)) ; table full: not cached, recomputed next time

(defun %wasm-standard-generic-call (gf args)
  (let* ((bits (inner-lfun-bits gf))
         (required (ldb $lfbits-numreq bits)) (optional (ldb $lfbits-numopt bits))
         (count (length args)))
    (when (< count required) (signal-program-error "Too few args to ~s" gf))
    (unless (or (<= count (+ required optional)) (logbitp $lfbits-rest-bit bits)
                (logbitp $lfbits-restv-bit bits) (logbitp $lfbits-keys-bit bits))
      (signal-program-error "Too many args to ~s" gf))
    (let* ((dt (%gf-dispatch-table gf))
           (cacheable (not (%wasm-gf-eql-specialized-p gf)))
           (classes (when cacheable (let* ((r nil) (a args)) (dotimes (i required (nreverse r)) (push (class-of (car a)) r) (setq a (cdr a))))))
           (combined (when cacheable (%wasm-dispatch-cache-ref dt classes))))
      (unless combined
        (setq combined (%wasm-compute-combined-method gf args)) ; the existing body of this function, returning the applicable closure or a keyword-checking wrapper
        (when (and cacheable combined) (%wasm-dispatch-cache-set dt classes combined)))
      (apply combined args))))
```

`%wasm-compute-combined-method` is the current function body from `methods`
downwards, returning `combined` (or the keyword-checking wrapper) instead of
applying it; `no-applicable-method` and non-standard method combinations
return uncached closures that apply directly. Correctness hinges on every path
that today calls `compute-dcode` still doing so; `add-method`,
`remove-method`, class finalization and `clear-gf-cache` already do.

### L-5 FASL read granularity (`xdump/faslenv.lisp` 46, `nfasload.lisp` 1109) — 3,545 → ≈110 host reads

`$fasl-buf-len` is 2048. The wasm32 reader allocates its own buffer at 1109
(`(make-array $fasl-buf-len …)`); give it a wasm32 constant of 65536 bytes.
Each read is a main-thread round trip (`file-client.mjs run`, 0.55 s).

## 3. Compiler — proposed; C-3a/C-3b executed as an archive rewrite

### C-1 Open-code the predicates and small accessors (`compiler/WASM32/wasm32-backend.lisp`) — ≈15 M calls

`bootstrap-compiler-macros` (3643) admits only `+ - * / min max make-string
make-array nth nthcdr proclaim assq char= … min-2 max-2 imin-2 imax-2`. The
native macros for `listp` (optimizers.lisp 1884), `fixnump` (1830), `symbolp`
(1869), `integerp` (2159), `stringp`/`base-string-p` (2131) expand to
`lisptag`/`fulltag`/`typecode` comparisons using `*target-backend*`'s arch
constants, which the backend already open-codes (4843–4846); they do no host
representation folding. `consp`, `endp`, `characterp`, `svref`, typed `aref`
and `uvsize` are already open-coded (4862, 4887, 4898).

```lisp
;; wasm32-backend.lisp 3648: extend the admitted set
(dolist (name '(+ - * / min max make-string make-array nth nthcdr proclaim ccl::assq
               char= char/= char< char<= char> char>=
               ccl::min-2 ccl::max-2 ccl::imin-2 ccl::imax-2
               listp fixnump symbolp integerp stringp ccl::base-string-p))
```

`memq` and `length` have no useful native macro. Open-code them in
`bootstrap-operator` (4677) next to `consp`: `memq` as a loop over `car`/`cdr`
with `eq`; `length` as a list walk when `listp`, falling back to the call for
vectors and improper lists (so the existing error path is untouched):

```lisp
;; in the b-call path (826/897): before emitting a dynamic call to a global
;; function, recognise two-argument MEMQ and one-argument LENGTH on a symbol callee
(defun bootstrap-inline-memq (item list)   ; both already evaluated into locals
  (b-wat "(block $done (result i32) (local.set ~a ~a) (loop $walk
    (br_if $done (i32.eq (local.get ~a) (i32.const 77825)))          ;; NIL: return NIL
    (if (i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 1)) (then (br $call)))  ;; not a cons: let MEMQ signal
    (if (i32.eq (i32.load offset=3 (local.get ~a)) ~a) (then (local.get ~a) (br $done)))
    (local.set ~a (i32.load offset=-1 (local.get ~a))) (br $walk)) (i32.const 77825))" …))
```

`$call` is the enclosing block that falls into the existing call sequence;
the cons layout (car at +3, cdr at −1 from the tagged pointer) is the one
`emit-cons-read` (72) uses. `SEQUENCE-TYPE`'s 3.8 M calls disappear with
`LENGTH`'s list path.

### C-2 Cross-file inline expansions (`wasm32-compile-file` 6484; `compiler/nx0.lisp` 1330) — 4.8 M calls

The probe shows same-file `declaim inline` works. `INSTANCE-SLOTS` is declared
inline in `l1-clos-boot.lisp` 44 and called 4.8 M times from other files
because the cross-compiler's host image holds no expansion for it
(`(assq 'ccl::instance-slots ccl::*nx-globally-inline*)` → NIL) and nothing in
the build records one. `nx-inline-expansion` consults `*nx-globally-inline*`
last (nx0.lisp 1347); populate it from the build.

```lisp
;;; compiler/WASM32/wasm32-bundle.lisp — retain inline expansions across files.
(defvar *wasm32-inline-expansions* nil)
(defun wasm32-note-inline-expansion (name lambda env)
  (when (and (ccl::lambda-expression-p lambda) (ccl::nx-declared-inline-p name env)
             (not (gethash name ccl::*nx1-alphatizers*)))
    (let* ((cell (assq name *wasm32-inline-expansions*)))
      (if cell (setf (cdr cell) lambda) (push (cons name lambda) *wasm32-inline-expansions*)))))

;; wasm32-compile-file: bind for the file
(let ((ccl::*nx-globally-inline* (append *wasm32-inline-expansions* ccl::*nx-globally-inline*))) …)

;; bundles driver, once per build: ccl::note-function-info (l1-readloop.lisp 646) is
;; the seam every %defun passes through in compile-file.
(let ((original #'ccl::note-function-info))
  (setf (fdefinition 'ccl::note-function-info)
        (lambda (name lambda env) (wasm32-note-inline-expansion name lambda env) (funcall original name lambda env))))
```

Bundles compile in load order, so definitions precede their cross-file
callers. The expansions inline only through `bootstrap-operator`; an expansion
the backend refuses stays a call, as today.

### C-3 Helpers (`b-stacks-runtime` 3099, `b-object-runtime` 1718)

C-3a **`stack_guard` fast path** (executed as an archive rewrite, e3). The
helper is called at least twice per call (caller reservation 812, callee
prologue 1487) and again per stack block; it re-checks the thread record's
alignment and ordering invariants every time. Return early when `end` lies in
`[base, limit − reserve]`; the full check remains the slow path, so refusals
are unchanged for every input the fast path does not accept.

```wat
;; after (local.set $reserve (i32.load offset=100 (global.get $tcr)))
(if (i32.and (i64.le_s (local.get $end)
                       (i64.sub (i64.extend_i32_u (local.get $limit)) (i64.extend_i32_u (local.get $reserve))))
             (i64.ge_u (local.get $end) (i64.extend_i32_u (local.get $base))))
  (then (return)))
```

The signed compare makes a corrupt `limit < reserve` fall through to the slow
path. The only behaviour the fast path skips is refusal of a thread record the
owner itself misaligned; the owner is its sole writer.

C-3b **`$span` inlined** in `resolve`, `object_base`, `function_value`
(executed, e3): replace each `(call $span P N)` with the extent test inline.
The helper stays for the bodies' own uses (`uvsize`).

C-3c **`resolve` for function objects** (1729): when the callee is a known
global function (`direct` at 908), the node is the symbol; today `resolve`
tag-checks, spans, header-checks, calls `function_value` (two more
`object_base`), then re-validates the function object. Emit a dedicated
`$resolve_symbol_function` that reads the fcell, checks the function header
once, and does the registry row check; identical refusals, fewer loads and no
nested helper calls.

Measured effect of a+b alone: 34.5 → 33.1 s. Helper trimming is worth having
but is not where the time is; C-1/C-2 and section 2 are.

### C-4 Call sequence (`b-internal-call` 897, body prologue 1483–1500, `b-entry-wrapper` 2107)

Per call today: caller saves five thread-record words, reserves with
`stack_guard`, writes an 8-word context and NIL-fills `2 + 4⌈n/4⌉` root cells,
stores self and arguments, runs `resolve_lisp` (a `try_table` around
`resolve`), stores four thread-record words, checks the tail slot twice,
`call_indirect`s; the callee loads five words, runs five frame checks (two in
i64), opens a `try_table`, reserves again with `stack_guard`, fills its own
roots, runs the body, bounds-checks the results, copies them with
`memory.copy`, restores seven words. Proposed, in order of value and safety:

- **C-4a exact root fill** (`b-runtime-roots` 816, called from 919): fill
  `2 + n` cells, not `2 + 4⌈n/4⌉`; the arguments are stored immediately after
  and the frame is already published, so rooting is unchanged.
- **C-4b single-value fast path** (933–934 and the body epilogue): when
  `count = 1`, store one word instead of `memory.copy`; multiple values keep
  the copy.
- **C-4c frame checks at the boundary only** (1487–1490 in `$body`; the six
  checks in `b-entry-wrapper` stay). `$body` is reachable only through the tail
  table, whose entries the loader sets from compiled modules and the host
  adapters; every caller has just built the context it is checking. Keeping
  the five checks costs ~30 instructions per call; dropping them is a policy
  decision Codex should make explicitly, since the plan's safety model is
  "trusted owner, checked boundary".
- **C-4d `resolve` once per constant callee** (C-3c) and the two tail-slot
  checks in `b-internal-dispatch` (893) folded into it.

## 4. Order, gates, exclusions

1. **Host (section 1)** — adopt as is; identity gates only. Expected READY
   ≈34 s (measured 34.5 s).
2. **Lisp runtime (section 2)** — L-1, L-2, L-3, L-5 change level-0 only;
   L-4 changes `w32-prims.lisp`. Rebuild boot and bundles; the traced census
   is the acceptance metric: L-1 removes ≈13 M calls, L-4 ≈16 M, L-2/L-3 remove
   3.5 s of self time. Existing native/R6 evidence stays qualified for the
   unchanged files; nfasload and w32-prims need fresh execution witnesses.
3. **Compiler (section 3)** — C-1 and C-2 first (they remove ≈20 M calls and
   need only the bootstrap front end and one build hook), then C-3c and C-4.
   Each compiler change regenerates every archive, so the equivalence gates
   (`archive-equivalence.mjs`, WAT witnesses) re-bind rather than compare
   against the current binaries.

Expected outcome, unverified: calls to READY from 84.6 M to ≈25–30 M, READY in
the 10–15 s range on this machine, with `%FIND-PKG`, the sort in `SORT-METHODS`
and the FASL expression loop as the remaining Lisp costs. The direct-call work
(P-6/A-13) sits on top of C-4 and is not part of this plan; engine flags are
not part of any plan.

Experiment outputs (`/private/tmp/ccl-work/claude/{base,e1,e2,e3,e0a,e0b,exp,probe,prof-*}`)
were deleted after the numbers above were recorded; the worktree carries none
of the patches, only this file.
