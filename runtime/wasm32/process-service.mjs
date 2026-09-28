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

export function processService({memory, configuration, startup, output, now = () => performance.now(), wait,
  wallTime = () => Date.now(), calendar, cpuTime, collectionInhibition, objectValidity, foreign}) {
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
      case 14: {
        need(typeof objectValidity === 'function', 'OBJECT_CAPABILITY');
        need(get(args + 8) === 77825, 'OBJECT_ARGUMENTS');
        const valid = objectValidity(get(args + 4));
        need(typeof valid === 'boolean', 'OBJECT_RESULT');
        return valid ? 77838 : 77825;
      }
      case 12: case 13: {
        need(typeof collectionInhibition === 'function', 'COLLECTOR_CAPABILITY');
        need(get(args + 4) === 77825 && get(args + 8) === 77825, 'COLLECTOR_ARGUMENTS');
        const depth = collectionInhibition(fixnum(args) === 12 ? 1 : -1);
        need(Number.isInteger(depth) && depth >= -536870911 && depth <= 536870911, 'COLLECTOR_RESULT');
        return depth * 4;
      }
      case 9: case 10: case 11: {
        const op = fixnum(args), word = get(args + 4), p = word - 6, count = op === 11 ? 4 : 2;
        need(word % 8 === 6 && p >= 0 && p + 4 + 4 * count <= memory.buffer.byteLength &&
          get(p) === count * 256 + 250, 'CLOCK_VECTOR');
        let values;
        if (op === 9) {
          need(typeof wallTime === 'function', 'WALL_CLOCK_CAPABILITY');
          const seconds = Math.floor(wallTime() / 1000), days = Math.floor(seconds / 86400);
          need(Number.isSafeInteger(seconds), 'WALL_CLOCK');
          values = [days, seconds - days * 86400];
        } else if (op === 10) {
          need(typeof calendar === 'function', 'CALENDAR_CAPABILITY');
          const days = fixnum(p + 4), seconds = fixnum(p + 8);
          need(seconds >= 0 && seconds < 86400, 'CALENDAR_SECONDS');
          const value = calendar(days * 86400 + seconds);
          need(value && Number.isInteger(value.minutesWest) && Math.abs(value.minutesWest) <= 1440 &&
            typeof value.daylight === 'boolean', 'CALENDAR_RESULT');
          values = [value.minutesWest, Number(value.daylight)];
        } else {
          need(typeof cpuTime === 'function', 'CPU_CAPABILITY');
          const value = cpuTime();
          need(value && [value.user, value.system].every(n => Number.isSafeInteger(n) && n >= 0), 'CPU_RESULT');
          values = [value.user, value.system].flatMap(n => [Math.floor(n / 1000000), n % 1000000]);
        }
        need(values.every(n => Number.isInteger(n) && n >= -536870912 && n <= 536870911), 'CLOCK_RANGE');
        values.forEach((n, i) => put(p + 4 + 4 * i, n * 4));
        return 77825;
      }
      case 15:
        need(typeof foreign === 'function', 'FOREIGN_CAPABILITY');
        return foreign(args);
      default: throw Error('process service: OPERATION');
    }
  };
}
