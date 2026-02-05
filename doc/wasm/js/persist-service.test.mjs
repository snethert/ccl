import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  createPersistenceService,
  createInMemoryPersistenceStore,
  createLmdbPersistenceStore,
  FILE_MODE_READ,
  FILE_MODE_WRITE,
  FILE_MODE_CREATE,
  FILE_MODE_TRUNCATE,
  FILE_MODE_APPEND,
} from "./persist-service.mjs";
import { ERRNO } from "./microkernel.mjs";

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8");

function toBytes(text) {
  return encoder.encode(String(text));
}

function toText(bytes) {
  return decoder.decode(bytes);
}

function mustOk(res, label) {
  assert.equal(res.ok, true, `${label} failed: errno=${res.errno}`);
  return res.value;
}

function mustErr(res, errno, label) {
  assert.equal(res.ok, false, `${label} expected error`);
  assert.equal(res.errno, errno, `${label} expected errno=${errno} got=${res.errno}`);
}

function concatBytes(chunks) {
  let total = 0;
  for (const c of chunks) total += c.length;
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.length;
  }
  return out;
}

function writeFile(service, filePath, bytes, flags = FILE_MODE_WRITE | FILE_MODE_CREATE | FILE_MODE_TRUNCATE) {
  const res = service.openFile(toBytes(filePath), flags);
  const handle = mustOk(res, `openFile(write) ${filePath}`);
  const data = bytes instanceof Uint8Array ? bytes : toBytes(bytes);
  const wrote = handle.write(data);
  assert.equal(wrote, data.length, `write returned ${wrote}`);
  const closed = handle.close();
  assert.equal(closed, 0, `close returned ${closed}`);
}

function readFile(service, filePath, step = 4096) {
  const res = service.openFile(toBytes(filePath), FILE_MODE_READ);
  const handle = mustOk(res, `openFile(read) ${filePath}`);
  const chunks = [];
  while (true) {
    const part = handle.read(step);
    assert.ok(!(typeof part === "number" && part < 0), `read returned error ${part}`);
    if (part.length === 0) break;
    chunks.push(part);
  }
  const closed = handle.close();
  assert.equal(closed, 0, `close returned ${closed}`);
  return concatBytes(chunks);
}

function readFileOnce(service, filePath, maxBytes = 4096) {
  const res = service.openFile(toBytes(filePath), FILE_MODE_READ);
  const handle = mustOk(res, `openFile(read) ${filePath}`);
  const part = handle.read(maxBytes);
  assert.ok(!(typeof part === "number" && part < 0), `read returned error ${part}`);
  const closed = handle.close();
  assert.equal(closed, 0, `close returned ${closed}`);
  return part;
}

test("ensureDirs/probe/truename/directory", () => {
  const service = createPersistenceService({ errno: ERRNO, now: () => 1111 });

  const ensure = service.ensureDirs(toBytes("/ql/tmp/fetch.dat"));
  assert.equal(ensure.ok, true);
  assert.equal(ensure.value, "/ql/tmp");

  const probeDir = service.probe(toBytes("/ql/tmp"));
  assert.equal(probeDir.ok, true);
  assert.equal(probeDir.value.kind, "dir");

  const probeMissing = service.probe(toBytes("/ql/tmp/fetch.dat"));
  mustErr(probeMissing, ERRNO.ENOENT, "probe missing file");

  const true1 = service.truename(toBytes("ql/tmp/../tmp/"));
  assert.equal(true1.ok, true);
  assert.equal(true1.value, "/ql/tmp");

  const dirList = service.directory(toBytes("/"));
  assert.equal(dirList.ok, true);
  const paths = dirList.value.map((e) => e.path).sort();
  assert.ok(paths.includes("/ql"));
  assert.ok(paths.includes("/ql/tmp"));
});

test("openFile read/write/append", () => {
  const service = createPersistenceService({ errno: ERRNO, now: () => 2000, chunkSize: 8 });

  writeFile(service, "/ql/tmp/file.lisp", "abc");
  assert.equal(toText(readFileOnce(service, "/ql/tmp/file.lisp")), "abc");

  writeFile(
    service,
    "/ql/tmp/file.lisp",
    "def",
    FILE_MODE_WRITE | FILE_MODE_APPEND | FILE_MODE_CREATE,
  );
  assert.equal(toText(readFileOnce(service, "/ql/tmp/file.lisp")), "abcdef");

  const missing = service.openFile(toBytes("/ql/tmp/missing"), FILE_MODE_READ);
  mustErr(missing, ERRNO.ENOENT, "open missing for read");
});

test("chunking and sequential reads", () => {
  const service = createPersistenceService({ errno: ERRNO, now: () => 3000, chunkSize: 4 });
  const payload = toBytes("ABCDEFGHIJ");
  writeFile(service, "/blob", payload);

  const store = service._debug.overlayStore;
  const meta = store.meta.get("/blob");
  assert.equal(meta.type, "file");
  assert.equal(meta.content.chunk_size, 4);
  assert.equal(meta.content.chunk_ids.length, 3);

  const roundTrip = readFile(service, "/blob", 3);
  assert.deepEqual(roundTrip, payload);
});

