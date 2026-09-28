import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export function readRecords(file) {
  if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file));
  return JSON.parse(execFileSync('python3', ['-B',
    fileURLToPath(new URL('./record_reader.py', import.meta.url)), file],
    {encoding: 'utf8', maxBuffer: 1024 * 1024 * 1024}));
}
