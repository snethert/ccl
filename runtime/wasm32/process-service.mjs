// Capabilities of a single Lisp Worker. All clock state belongs to this
// instance; no host addresses or clock origin are serialized into its image.
import {processConfiguration} from './config.mjs';

export class ProcessExit extends Error {
  constructor(status) { super('Lisp process exited: ' + status); this.status = status; }
}

export class UnhandledCondition extends Error {
  constructor(word) { super('Unhandled Lisp condition'); this.condition = word; }
}

export class ProcessReady extends Error {
  constructor() { super('Lisp startup completed'); }
}

export function processService({memory, configuration, startup, output, now = () => performance.now(), wait}) {
  const config = processConfiguration(configuration), origin = now();
  const need = (ok, why) => { if (!ok) throw Error('process service: ' + why); };
  need(Number.isFinite(origin) && typeof wait === 'function', 'CAPABILITIES');
  let strings;
  if (startup !== undefined) {
    need(startup && typeof startup.imageName === 'string' && startup.imageName.length > 0 &&
      typeof startup.cclRoot === 'string' && startup.cclRoot.startsWith('/') &&
      Array.isArray(startup.arguments), 'STARTUP');
    strings = [startup.imageName, startup.cclRoot, ...startup.arguments].map(value => {
      need(typeof value === 'string' && value.length <= 1048576 && !value.includes('\0'), 'STARTUP_STRING');
      return Array.from(value, ch => ch.codePointAt(0));
    });
  }
  const get = p => new DataView(memory.buffer).getUint32(p, true);
  const put = (p, v) => new DataView(memory.buffer).setUint32(p, v, true);
  const fixnum = p => { const word = get(p); need(word % 4 === 0, 'FIXNUM'); return (word | 0) >> 2; };
  let previous = 0;
  return args => {
    need(Number.isInteger(args) && args >= 0 && args + 12 <= memory.buffer.byteLength, 'ARGUMENTS');
    switch (fixnum(args)) {
      case 0: {
        const word = get(args + 4), p = word - 6;
        need(word % 8 === 6 && p >= 0 && p + 12 <= memory.buffer.byteLength && get(p) === 762, 'TIME_VECTOR');
        const elapsed = Math.floor((now() - origin) * 1000);
        need(Number.isSafeInteger(elapsed) && elapsed >= previous, 'MONOTONIC_CLOCK');
        const seconds = Math.floor(elapsed / 1000000);
        need(seconds <= 536870911, 'CLOCK_RANGE');
        previous = elapsed;
        put(p + 4, seconds * 4); put(p + 8, (elapsed % 1000000) * 4);
        return 77825;
      }
      case 1: {
        const seconds = fixnum(args + 4), micros = fixnum(args + 8);
        need(seconds >= 0 && micros >= 0 && micros <= 1000000, 'WAIT_RANGE');
        // Recheck the deadline: an embedding's wait may return early.
        const deadline = now() + seconds * 1000 + micros / 1000;
        for (let remaining; (remaining = deadline - now()) > 0;) wait(remaining);
        return 77825;
      }
      case 2: {
        const values = [config.ticks, config.pageSize, config.cpuCount, config.stackSize];
        const index = fixnum(args + 4); need(index >= 0 && index < values.length, 'CONFIG_KEY');
        return values[index] * 4;
      }
      case 3: throw new ProcessExit(fixnum(args + 4));
      case 4: throw new UnhandledCondition(get(args + 4));
      case 5: {
        need(strings, 'STARTUP_CAPABILITY');
        const index = fixnum(args + 4), word = get(args + 8);
        need(index >= 0 && index < strings.length, 'STARTUP_KEY');
        const value = strings[index];
        if (word === 77825) return value.length * 4;
        const p = word - 6;
        need(word % 8 === 6 && p >= 0 && p + 4 + value.length * 4 <= memory.buffer.byteLength &&
          get(p) === value.length * 256 + 191, 'STARTUP_BUFFER');
        value.forEach((ch, i) => put(p + 4 + i * 4, ch));
        return word;
      }
      case 6:
        need(strings, 'STARTUP_CAPABILITY');
        return (strings.length - 2) * 4;
      case 7: {
        need(typeof output === 'function', 'OUTPUT_CAPABILITY');
        const channel = fixnum(args + 4), word = get(args + 8), p = word - 6;
        need(channel === 1 || channel === 2, 'OUTPUT_CHANNEL');
        need(word % 8 === 6 && p >= 0 && p + 4 <= memory.buffer.byteLength &&
          (get(p) & 255) === 191, 'OUTPUT_STRING');
        const length = get(p) >>> 8;
        need(length <= 1048576 && p + 4 + length * 4 <= memory.buffer.byteLength, 'OUTPUT_STRING');
        let text = '';
        for (let i = 0; i < length; i++) {
          const ch = get(p + 4 + i * 4);
          need(ch <= 0x10ffff && (ch < 0xd800 || ch > 0xdfff), 'OUTPUT_SCALAR');
          text += String.fromCodePoint(ch);
        }
        // This capability is synchronous and unbuffered; force/finish-output
        // need no later host action. Validate the whole string before writing.
        need(output(channel, text) === undefined, 'OUTPUT_RESULT');
        return word;
      }
      case 8: throw new ProcessReady();
      default: throw Error('process service: OPERATION');
    }
  };
}
