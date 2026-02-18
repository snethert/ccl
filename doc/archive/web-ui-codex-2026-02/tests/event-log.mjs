function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertNoExtraKeys(obj, allowed, path) {
  for (const key of Object.keys(obj)) {
    if (!allowed.includes(key)) {
      throw new Error(`Unexpected key at ${path}: ${key}`);
    }
  }
}

function assertInteger(value, path, min = null) {
  assert(Number.isInteger(value), `Expected integer at ${path}`);
  if (min !== null) {
    assert(value >= min, `Expected integer >= ${min} at ${path}`);
  }
}

function assertString(value, path) {
  assert(typeof value === "string", `Expected string at ${path}`);
}

function assertObject(value, path) {
  assert(value && typeof value === "object" && !Array.isArray(value), `Expected object at ${path}`);
}

export function validateEvents(events) {
  assert(Array.isArray(events), "Expected array at events");

  let lastSeq = -1;
  for (let i = 0; i < events.length; i += 1) {
    const event = events[i];
    const path = `events[${i}]`;
    assertObject(event, path);
    assertNoExtraKeys(event, ["seq", "ts", "type", "target", "payload"], path);

    assertInteger(event.seq, `${path}.seq`, 0);
    assert(event.seq > lastSeq, `Expected monotonically increasing seq at ${path}.seq`);
    lastSeq = event.seq;

    if (event.ts !== undefined) {
      assertInteger(event.ts, `${path}.ts`, 0);
    }

    assertString(event.type, `${path}.type`);

    if (event.target !== undefined) {
      assertString(event.target, `${path}.target`);
    }

    assertObject(event.payload, `${path}.payload`);
  }

  return true;
}

export function validateEventLog(log) {
  assertObject(log, "log");
  assertNoExtraKeys(log, ["version", "events"], "log");
  assertString(log.version, "log.version");
  return validateEvents(log.events);
}
