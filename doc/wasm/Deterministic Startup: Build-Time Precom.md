Deterministic Startup: Build-Time Precomputation for Fast Launch
Design Principle
Launch speed is paramount. Build can take days. Every millisecond of dynamic work at launch that could have been done at build time is a design failure. The goal: webrunner instantiation is a deterministic apply-and-verify sequence with zero scanning, zero parsing, zero symbol resolution.

Context
The WASM port currently does significant dynamic work at launch:

Scans subprims exports and matches them to table slots
Parses module bundle JSON + binary index to discover metadata
Resolves function designators by scanning const pools
Relocates all pointer cells in the image (O(n) walk)
Cold-load functions never execute → B9/B10 class bugs
All of this should happen at build time. The root.image + startup-plan artifact should make launch a tight loop of instantiate-and-place with no decisions.

Architecture: Two Build-Time Artifacts
1. root.image — Fully Initialized Heap
The saved image contains ALL initialization effects:

Cold-load functions executed (B9/B10 fixed)
System locks created
Package hash tables resized
Class cells populated
Binding indices updated
Level-1 FASL code loaded
At launch, root.image is loaded and ready. No init work needed.

2. startup-plan.json — Deterministic Launch Plan
Generated at build time alongside root.image. Contains everything the JS launcher needs to bring up the Lisp without any scanning or resolution:


{
  "schemaVersion": "startup-plan-v1",
  "buildHash": "sha256:...",

  "memory": {
    "initialPages": 4096,
    "imageBase": 268435456,
    "imageSize": 52428800,
    "cstackSize": 1048576
  },

  "subprims": [
    { "index": 0, "export": "_SPfuncall", "source": "subprims" },
    ...
  ],

  "modules": [
    {
      "entryIndex": 200,
      "binaryOffset": 0,
      "binaryLength": 1024,
      "binaryEncoding": "gzip",
      "constPool": { "id": 3, "offset": 8192, "length": 512 }
    },
    ...
  ],

  "toplevelEntryIndex": 5842,

  "designators": {
    "TOPLEVEL": 5842,
    "RUN-READ-LOOP": 5200,
    "RUNTIME-BRIDGE-PUMP-COMMANDS": 5100
  }
}
Implementation: Three Phases
Phase 1: Cold-Boot Init (Correctness Fix)
Problem: make-real-image.mjs never calls %toplevel-function%, so cold-load functions never execute. This causes B9 (*FASL-API* NIL), B10 (PATHNAME-ENCODING-NAME undefined), and ~10 more missing inits.

Fix: Extract init steps into callable function, invoke from C during image construction, bake results into root.image.

File 1: level-0/nfasload.lisp
Extract steps 1-8 from the %toplevel-function% lambda (lines 1243-1284) into a named function:


(defun %run-cold-boot-init ()
  (declare (special *xload-cold-load-functions*
                    *xload-cold-load-documentation*
                    *early-class-cells*))
  (%wasm-note-startup-step 10)
  (%set-tcr-toplevel-function (%current-tcr) nil)
  (%wasm-note-startup-step 20)
  (setq %system-locks% (%cons-population nil))
  (%wasm-note-startup-step 30)
  (setq %all-packages-lock% (make-read-write-lock))
  (%wasm-note-startup-step 40)
  (dolist (f (prog1 *xload-cold-load-functions* (setq *xload-cold-load-functions* nil)))
    (funcall f))
  (%wasm-note-startup-step 50)
  (dolist (pair (prog1 *early-class-cells* (setq *early-class-cells* nil)))
    (setf (gethash (car pair) %find-classes%) (cdr pair)))
  (%wasm-note-startup-step 60)
  (dolist (p %all-packages%)
    (%resize-htab (pkg.itab p))
    (%resize-htab (pkg.etab p)))
  (%wasm-note-startup-step 70)
  (dolist (f (prog1 *xload-cold-load-documentation* (setq *xload-cold-load-documentation* nil)))
    (apply 'set-documentation f))
  (%wasm-note-startup-step 80)
  (let* ((max 0))
    (%map-areas #'(lambda (symvec)
                    (when (= (the fixnum (typecode symvec)) target::subtag-symbol)
                      (let* ((s (symvector->symptr symvec))
                             (idx (symbol-binding-index s)))
                        (when (> idx 0) (cold-load-binding-index s))
                        (when (> idx max) (setq max idx))))))
    (%set-binding-index max))
  (%wasm-note-startup-step 90))

(defvar %toplevel-function%
  #'(lambda ()
      (declare (special *xload-startup-file*))
      (%run-cold-boot-init)
      (%fasload *xload-startup-file*)))
