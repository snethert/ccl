// Optional P-0 observation. Separate append-only journals survive a killed
// Worker. Times use a common epoch; memory counters are bytes, never summed.
import fs from 'node:fs';

export function startupTiming(prefix, thread) {
  if (!prefix) return undefined;
  const fd = fs.openSync(prefix + '.' + thread + '.jsonl', 'wx');
  const stack = [], loads = [], buckets = new Map();
  let serial = 0, previous = performance.now();
  const now = () => performance.timeOrigin + performance.now();
  const write = row => fs.writeSync(fd, JSON.stringify({thread, epochMs: now(), ...row}) + '\n');
  const path = () => stack.findLast(frame => frame.path)?.path ?? loads.at(-1)?.path ?? '(startup)';
  function account() {
    const end = performance.now(), phase = stack.at(-1)?.phase ?? 'unmeasured';
    const key = JSON.stringify([path(), phase]);
    buckets.set(key, (buckets.get(key) ?? 0) + end - previous); previous = end;
  }
  function checkpoint() {
    account();
    write({kind: 'checkpoint', exclusive: [...buckets].map(([key, ms]) => {
      const [path, phase] = JSON.parse(key); return {path, phase, ms};
    })});
    buckets.clear();
  }
  const memory = (label, extra = {}) => {
    checkpoint();
    write({kind: 'memory', label, memory: process.memoryUsage(),
      peakRssBytes: process.resourceUsage().maxRSS * 1024, ...extra});
  };
  const event = (label, extra = {}) => write({kind: 'event', label, ...extra});
  function measure(phase, run, detail = {}) {
    account();
    const frame = {id: ++serial, phase, path: detail.path, childMs: 0};
    const parent = stack.at(-1)?.id ?? null, begin = now();
    stack.push(frame);
    let completed = false;
    try { const result = run(); completed = true; return result; }
    finally {
      account(); stack.pop();
      const ms = now() - begin;
      if (stack.length) stack.at(-1).childMs += ms;
      write({kind: 'span', id: frame.id, parent, phase, path: detail.path ?? path(),
        beginEpochMs: begin, ms, selfMs: ms - frame.childMs, completed});
    }
  }
  memory('thread-start', {pid: process.pid, versions: process.versions});
  return {measure, memory, event, checkpoint,
    open(path, fd) { account(); loads.push({path, fd}); event('file-open', {path, fd}); },
    close(path, fd) { account(); loads.splice(loads.findIndex(row => row.fd === fd), 1); event('file-close', {path, fd}); },
    finish() { checkpoint(); fs.closeSync(fd); }
  };
}
