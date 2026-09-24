// Compose the namespace byte provider with the existing D5 proof machinery.
// This is a hand-built transport test, not the missing generated-Lisp bridge.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {build} from '../../stage0/integrated-runtime/build.mjs';
import {Harness} from '../../stage0/integrated-runtime/harness.mjs';
import {manifest} from './fixtures.mjs';
const out = process.argv[2];
const {createNamespace} = await import(pathToFileURL(path.join(out, 'runtime/namespace.mjs')));
const dir = path.join(out, 'transport'); fs.mkdirSync(dir);
const binary = build(dir), rows = [];
fs.writeFileSync(path.join(dir, 'versions.json'), JSON.stringify(binary.versions, null, 2) + '\n');
const h = new Harness(binary);
try {
  for (const [offset, count, interrupt] of [[0, 8, false], [6, 8, false], [8, 8, false], [100, 8, true]]) {
    await h.reset();
    const before = h.prepareValues(0, 6), E = h.schema.events;
    const session = createNamespace(manifest()).session(), fd = session.open('/ccl/a.bin');
    const job = h.actors[0].run('outer', [1, 6], [{code: E.WAITING, occurrence: 1}], 'program');
    const ticket = await h.request(); await h.actors[0].at(E.WAITING);
    assert.equal(h.state(0), h.schema.states.FOREIGN);
    await h.actors[1].run('collect_and_park');
    const bytes = session.pread(fd, offset, count);
    // The request is stable owner storage; it never retains a Lisp heap pointer.
    if (interrupt) h.interrupt(ticket);
    h.complete(ticket, {bytes, result: bytes.length});
    h.actors[0].resume();
    const done = await job;
    const restored = h.verifyResume(before, done);
    const q = h.schema.request;
    assert.equal(h.word(ticket.address + q.length), bytes.length);
    assert.equal(h.word(ticket.address + q.result), bytes.length);
    assert.equal(h.word(ticket.address + q.consumed), h.schema.outcome.COMPLETE);
    assert.deepEqual(Array.from(new Uint8Array(h.memory.buffer, ticket.address + q.payload, bytes.length)), [...bytes]);
    assert.throws(() => h.complete(ticket, {bytes}), /STALE_REQUEST_GENERATION/);
    const stale = ticket;
    const next = h.actors[0].run('outer', [1, 6], [{code: E.WAITING, occurrence: 1}], 'program');
    const current = await h.request(); await h.actors[0].at(E.WAITING);
    assert.equal(current.address, stale.address);
    assert.notEqual(current.generation, stale.generation);
    assert.throws(() => h.complete(stale, {bytes}), /STALE_REQUEST_GENERATION/);
    h.complete(current, {bytes: new Uint8Array(), result: 0}); h.actors[0].resume();
    await next;
    session.close(fd);
    rows.push({offset, count, bytes: [...bytes], interrupt, moved_roots: restored.new_root !== restored.old_root,
               thread_state_restored: true, stale_completion_refused: true});
  }
} finally { await h.close(); }
fs.writeFileSync(path.join(out, 'mailbox.json'), JSON.stringify({status: 'PASS', rows,
  driver: 'stage0/integrated-runtime', generated_lisp: false,
  request_arguments: 'owner-selected transport cases, not encoded Lisp path arguments',
  namespace_results_consumed: true}, null, 2) + '\n');
console.log(JSON.stringify({status: 'PASS', mailbox_cases: rows.length}));