Idempotent — each list is cleared after processing. Native CCL cold boot unaffected.

File 2: lisp-kernel/wasm-kernel-stubs.c
Add wasm_run_cold_boot_init() export (follows wasm_restore_lisp_pointers pattern at lines 3060-3100):


__attribute__((used, visibility("default"), export_name("wasm_run_cold_boot_init")))
int wasm_run_cold_boot_init(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (!tcr) return -1;
  if (!wasm_subprims_ready) return -2;

  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
  if (ccl_pkg == lisp_nil) return -3;

  static const uint8_t fn_name[] = "%RUN-COLD-BOOT-INIT";
  LispObj sym = wasm_find_symbol_named_bytes(fn_name, (uint32_t)(sizeof(fn_name) - 1), ccl_pkg);
  if (sym == (LispObj)0) return -4;

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  LispObj fn = rawsym->fcell;
  if (fn == lisp_nil || fn == nrs_UDF.vcell) return -5;

  natural old = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn;
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  int result = tcr->wasm_pending_throw ? (tcr->wasm_pending_throw = 0, -6) : 0;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old);
  return result;
}
Also: remove B9 hack (lines 4195-4266 in wasm_fasload_path).

File 3: scripts/wasm/lib/make-real-image.mjs
Call cold-boot init after module installation, before FASL loading (~line 1225):


const coldBootRc = ex.wasm_run_cold_boot_init() | 0;
if (coldBootRc !== 0) fail(`wasm_run_cold_boot_init returned ${coldBootRc}`);
trace("cold-boot-init complete");
Also: remove B3 table diagnostics (lines 1202-1224).

Phase 2: Startup-Plan Artifact Generation
Goal: At the end of make-real-image.mjs, emit startup-plan.json containing everything the runtime launcher needs. No scanning, no parsing at launch.

File: scripts/wasm/lib/make-real-image.mjs (extend)
After saving root.image, generate the startup plan from data already in memory:


const startupPlan = {
  schemaVersion: "startup-plan-v1",
  generatedAt: new Date().toISOString(),

  // Image placement — from actual build values
  image: {
    path: rootImagePath,
    size: imageBytes.length,
    sha256: imageSha256,
    savedBase: actualImageBase,  // from wasm_get_image_base() or header
  },

  // Subprims — from subprims-map.json already loaded
  subprims: subprimsMap.symbols.map((sym, i) => ({
    index: i,
    export: sym,
    source: subprimsInstance.exports[sym] ? "subprims" : "kernel"
  })),

  // Compiled modules — from bundle metadata already parsed
  modules: compiledModulesBundle.functions.map(fn => ({
    entryIndex: fn.entryIndex,
    exportName: fn.name || `${compiledModulesBundle.exportNameTemplatePrefix}${fn.entryIndex}`,
    binaryOffset: fn.offset ?? null,
    binaryLength: fn.length ?? null,
    binaryStoredLength: fn.storedLength ?? null,
    binaryEncoding: fn.encoding ?? null,
    constPoolId: fn.constPoolId ?? null,
    constPoolOffset: fn.constPoolOffset ?? null,
    constPoolLength: fn.constPoolLength ?? null,
  })),

  // Key entry points
  toplevelEntryIndex,

  // Function designator pre-resolution
  designators: Object.fromEntries(
    compiledModulesBundle.functions
      .filter(f => f.name && ["TOPLEVEL", "RUN-READ-LOOP",
              "RUNTIME-BRIDGE-PUMP-COMMANDS"].includes(f.name))
      .map(f => [f.name, f.entryIndex])
  ),

  // Build provenance for validation
  artifacts: {
    kernelWasm: { sha256: kernelSha256 },
    subprimsWasm: { sha256: subprimsSha256 },
    modulesBinary: { sha256: modulesBinarySha256 },
  }
};

await fs.writeFile(
  path.join(outputDir, "startup-plan.json"),
  JSON.stringify(startupPlan, null, 2)
);
File: scripts/wasm/lib/make-real-image.mjs (extend root manifest)
Add startup-plan reference to root.image.manifest.json:


manifest.artifacts.startupPlan = {
  path: "startup-plan.json",
  sha256: startupPlanSha256,
  schemaVersion: "startup-plan-v1"
};
Phase 3: Deterministic Launcher (Consumes Startup Plan)
Goal: Rewrite the runtime launcher (load-image.mjs) to consume startup-plan.json instead of dynamically computing everything.

