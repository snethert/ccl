/*
 * Runtime command SAB transport smoke test.
 *
 * This smoke is intentionally strict: it only passes if a real compiled-Lisp
 * runtime command pump emits `command.result` over the egress SAB lane.
 * No synthetic `KERNEL_OP_RUNTIME_EVENT` injection is used.
 */

import fsSync from "node:fs";
import fs from "node:fs/promises";
import assert from "node:assert/strict";
import * as zlib from "node:zlib";
import { fileURLToPath } from "node:url";

import {
  createMicrokernel,
  KERNEL_OP_RUNTIME_EVENT,
  KERNEL_OP_RUNTIME_COMMAND_POLL
} from "./microkernel.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "./sab-ring.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  decodeBundleBytesSync,
  instantiateWasm,
  installCompiledModulesFromBundle,
  installCompiledModulesFromRegistry,
  installConstPoolBytes,
  installSubprimsTable,
  resolveBundleEntries,
  storedLengthFor
} from "./ccl-loader.mjs";
import { createRuntimeCommandClient } from "../../../web-ui/src/runtime-command-client.mjs";
import { drainRuntimeSabMessages } from "../../../web-ui/src/runtime-sab-transport.mjs";
import {
  BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP,
  createBootstrapFunctionResolver,
  registerResolverFunctionsFromBundle,
  rewriteConstPoolFunctionDesignators,
  STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1
} from "./bootstrap-function-resolver.mjs";
import {
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1,
  STARTUP_SYMBOL_TO_ENTRY_FUNCTION_DESIGNATORS_PRE_TOPLEVEL_V1
} from "./bootstrap-contract.mjs";
import { WASM_BOOT_ENTRY_INDEX as BOOT_ENTRY_INDEX } from "./abi-constants.mjs";
import { ensureSubprimsMap } from "../lib/ensure-subprims-map.mjs";

const CSTACK_SIZE = 1 << 20;
const HEAP_RESERVE_BYTES = 4 << 20;
const RUN_TOPLEVEL_ATTEMPTS = 32;

function readFileUrl(url) {
  return fs.readFile(fileURLToPath(url));
}

const scriptUrl = import.meta.url;
const kernelBytes = await readFileUrl(new URL("../../../build/wasm32/kernel/wasmcl.wasm", scriptUrl));
const subprimsBytes = await readFileUrl(new URL("../../../build/wasm32/subprims/subprims.wasm", scriptUrl));
const rootImageBytes = await readFileUrl(new URL("../../../build/wasm32/images/minimal.image", scriptUrl));
const repoRoot = path.resolve(path.dirname(fileURLToPath(scriptUrl)), "../../..");
const subprimsMap = await ensureSubprimsMap(repoRoot);
const runtimeModulesBundle = JSON.parse(
  await fs.readFile(fileURLToPath(new URL("../../../build/wasm32/modules/wasm-smoke-modules.json", scriptUrl)), "utf8")
);
function normalizeDesignatorNameSet(values) {
  const out = new Set();
  for (const value of Array.isArray(values) ? values : []) {
    if (typeof value !== "string") continue;
    const normalized = value.trim().toUpperCase();
    if (!normalized) continue;
    out.add(normalized);
  }
  return out;
}

function bindingStateForGateFailure(reason) {
  switch (reason) {
    case "ambiguous":
      return "ambiguous-function-designator";
    case "phase-disabled":
      return "resolver-phase-disabled";
    case "missing-name":
      return "invalid-function-designator";
    default:
      return "unresolved-required-function-designator";
  }
}
const startupRequiredPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1?.phases?.["pre-toplevel"]?.requiredResolveOrFail ?? []
);
const startupDeferredPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1?.phases?.["pre-toplevel"]?.deferredAllowed ?? []
);
const startupSymbolToEntryPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_SYMBOL_TO_ENTRY_FUNCTION_DESIGNATORS_PRE_TOPLEVEL_V1
);
const bootstrapFunctionResolver = createBootstrapFunctionResolver({
  phase: BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP
});
registerResolverFunctionsFromBundle(bootstrapFunctionResolver, runtimeModulesBundle, {
  source: "runtime-modules-manifest.functions"
});

