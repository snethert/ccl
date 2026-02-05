/*
 * Reference "world/runner" microkernel layer.
 *
 * This composes the per-runner kernel_request microkernel with a simple
 * world/runner/image lifecycle manager. It is intentionally minimal and
 * designed for bring-up and tests, not production deployments.
 */

import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installCompiledModulesFromRegistry,
  installCompiledModulesFromRegistrySync,
  installSubprimsTable,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

function normalizeBytes(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  throw new TypeError("expected Uint8Array/ArrayBuffer/view");
}

const REQUIRED_SUBPRIMS = ["_SPmkcatch1v", "_SPfuncall", "_SPnthrow1value"];

function hasRequiredSubprims(exports) {
  return REQUIRED_SUBPRIMS.every((name) => typeof exports?.[name] === "function");
}

function setSubprimsReady(kernel, ready) {
  const fn = kernel?.instance?.exports?.wasm_set_subprims_ready;
  if (typeof fn === "function") {
    fn(ready ? 1 : 0);
  }
}

export function createKernel({
  kernelBytes,
  subprimsBytes = null,
  subprimsMap = null,
  memoryInitialPages = 256,
  memoryMaximumPages = undefined,
  subprimsTableInitial = 256,
  subprimsTableMaximum = undefined,
  cstackSize = 1 << 20, // 1 MiB
  reserveBytes = 4 << 20, // scratch/heap slack
  asyncStdin = false,
  namedBytes = null,
  writeStdout,
  writeStderr,
  logSink = null,
  now = () => Date.now(),
} = {}) {
  if (!kernelBytes) {
    throw new Error("createKernel: kernelBytes is required");
  }
  if (subprimsBytes && !subprimsMap) {
    throw new Error("createKernel: subprimsMap is required when subprimsBytes is provided");
  }

  let nextWorldId = 1;
  let nextRunnerId = 1;
  let nextImageId = 1;

  const images = new Map(); // imageId -> Uint8Array
  const worlds = new Map(); // worldId -> { id, imageId, runners:Set }
  const runners = new Map(); // runnerId -> runner object

  function registerImage(imageIdOrBytes, maybeBytes) {
    let imageId = imageIdOrBytes;
    let imageBytes = maybeBytes;
    if (maybeBytes === undefined) {
      imageBytes = imageIdOrBytes;
      imageId = `image-${nextImageId++}`;
    }
    if (!imageBytes) {
      throw new Error("registerImage: image bytes are required");
    }
    images.set(String(imageId), normalizeBytes(imageBytes));
    return String(imageId);
  }

  function createWorld({ imageId = null, imageBytes = null } = {}) {
    if (imageBytes) {
      imageId = registerImage(imageBytes);
    }
    if (imageId && !images.has(String(imageId))) {
      throw new Error(`createWorld: unknown imageId ${imageId}`);
    }
    const id = nextWorldId++;
    worlds.set(id, { id, imageId: imageId ? String(imageId) : null, runners: new Set() });
    return id;
  }

  function cloneWorld(imageId, options = {}) {
    if (!images.has(String(imageId))) {
      throw new Error(`cloneWorld: unknown imageId ${imageId}`);
    }
    return createWorld({ ...options, imageId });
  }

  async function createRunner(worldId, options = {}) {
    const world = worlds.get(worldId);
    if (!world) {
      throw new Error(`createRunner: unknown worldId ${worldId}`);
    }

    const runtime = createSharedCclRuntime({
      memoryInitialPages: options.memoryInitialPages ?? memoryInitialPages,
      memoryMaximumPages: options.memoryMaximumPages ?? memoryMaximumPages,
      subprimsTableInitial: options.subprimsTableInitial ?? subprimsTableInitial,
      subprimsTableMaximum: options.subprimsTableMaximum ?? subprimsTableMaximum,
    });

    let kernel = null;

    const microkernel = createMicrokernel({
      memory: runtime.memory,
      asyncStdin: options.asyncStdin ?? asyncStdin,
      namedBytes: options.namedBytes ?? namedBytes,
      writeStdout: options.writeStdout ?? writeStdout,
      writeStderr: options.writeStderr ?? writeStderr,
      logSink: options.logSink ?? logSink,
      now: options.now ?? now,
      compiledModulesInstaller: ({ registry, nil }) => {
        if (!kernel) return 0;
        const { installed } = installCompiledModulesFromRegistrySync({
          kernel,
          memory: runtime.memory,
          subprimsTable: runtime.subprimsTable,
          microkernel,
          registry,
          nil,
          verbose: options.verboseInstallCompiledModules ?? false,
        });
        return installed;
      },
    });

    kernel = await instantiateWasm(
      kernelBytes,
      createCclImports({
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
      }),
    );

    const providers = [{ exports: kernel.instance.exports }];
    let subprimsReady = false;
    if (subprimsBytes) {
      const subprims = await instantiateWasm(
        subprimsBytes,
        createCclImports({
          memory: runtime.memory,
          subprimsTable: runtime.subprimsTable,
          microkernel,
          extra: { ccl: kernel.instance.exports },
        }),
      );
      providers.push({ exports: subprims.instance.exports });
      subprimsReady = hasRequiredSubprims(subprims.instance.exports);
    }

    if (subprimsMap) {
      installSubprimsTable({
        table: runtime.subprimsTable,
        subprimsMap,
        providers,
      });
    }
    setSubprimsReady(kernel, subprimsReady);

    const runnerId = nextRunnerId++;
    const runner = {
      id: runnerId,
      worldId,
      runtime,
      microkernel,
      kernel,
      status: "ready",
      cstackSize: options.cstackSize ?? cstackSize,
      reserveBytes: options.reserveBytes ?? reserveBytes,
    };

    runner.loadImage = (imageIdOrBytes) => {
      const cached = images.get(String(imageIdOrBytes));
      if (!cached && typeof imageIdOrBytes === "string") {
        throw new Error(`loadImage: unknown imageId ${imageIdOrBytes}`);
      }
      const imageBytes = cached ?? normalizeBytes(imageIdOrBytes);
      const imageLen = imageBytes.byteLength >>> 0;
      const pageSize = 65536;
      const needBytes = imageLen + runner.cstackSize + runner.reserveBytes;
      let haveBytes = runtime.memory.buffer.byteLength;
      if (needBytes > haveBytes) {
        const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
        runtime.memory.grow(growPages);
        haveBytes = runtime.memory.buffer.byteLength;
      }

      if (typeof kernel.instance.exports.wasm_set_cstack_bounds !== "function") {
        throw new Error("loadImage: kernel missing export wasm_set_cstack_bounds");
      }
      const cstackBase = runtime.memory.buffer.byteLength;
      kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, runner.cstackSize);

      const blobBase = (cstackBase - runner.cstackSize - imageLen) & ~15;
      if (blobBase < 0) {
        throw new Error("loadImage: not enough memory to place boot image below cstack");
      }
      new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

      if (typeof kernel.instance.exports.wasm_ccl_load_image !== "function") {
        throw new Error("loadImage: kernel missing export wasm_ccl_load_image");
      }
      return kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);
    };

    runner.installCompiledModules = (opts = {}) =>
      installCompiledModulesFromRegistry({
        kernel: kernel.instance,
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
        ...opts,
      });

    runner.start = () => {
      if (typeof kernel.instance.exports.wasm_ccl_start !== "function") {
        throw new Error("runner.start: kernel missing export wasm_ccl_start");
      }
      return kernel.instance.exports.wasm_ccl_start();
    };

    runner.step = (deadlineMs = 0) => {
      if (typeof kernel.instance.exports.wasm_ccl_step !== "function") {
        throw new Error("runner.step: kernel missing export wasm_ccl_step");
      }
      return kernel.instance.exports.wasm_ccl_step(deadlineMs);
    };

    runners.set(runnerId, runner);
    world.runners.add(runnerId);

    if (world.imageId && options.autoloadImage !== false) {
      runner.loadImage(world.imageId);
      if (options.autoInstallCompiledModules !== false) {
        await runner.installCompiledModules({
          verbose: options.verboseInstallCompiledModules ?? false,
        });
      }
    }

    return runnerId;
  }

  function terminateRunner(runnerId, reason = "terminated") {
    const runner = runners.get(runnerId);
    if (!runner) return false;
    runner.status = reason;
    runner.microkernel?.closeStdin?.();
    runners.delete(runnerId);
    const world = worlds.get(runner.worldId);
    world?.runners?.delete(runnerId);
    return true;
  }

  function terminateWorld(worldId, reason = "terminated") {
    const world = worlds.get(worldId);
    if (!world) return false;
    for (const rid of Array.from(world.runners)) {
      terminateRunner(rid, reason);
    }
    worlds.delete(worldId);
    return true;
  }

  function getWorld(worldId) {
    return worlds.get(worldId) ?? null;
  }

  function getRunner(runnerId) {
    return runners.get(runnerId) ?? null;
  }

  function sendToRunner(runnerId, message) {
    const runner = runners.get(runnerId);
    if (!runner) {
      throw new Error(`sendToRunner: unknown runnerId ${runnerId}`);
    }
    if (message == null) return;
    if (message instanceof Uint8Array || message instanceof ArrayBuffer || ArrayBuffer.isView(message)) {
      runner.microkernel.feedStdin(normalizeBytes(message));
      return;
    }
    switch (message.type) {
    case "stdin":
      runner.microkernel.feedStdin(normalizeBytes(message.bytes));
      return;
    case "close-stdin":
      runner.microkernel.closeStdin();
      return;
    default:
      throw new Error(`sendToRunner: unknown message type ${message.type}`);
    }
  }

  return {
    registerImage,
    createWorld,
    cloneWorld,
    createRunner,
    getWorld,
    getRunner,
    terminateRunner,
    terminateWorld,
    sendToRunner,
    _debug: { images, worlds, runners },
  };
}
