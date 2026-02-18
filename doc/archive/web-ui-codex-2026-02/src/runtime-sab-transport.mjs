import { decodeRuntimeMessage } from "../bridge/runtime.mjs";
import { SAB_RING_TRANSPORT } from "./runtime-transport.mjs";

function resolveReader(transport) {
  if (!transport || transport.transport !== SAB_RING_TRANSPORT) {
    throw new Error("runtime-sab-transport: expected command transport sab_ring_v1");
  }
  if (typeof transport.dequeueFrame === "function") return transport;
  if (transport.reader && typeof transport.reader.dequeueFrame === "function") return transport.reader;
  if (transport.ring && typeof transport.ring.dequeueFrame === "function") return transport.ring;
  throw new Error("runtime-sab-transport: transport requires dequeueFrame()");
}

function decodeUtf8(bytes) {
  return new TextDecoder().decode(bytes);
}

export function drainRuntimeSabMessages(transport, options = {}) {
  const reader = resolveReader(transport);
  const strictKinds = options.strictKinds !== false;
  const maxMessages = Number.isInteger(options.maxMessages) ? Math.max(1, options.maxMessages) : 64;
  const messages = [];
  const errors = [];

  for (let i = 0; i < maxMessages; i++) {
    const entry = reader.dequeueFrame();
    if (!entry?.ok || !(entry.frame instanceof Uint8Array)) break;
    const text = decodeUtf8(entry.frame);
    const decoded = decodeRuntimeMessage(text, { strictKinds });
    if (decoded.ok) {
      messages.push(decoded.message);
    } else {
      errors.push({ reason: decoded.error ?? "decode failed", text });
    }
  }

  return { transport: SAB_RING_TRANSPORT, messages, errors, count: messages.length };
}