function runPreToplevelFunctionDesignatorGateOrThrow() {
  const requiredNames = Array.from(startupRequiredPreToplevelDesignators.values());
  if (requiredNames.length === 0) return;

  const failures = [];
  for (const symbolName of requiredNames) {
    const resolution = bootstrapFunctionResolver.resolveFunctionDesignator({ name: symbolName });
    const ok = Boolean(resolution?.ok);
    const reason = ok ? null : (resolution?.reason ?? "missing");
    const record = {
      schema_version: "startup_function_designator_gate_v1",
      phase: "pre-toplevel",
      status: ok ? "pass" : "fail",
      mode: "strict",
      symbol_name: symbolName,
      entry_index: ok ? (resolution.entryIndex >>> 0) : null,
      resolved_entry_index: ok ? (resolution.entryIndex >>> 0) : null,
      source: ok ? (resolution.source ?? null) : null,
      binding_state: ok ? "resolved-entry-function" : bindingStateForGateFailure(reason),
      reason
    };
    if (ok) {
      console.log(`STARTUP_FUNCTION_DESIGNATOR_GATE ${JSON.stringify(record)}`);
      continue;
    }
    failures.push(record);
    console.error(`STARTUP_FUNCTION_DESIGNATOR_GATE ${JSON.stringify(record)}`);
  }
  if (failures.length > 0) {
    throw new Error(
      `pre-toplevel function designator gate failed: ` +
      failures.map((item) => `${item.symbol_name}:${item.reason}`).join(",")
    );
  }
}
const runtimeModulesIndexBytes = await readFileUrl(
  new URL(`../${runtimeModulesBundle.index}`, scriptUrl)
);
const runtimeModulesBinaryPath = fileURLToPath(
  new URL(`../${runtimeModulesBundle.binary}`, scriptUrl)
);

let modulesHandle = null;
let modulesFd = null;
let runtimeCommandClient = null;