File: scripts/wasm/lib/load-image.mjs (modify)
Replace dynamic scanning with plan-driven execution:

Subprims installation — replace provider scan with direct assignment:


// Before: scans providers in priority order
// After: direct from plan
for (const entry of plan.subprims) {
  const fn = (entry.source === "subprims" ? subprimsExports : kernelExports)[entry.export];
  if (fn) table.set(entry.index, fn);
}
Module installation — replace bundle parsing with plan-driven loop:


// Before: parse JSON, decode binary index, resolve spans
// After: offsets/lengths from plan, just load and install
for (const mod of plan.modules) {
  const wasmBytes = modulesBinary.slice(mod.binaryOffset, mod.binaryOffset + mod.binaryLength);
  // decompress if needed, instantiate, install
  const instance = await WebAssembly.instantiate(wasmBytes, imports);
  table.set(mod.entryIndex, instance.exports[mod.exportName]);
  if (mod.constPoolId != null) {
    kernel.exports.wasm_const_pool_install(mod.entryIndex, poolPtr, poolLen);
  }
}
Function designator resolution — precomputed in plan:


// Before: scan const pools, resolve symbols, rewrite
// After: direct from plan
kernel.exports.wasm_set_toplfunc_entry(plan.toplevelEntryIndex);
Artifact validation — hash check at load, not re-derivation:


// Validate that loaded artifacts match plan provenance
if (sha256(kernelBytes) !== plan.artifacts.kernelWasm.sha256) {
  fail("kernel WASM hash mismatch — rebuild required");
}
Phase 4: Relocation Elimination (Future)
Goal: Zero-bias image loading — skip the O(n) pointer relocation walk entirely.

Approach: Two-phase build:

Build kernel first → measure __heap_base value
Set boot image base = __heap_base in xdump/xwasmfasload.lisp:76
Rebuild boot image with matching base → bias = 0 at load
File: xdump/xwasmfasload.lisp
Change :image-base-address #x10000000 to a value derived from the kernel's __heap_base.

File: scripts/wasm/rebuild-everything.sh
Add step between kernel build and boot image build:


# Extract __heap_base from compiled kernel
HEAP_BASE=$(wasm-objdump -x build/wasm32/wasmcl.wasm | grep __heap_base | awk '{print $NF}')
# Pass to boot image builder
Constraints:

__heap_base shifts if kernel size changes (re-alignment needed)
Requires linker-stable __heap_base between kernel build and image build (same build session = OK)
Fallback: if bias ≠ 0, relocation still works (graceful degradation)
Implementation Order
Phase	What	Why	Files
1	Cold-boot init	Correctness: fixes B9/B10, unblocks FASL loading	nfasload.lisp, wasm-kernel-stubs.c, make-real-image.mjs
2	Startup-plan generation	Foundation: emits the artifact consumed by Phase 3	make-real-image.mjs
3	Plan-driven launcher	Launch speed: eliminates scanning/parsing at runtime	load-image.mjs, ccl-loader.mjs
4	Relocation elimination	Launch speed: skips O(n) pointer walk	xwasmfasload.lisp, rebuild-everything.sh
Phase 1 is the critical path (blocks all progress). Phase 2 is low-risk (additive). Phase 3 is the big launch-speed win. Phase 4 is independent optimization.

Constraint: Dynamic Compilation
The Lisp compiler produces new WASM function modules at runtime. Individual function table entries may be replaced by the kernel when the compiler recompiles a function. The startup plan describes the initial state at launch, not a permanent layout.

This means:

The function table must remain growable (WebAssembly.Table with no fixed maximum)
table.set(entryIndex, newFn) must work at any time after launch
New const pools can be installed via wasm_const_pool_install() at runtime
The startup plan does NOT lock down the table — it only provides the initial population
Phase 3 launcher must leave all table/memory management APIs accessible to the kernel
Verification
Phase 1 Verification

scripts/wasm/rebuild-everything.sh
Expected: cold-boot-init: ok, all 35 FASL files load, no B9/B10 errors.

Phase 2 Verification
Check build/wasm32/startup-plan.json contains valid module/subprim/designator data.

Phase 3 Verification
Launch a webrunner from root.image using the startup-plan-driven loader. Measure launch time before/after. Target: no JSON parsing, no bundle index decoding, no symbol scanning at launch.

Phase 4 Verification
Check bias = 0 in image load log. Confirm relocation loop is skipped.