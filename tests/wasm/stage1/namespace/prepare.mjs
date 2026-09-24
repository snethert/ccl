import fs from 'node:fs';
import path from 'node:path';
import {files, trace} from './fixtures.mjs';
const out = process.argv[2];
for (const [name, values] of Object.entries(files)) {
  const dest = path.join(out, 'native-tree', name);
  fs.mkdirSync(path.dirname(dest), {recursive: true});
  fs.writeFileSync(dest, new Uint8Array(values));
}
fs.writeFileSync(path.join(out, 'requests.json'), JSON.stringify(trace, null, 2) + '\n');