try {
  modulesHandle = await fs.open(runtimeModulesBinaryPath, "r");
  modulesFd = fsSync.openSync(runtimeModulesBinaryPath, "r");

  const constPoolEntries = new Map();
  const constPoolById = new Map();
  const constPoolSpanRefCounts = new Map();
  const constPoolSpanCache = new Map();
  const constPoolByIdCache = new Map();
  const constPoolDecodeInFlight = new Set();
  const constPoolsInstalled = new Set();

  let constPoolSharedBlobInfo = null;
  let constPoolSharedBlobRaw = null;

  const constPoolSpanKey = (offset, storedLength, encoding, rawLength) =>
    `${offset >>> 0}:${storedLength >>> 0}:${encoding ?? "raw"}:${rawLength >>> 0}`;

  const resolvedBundle = await resolveBundleEntries({
    bundle: runtimeModulesBundle,
    indexBytes: runtimeModulesIndexBytes
  });

  if (
    Number.isFinite(runtimeModulesBundle?.constPoolBlobOffset) &&
    Number.isFinite(runtimeModulesBundle?.constPoolBlobLength)
  ) {
    constPoolSharedBlobInfo = {
      offset: runtimeModulesBundle.constPoolBlobOffset >>> 0,
      length: runtimeModulesBundle.constPoolBlobLength >>> 0,
      storedLength: Number.isFinite(runtimeModulesBundle?.constPoolBlobStoredLength)
        ? runtimeModulesBundle.constPoolBlobStoredLength >>> 0
        : runtimeModulesBundle.constPoolBlobLength >>> 0,
      encoding: runtimeModulesBundle?.constPoolBlobEncoding ?? null
    };
  }

  for (const entry of Array.isArray(resolvedBundle?.modules) ? resolvedBundle.modules : []) {
    if (!Number.isFinite(entry?.entryIndex)) continue;
    if (!Number.isFinite(entry?.constPoolOffset) || !Number.isFinite(entry?.constPoolLength)) continue;

    const rawLength = entry.constPoolLength >>> 0;
    const storedLength = storedLengthFor(entry, "constPoolLength", "constPoolStoredLength");
    if (rawLength === 0 || storedLength === 0) continue;

    const encoding = entry.constPoolEncoding ?? null;
    const key = constPoolSpanKey(entry.constPoolOffset, storedLength, encoding, rawLength);
    const info = {
      offset: entry.constPoolOffset >>> 0,
      length: rawLength,
      storedLength,
      encoding,
      key,
      id: Number.isFinite(entry?.constPoolId) ? entry.constPoolId >>> 0 : null,
      baseId: Number.isFinite(entry?.constPoolDeltaBaseId) ? entry.constPoolDeltaBaseId >>> 0 : null,
      deltaOp: entry?.constPoolDeltaOp ?? null
    };
    constPoolEntries.set(entry.entryIndex >>> 0, info);
    if (info.id != null && !constPoolById.has(info.id)) {
      constPoolById.set(info.id, info);
    }
    constPoolSpanRefCounts.set(key, (constPoolSpanRefCounts.get(key) ?? 0) + 1);
  }

  function decodeConstPoolForInfo(info) {
    if (!info) return null;
    if (info.id != null && constPoolByIdCache.has(info.id)) {
      return constPoolByIdCache.get(info.id);
    }
    if (info.id != null) {
      if (constPoolDecodeInFlight.has(info.id)) return null;
      constPoolDecodeInFlight.add(info.id);
    }

    try {
      const shouldCache = (constPoolSpanRefCounts.get(info.key) ?? 0) > 1;
      let decodedBytes = null;
      if (shouldCache && constPoolSpanCache.has(info.key)) {
        decodedBytes = constPoolSpanCache.get(info.key);
      } else {
        if (constPoolSharedBlobInfo) {
          if (!constPoolSharedBlobRaw) {
            const sharedStored = Buffer.allocUnsafe(constPoolSharedBlobInfo.storedLength);
            let total = 0;
            while (total < constPoolSharedBlobInfo.storedLength) {
              const bytesRead = fsSync.readSync(
                modulesFd,
                sharedStored,
                total,
                constPoolSharedBlobInfo.storedLength - total,
                constPoolSharedBlobInfo.offset + total
              );
              if (bytesRead === 0) break;
              total += bytesRead;
            }
            if (total !== constPoolSharedBlobInfo.storedLength) return null;
            constPoolSharedBlobRaw = decodeBundleBytesSync(
              sharedStored,
              constPoolSharedBlobInfo.encoding,
              constPoolSharedBlobInfo.length,
              "const pool shared blob",
              zlib
            );
          }
          const start = info.offset >>> 0;
          const end = start + info.storedLength;
          if (end > constPoolSharedBlobRaw.length) return null;
          decodedBytes = decodeBundleBytesSync(
            constPoolSharedBlobRaw.subarray(start, end),
            info.encoding,
            info.length,
            "const pool",
            zlib
          );
        } else {
          const stored = Buffer.allocUnsafe(info.storedLength);
          let total = 0;
          while (total < info.storedLength) {
            const bytesRead = fsSync.readSync(
              modulesFd,
              stored,
              total,
              info.storedLength - total,
              info.offset + total
            );
            if (bytesRead === 0) break;
            total += bytesRead;
          }
          if (total !== info.storedLength) return null;
          decodedBytes = decodeBundleBytesSync(
            stored,
            info.encoding,
            info.length,
            "const pool",
            zlib
          );
        }
        if (shouldCache) {
          constPoolSpanCache.set(info.key, decodedBytes);
        }
      }

      if (info.baseId != null) {
        if (info.deltaOp !== "xor") return null;
        const baseInfo = constPoolById.get(info.baseId);
        if (!baseInfo) return null;
        const baseBytes = decodeConstPoolForInfo(baseInfo);
        if (!baseBytes || baseBytes.length !== decodedBytes.length) return null;
        const out = Buffer.allocUnsafe(decodedBytes.length);
        for (let i = 0; i < decodedBytes.length; i++) {
          out[i] = decodedBytes[i] ^ baseBytes[i];
        }
        decodedBytes = out;
      }

      if (info.id != null) {
        constPoolByIdCache.set(info.id, decodedBytes);
      }
      return decodedBytes;
    } finally {
      if (info.id != null) {
        constPoolDecodeInFlight.delete(info.id);
      }
    }
  }

  const runtime = createSharedCclRuntime({
    memoryInitialPages: 256,
    subprimsTableInitial: 256,
    createMemory: true
  });

  const commandIngressRing = createSabRing({ capacity: 65536 });
  const runtimeEgressRing = createSabRing({ capacity: 65536 });
  const traceEvents = [];

  let kernelExports = null;
  const hostDesignatorDecoder = new TextDecoder("utf-8");
  function decodeHostDesignatorString(rawPtr, rawLen) {
    const ptr = rawPtr >>> 0;
    const len = rawLen >>> 0;
    if (ptr === 0 || len === 0) return "";
    try {
      return hostDesignatorDecoder.decode(new Uint8Array(runtime.memory.buffer, ptr, len));
    } catch {
      return "";
    }
  }
  function resolveFunctionDesignatorEntryFromHost(namePtr, nameLen, packagePtr, packageLen) {
    const name = decodeHostDesignatorString(namePtr, nameLen);
    if (!name) return -1;
    const packageName = decodeHostDesignatorString(packagePtr, packageLen);
    const resolution = bootstrapFunctionResolver.resolveFunctionDesignator({ name, packageName });
    if (!resolution?.ok) return -1;
    return (resolution.entryIndex >>> 0) | 0;
  }
  function installConstPoolOnDemand(entryIndexRaw) {
    if (!kernelExports || modulesFd == null) return 0;
    const entryIndex = entryIndexRaw >>> 0;
    if (constPoolsInstalled.has(entryIndex)) return 1;
    const info = constPoolEntries.get(entryIndex);
    if (!info) return 0;
    const decodedBytes = decodeConstPoolForInfo(info);
    if (!decodedBytes) return 0;
    let payloadBytes = decodedBytes;
    let rewrite = null;
    try {
      rewrite = rewriteConstPoolFunctionDesignators(decodedBytes, {
        resolver: bootstrapFunctionResolver,
        entryIndex,
        requiredResolveOrFailNames: startupRequiredPreToplevelDesignators,
        deferredAllowedNames: startupDeferredPreToplevelDesignators,
        symbolToEntryFunctionNames: startupSymbolToEntryPreToplevelDesignators,
        symbolPackageOverrides: STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1
      });
      payloadBytes = rewrite.bytes;
    } catch (_err) {
      payloadBytes = decodedBytes;
    }
    if ((rewrite?.deferredUnresolvedCount ?? 0) > 0) {
      const diagnostics = Array.isArray(rewrite?.deferredUnresolved) ? rewrite.deferredUnresolved : [];
      for (const item of diagnostics) {
        console.log(
          `STARTUP_CONSTPOOL_FUNCTION_GATE ${JSON.stringify({
            schema_version: "startup_constpool_function_gate_v1",
            phase: "pre-toplevel",
            status: "deferred",
            mode: "strict",
            entry_index: entryIndex >>> 0,
            const_index: Number.isFinite(item?.constIndex) ? (item.constIndex >>> 0) : null,
            symbol_name: item?.name ?? null,
            package_name: item?.packageName ?? null,
            policy_class: item?.policyClass ?? "deferred-allowed",
            binding_state: item?.bindingState ?? "deferred-symbolic-function-designator",
            reason: item?.reason ?? "missing"
          })}`
        );
      }
    }
    if ((rewrite?.requiredUnresolvedCount ?? 0) > 0) {
      const diagnostics = Array.isArray(rewrite?.requiredUnresolved) ? rewrite.requiredUnresolved : [];
      for (const item of diagnostics) {
        console.error(
          `STARTUP_CONSTPOOL_FUNCTION_GATE ${JSON.stringify({
            schema_version: "startup_constpool_function_gate_v1",
            phase: "pre-toplevel",
            status: "fail",
            mode: "strict",
            entry_index: entryIndex >>> 0,
            const_index: Number.isFinite(item?.constIndex) ? (item.constIndex >>> 0) : null,
            symbol_name: item?.name ?? null,
            package_name: item?.packageName ?? null,
            policy_class: item?.policyClass ?? "required-resolve-or-fail",
            binding_state: item?.bindingState ?? "unresolved-required-function-designator",
            reason: item?.reason ?? "missing"
          })}`
        );
      }
      throw new Error(
        `startup const-pool function gate failed for entry ${entryIndex}: unresolved required designators=` +
        diagnostics.map((item) => String(item?.name ?? "")).filter(Boolean).join(",")
      );
    }
    if (entryIndex === 3712) {
      const head = Array.from(decodedBytes.subarray(0, Math.min(16, decodedBytes.length)));
      console.log(
        `DEBUG const-pool 3712 len=${decodedBytes.length} info.length=${info.length} stored=${info.storedLength} encoding=${info.encoding ?? "raw"} head=${head.join(",")}`
      );
    }
    const rc = installConstPoolBytes({
      kernelExports,
      memory: runtime.memory,
      entryIndex,
      constPoolBytes: payloadBytes
    });
    if (rc === 0) return 0;
    constPoolsInstalled.add(entryIndex);
    return 1;
  }

  const hostLogDecoder = new TextDecoder("utf-8");
  const wasmHostLog = (ptr, len) => {
    if (process.env.CCL_WASM_TRACE !== "1") return;
    try {
      const p = ptr >>> 0;
      const n = len >>> 0;
      const bytes = new Uint8Array(runtime.memory.buffer, p, n);
      const text = hostLogDecoder.decode(bytes);
      console.error(`[wasm_host_log] ${text.replace(/\s+$/u, "")}`);
    } catch (_err) {
      // Debug-only logging should never affect smoke behavior.
    }
  };
  const microkernel = createMicrokernel({
    memory: runtime.memory,
    writeStdout: () => {},
    writeStderr: () => {},
    traceRequests: (event) => traceEvents.push(event),
    runtimeBridge: {
      commandTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: commandIngressRing.sharedBuffer
      },
      eventTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: runtimeEgressRing.sharedBuffer
      }
    }
  });

  assert.equal(microkernel._debug.runtimeCommand.transport, SAB_RING_TRANSPORT, "command ingress uses sab ring");
  assert.equal(microkernel._debug.runtimeEvent.transport, SAB_RING_TRANSPORT, "event egress uses sab ring");

  const kernel = await instantiateWasm(
    kernelBytes,
    createCclImports({
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
      extra: {
        env: { wasm_host_log: wasmHostLog },
        ccl: {
          wasm_host_install_const_pool: installConstPoolOnDemand,
          wasm_host_resolve_function_designator_entry: resolveFunctionDesignatorEntryFromHost
        }
      }
    })
  );
  kernelExports = kernel.instance.exports;

  const subprims = await instantiateWasm(
    subprimsBytes,
    createCclImports({
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
      extra: {
        env: { wasm_host_log: wasmHostLog },
        ccl: {
          wasm_host_install_const_pool: installConstPoolOnDemand,
          wasm_host_resolve_function_designator_entry: resolveFunctionDesignatorEntryFromHost,
          ...kernel.instance.exports
        }
      }
    })
  );

  installSubprimsTable({
    table: runtime.subprimsTable,
    subprimsMap,
    providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }]
  });

  const ex = kernel.instance.exports;
  function installBootEntry() {
    assert.equal(typeof ex.wasm_boot_entry, "function", "missing wasm_boot_entry");
    if (runtime.subprimsTable.length <= BOOT_ENTRY_INDEX) {
      runtime.subprimsTable.grow(BOOT_ENTRY_INDEX - runtime.subprimsTable.length + 1);
    }
    runtime.subprimsTable.set(BOOT_ENTRY_INDEX, ex.wasm_boot_entry);
  }

  const imageLen = rootImageBytes.byteLength >>> 0;
  const pageSize = 65536;
  const needBytes = imageLen + CSTACK_SIZE + HEAP_RESERVE_BYTES;
  if (needBytes > runtime.memory.buffer.byteLength) {
    runtime.memory.grow(Math.ceil((needBytes - runtime.memory.buffer.byteLength) / pageSize));
  }

  const cstackBase = runtime.memory.buffer.byteLength;
  assert.equal(typeof ex.wasm_set_cstack_bounds, "function", "missing wasm_set_cstack_bounds");
  ex.wasm_set_cstack_bounds(cstackBase, CSTACK_SIZE);

  const blobBase = (cstackBase - CSTACK_SIZE - imageLen) & ~15;
  assert(blobBase >= 0, "insufficient memory to place root image");
  new Uint8Array(runtime.memory.buffer).set(rootImageBytes, blobBase);

  assert.equal(typeof ex.wasm_ccl_load_image, "function", "missing wasm_ccl_load_image");
  assert.equal(ex.wasm_ccl_load_image(blobBase, imageLen) | 0, 0, "load root image");
  if (typeof ex.wasm_reset_root_image_runtime_state === "function") {
    assert.equal(ex.wasm_reset_root_image_runtime_state() | 0, 0, "reset root image runtime state");
  }

  const modulesReader = async (offset, length) => {
    const size = length >>> 0;
    if (size === 0) return new Uint8Array(0);
    const buffer = Buffer.allocUnsafe(size);
    let total = 0;
    while (total < size) {
      const { bytesRead } = await modulesHandle.read(
        buffer,
        total,
        size - total,
        (offset >>> 0) + total
      );
      if (bytesRead === 0) break;
      total += bytesRead;
    }
    if (total !== size) {
      throw new Error(`short read from runtime modules binary: expected ${size}, got ${total}`);
    }
    return buffer;
  };

  const bundleInstall = await installCompiledModulesFromBundle({
    bundle: runtimeModulesBundle,
    binaryReader: modulesReader,
    indexBytes: runtimeModulesIndexBytes,
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    strict: true,
    installConstPools: false
  });
  assert(bundleInstall.installed > 0, "runtime modules bundle install yielded zero modules");

  const registryInstall = await installCompiledModulesFromRegistry({
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel
  });
  runPreToplevelFunctionDesignatorGateOrThrow();

  if (typeof ex.wasm_set_subprims_ready === "function") {
    ex.wasm_set_subprims_ready(1);
  }
  installBootEntry();
  const runEntry = ex.wasm_run_toplevel;
  assert.equal(typeof runEntry, "function", "missing wasm_run_toplevel entrypoint");

  runtimeCommandClient = createRuntimeCommandClient({
    timeoutMs: 0,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring: commandIngressRing
    }
  });

  let dispatched = null;
  let commandResultMessage = null;
  const runStatuses = [];
  let trapStack = null;
  let sawCommandPoll = false;

  const runToplevelOnce = () => {
    let runRc;
    try {
      runRc = runEntry() | 0;
    } catch (err) {
      runStatuses.push(`trap:${err?.message ?? String(err)}`);
      if (trapStack == null && err?.stack) {
        trapStack = String(err.stack);
      }
      return false;
    }
    runStatuses.push(String(runRc));

    const drained = drainRuntimeSabMessages(
      { transport: SAB_RING_TRANSPORT, ring: runtimeEgressRing },
      { maxMessages: 128 }
    );
    assert.equal(drained.errors.length, 0, "runtime->ui SAB payload decode");
    for (const message of drained.messages) {
      runtimeCommandClient.handleRuntimeMessage(message);
      if (dispatched &&
        message.kind === "command.result" &&
        message.payload?.invocationId === dispatched.runtimeInvocation.id
      ) {
        commandResultMessage = message;
      }
    }
    return true;
  };

  /*
   * First give Lisp a chance to enter the command pump without pending work.
   * Then always enqueue one real command so runtimes that only poll once work
   * exists are still exercised by this smoke.
   */
  for (let i = 0; i < RUN_TOPLEVEL_ATTEMPTS; i++) {
    if (!runToplevelOnce()) break;
    sawCommandPoll = traceEvents.some(
      (event) => event.phase === "request" && event.op === KERNEL_OP_RUNTIME_COMMAND_POLL
    );
    if (sawCommandPoll) break;
  }

  dispatched = runtimeCommandClient.dispatchTypedCommand(
    {
      id: "runtime.eval.form",
      title: "Eval Form",
      args: [{ name: "form", type: "string", required: true }]
    },
    {
      id: "inv-sab-smoke-lisp",
      args: { form: "(+ 20 22)" },
      source: "smoke"
    },
    {
      jobId: "job-sab-smoke",
      context: { package: "CL-USER" }
    }
  );
  assert.equal(dispatched.ok, true, "dispatch command.invoke via SAB ingress");
  assert.equal(dispatched.transport, SAB_RING_TRANSPORT, "runtime command client transport");
  void dispatched.promise.catch(() => {});

  if (dispatched) {
    for (let i = 0; i < RUN_TOPLEVEL_ATTEMPTS; i++) {
      if (!runToplevelOnce()) break;
      if (commandResultMessage) break;
    }
  }

  const runtimeCommandPollRequests = traceEvents.filter(
    (event) => event.phase === "request" && event.op === KERNEL_OP_RUNTIME_COMMAND_POLL
  ).length;
  const runtimeEventRequests = traceEvents.filter(
    (event) => event.phase === "request" && event.op === KERNEL_OP_RUNTIME_EVENT
  ).length;
  const requestOpHistogram = new Map();
  for (const event of traceEvents) {
    if (event?.phase !== "request") continue;
    const key = String(event.op);
    requestOpHistogram.set(key, (requestOpHistogram.get(key) ?? 0) + 1);
  }
  const requestOpsSummary = Array.from(requestOpHistogram.entries())
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([op, count]) => `${op}:${count}`)
    .join(",");

  if (!commandResultMessage) {
    const debugConstPool = {
      entry: null,
      phase: null,
      index: null,
      tag: null,
      offset: null
    };
    let probe3664 = null;
    let requireStructureTypeProbe = null;
    throw new Error(
      [
        "No compiled-Lisp command.result observed over SAB egress.",
        `runtime_command_poll requests: ${runtimeCommandPollRequests}`,
        `runtime_event requests: ${runtimeEventRequests}`,
        `request_ops: [${requestOpsSummary || "<none>"}]`,
        `dispatch_state: ${dispatched ? "sent" : "skipped(no initial runtime_command_poll)"}`,
        `wasm_run_toplevel statuses: [${runStatuses.join(", ")}]`,
        `bundle install: ${bundleInstall.installed}/${bundleInstall.count}`,
        `registry install: ${registryInstall.installed}/${registryInstall.count}`,
        `const_pool_debug entry=${debugConstPool.entry} phase=${debugConstPool.phase} index=${debugConstPool.index} tag=${debugConstPool.tag} offset=${debugConstPool.offset}`,
        probe3664
          ? `probe3664 fn=0x${probe3664.fn.toString(16)} fnSubtag=${probe3664.fnSubtag} fnEntry=${probe3664.fnEntry} fnName=${probe3664.fnName ?? "<none>"} token=0x${probe3664.token.toString(16)} tokenSubtag=${probe3664.tokenSubtag} tokenName=${probe3664.tokenName ?? "<none>"}`
          : "probe3664 <unavailable>",
        requireStructureTypeProbe
          ? `probeRequireStructureType sym=0x${requireStructureTypeProbe.sym.toString(16)} symSubtag=${requireStructureTypeProbe.symSubtag} fcell=0x${requireStructureTypeProbe.fcell.toString(16)} fcellSubtag=${requireStructureTypeProbe.fcellSubtag} fcellEntry=${requireStructureTypeProbe.fcellEntry}`
          : "probeRequireStructureType <unavailable>",
        trapStack ? `trap_stack: ${trapStack.replace(/\\s+/g, " ").trim()}` : "trap_stack: <none>"
      ].join(" ")
    );
  }

  assert(
    runtimeCommandPollRequests > 0,
    "expected Lisp to call KERNEL_OP_RUNTIME_COMMAND_POLL at least once"
  );
  assert(
    runtimeEventRequests > 0,
    "expected Lisp to call KERNEL_OP_RUNTIME_EVENT at least once"
  );

  assert(dispatched, "expected to dispatch after runtime command poll readiness");
  const settled = await dispatched.promise;
  assert.equal(settled.ok, true, "runtime command promise resolved");
  assert.equal(
    commandResultMessage.requestId,
    dispatched.runtimeInvocation.id,
    "Lisp requestId correlation uses invocation id"
  );
  assert.equal(settled.payload?.result?.valueSummary, "42", "Lisp eval result summary");

  console.log("PASS: runtime command SAB transport smoke (compiled Lisp roundtrip)");
} finally {
  if (runtimeCommandClient) {
    runtimeCommandClient.cancelAll("runtime-command-sab-smoke teardown");
  }
  if (modulesHandle) {
    await modulesHandle.close();
  }
  if (modulesFd != null) {
    fsSync.closeSync(modulesFd);
  }
}
