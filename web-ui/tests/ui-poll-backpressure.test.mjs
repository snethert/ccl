import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createMicrokernel,
  ERRNO,
  KERNEL_OP_UI_POLL,
  KERNEL_STATUS_DONE,
  KERNEL_STATUS_PENDING
} from "../../scripts/wasm/lib/microkernel.mjs";

function writePollRequest(memory, { maxEvents = 0, maxBytes = 0, flags = 0 }, ptr = 0) {
  const dv = new DataView(memory.buffer, ptr, 12);
  dv.setUint32(0, maxEvents >>> 0, true);
  dv.setUint32(4, maxBytes >>> 0, true);
  dv.setUint32(8, flags >>> 0, true);
  return ptr;
}

test("UI_POLL returns E2BIG when first selected payload exceeds maxBytes", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const payload = new Uint8Array(128);
  payload.fill(7);

  const uiService = {
    pollEvents: () => ({ payload, count: 1 })
  };

  const kernel = createMicrokernel({ memory, uiService });
  const ptr = writePollRequest(memory, { maxEvents: 1, maxBytes: 16, flags: 0 });
  const reqId = kernel.imports.kernel_request(KERNEL_OP_UI_POLL, ptr, 12);

  assert.equal(kernel.imports.kernel_poll(reqId), KERNEL_STATUS_DONE);
  assert.equal(kernel.imports.kernel_result(reqId), -ERRNO.E2BIG);
  assert.equal(kernel.imports.kernel_response_size(reqId), 0);
  kernel.imports.kernel_drop_request(reqId);
});

test("UI_POLL pending and non-pending empty-queue semantics are deterministic", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const allowPendingCalls = [];

  const uiService = {
    supportsPending: true,
    pollEvents: ({ allowPending }) => {
      allowPendingCalls.push(Boolean(allowPending));
      if (allowPending) {
        return { pending: true };
      }
      return { payload: new Uint8Array(0), count: 0 };
    }
  };

  const kernel = createMicrokernel({ memory, uiService });

  const pendingPtr = writePollRequest(memory, { maxEvents: 32, maxBytes: 4096, flags: 0x1 }, 0);
  const pendingReq = kernel.imports.kernel_request(KERNEL_OP_UI_POLL, pendingPtr, 12);
  assert.equal(kernel.imports.kernel_poll(pendingReq), KERNEL_STATUS_PENDING);
  assert.equal(kernel._debug.pendingUiPolls.length, 1);

  const nonPendingPtr = writePollRequest(memory, { maxEvents: 32, maxBytes: 4096, flags: 0x0 }, 16);
  const nonPendingReq = kernel.imports.kernel_request(KERNEL_OP_UI_POLL, nonPendingPtr, 12);
  assert.equal(kernel.imports.kernel_poll(nonPendingReq), KERNEL_STATUS_DONE);
  assert.equal(kernel.imports.kernel_result(nonPendingReq), 0);
  assert.equal(kernel.imports.kernel_response_size(nonPendingReq), 0);

  assert.deepEqual(allowPendingCalls, [true, false]);

  kernel.imports.kernel_drop_request(pendingReq);
  assert.equal(kernel._debug.pendingUiPolls.length, 0);
  kernel.imports.kernel_drop_request(nonPendingReq);
});