test("fileWriteDate updates on rewrite", () => {
  let nowValue = 1000;
  const store = createInMemoryPersistenceStore({ chunkSize: 4, now: () => nowValue });
  const service = createPersistenceService({ errno: ERRNO, overlay: store });

  writeFile(service, "/mtime.txt", "one");
  const first = service.fileWriteDate(toBytes("/mtime.txt"));
  assert.equal(first.ok, true);
  assert.equal(first.value, 1000);

  nowValue = 2000;
  writeFile(service, "/mtime.txt", "two", FILE_MODE_WRITE | FILE_MODE_TRUNCATE | FILE_MODE_CREATE);
  const second = service.fileWriteDate(toBytes("/mtime.txt"));
  assert.equal(second.ok, true);
  assert.equal(second.value, 2000);
});

test("rename/delete and directory errors", () => {
  const service = createPersistenceService({ errno: ERRNO, now: () => 4000, chunkSize: 8 });

  writeFile(service, "/a.txt", "A");
  writeFile(service, "/b.txt", "B");

  const ren = service.renameFile(toBytes("/a.txt"), toBytes("/b.txt"));
  assert.equal(ren.ok, true);
  assert.equal(toText(readFileOnce(service, "/b.txt")), "A");

  const probeA = service.probe(toBytes("/a.txt"));
  mustErr(probeA, ERRNO.ENOENT, "probe renamed src");

  const del = service.deleteFile(toBytes("/b.txt"));
  assert.equal(del.ok, true);
  const probeB = service.probe(toBytes("/b.txt"));
  mustErr(probeB, ERRNO.ENOENT, "probe deleted file");

  const ensureDir = service.ensureDirs(toBytes("/dir/"));
  assert.equal(ensureDir.ok, true);
  const delDirAsFile = service.deleteFile(toBytes("/dir"));
  mustErr(delDirAsFile, ERRNO.EISDIR, "deleteFile on dir");
});

test("deleteEmptyDirectory and deleteDirectoryTree", () => {
  const service = createPersistenceService({ errno: ERRNO, now: () => 5000, chunkSize: 8 });

  const mkEmpty = service.ensureDirs(toBytes("/empty/"));
  assert.equal(mkEmpty.ok, true);
  const delEmpty = service.deleteEmptyDirectory(toBytes("/empty"));
  assert.equal(delEmpty.ok, true);

  writeFile(service, "/tree/file.txt", "data");
  const delNonEmpty = service.deleteEmptyDirectory(toBytes("/tree"));
  mustErr(delNonEmpty, ERRNO.ENOTEMPTY, "delete non-empty dir");

  const delTreeNoValidate = service.deleteDirectoryTree(toBytes("/tree"), false);
  mustErr(delTreeNoValidate, ERRNO.EINVAL, "delete tree without validate");

  const delTree = service.deleteDirectoryTree(toBytes("/tree"), true);
  assert.equal(delTree.ok, true);
  const probeTree = service.probe(toBytes("/tree"));
  mustErr(probeTree, ERRNO.ENOENT, "probe deleted tree");
});

test("read-only mount enforcement", () => {
  const roStore = createInMemoryPersistenceStore({ chunkSize: 8, now: () => 6000 });
  const roService = createPersistenceService({ errno: ERRNO, overlay: roStore });
  writeFile(roService, "/ro/file.txt", "ro");
  roStore.readonly = true;

  const service = createPersistenceService({
    errno: ERRNO,
    readOnlyMounts: [{ prefix: "/ro", store: roStore }],
  });

  const readOnlyProbe = service.probe(toBytes("/ro/file.txt"));
  assert.equal(readOnlyProbe.ok, true);
  assert.equal(readOnlyProbe.value.readonly, true);

  const del = service.deleteFile(toBytes("/ro/file.txt"));
  mustErr(del, ERRNO.EACCES, "delete read-only file");

  const ren = service.renameFile(toBytes("/ro/file.txt"), toBytes("/ro/other.txt"));
  mustErr(ren, ERRNO.EACCES, "rename read-only file");

  const rmdir = service.deleteEmptyDirectory(toBytes("/ro"));
  mustErr(rmdir, ERRNO.EACCES, "rmdir read-only mount");
});

const LMDB_TEST_ENABLED = process.env.CCL_ENABLE_LMDB_TESTS === "1";

test("lmdb backend persists across reopen", { skip: !LMDB_TEST_ENABLED }, async () => {
  const lmdb = await import("lmdb");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ccl-lmdb-"));
  let store = null;
  try {
    store = createLmdbPersistenceStore({ lmdb, path: dir, chunkSize: 4 });
    const service = createPersistenceService({ errno: ERRNO, overlay: store });
    writeFile(service, "/persist.txt", "persisted");
    await store.persist?.close?.();

    store = createLmdbPersistenceStore({ lmdb, path: dir, chunkSize: 4 });
    const service2 = createPersistenceService({ errno: ERRNO, overlay: store });
    const data = readFileOnce(service2, "/persist.txt");
    assert.equal(toText(data), "persisted");
  } finally {
    await store?.persist?.close?.();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
