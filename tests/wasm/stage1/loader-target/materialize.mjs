// Materialize compiler records directly, without XFASLOAD or a target heap.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {encodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {PACKAGING} from '../../../../runtime/wasm32/bundle.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

export function materialize({records, fasl, out, versions, policy, inventory}) {
  fs.mkdirSync(out, {recursive: true});
  const modules = [], units = [];
  for (const unit of records.units) {
    const names = new Map(), all = [];
    const reserve = record => {
      if (names.has(record[1])) throw Error('Duplicate code name: ' + record[1]);
      names.set(record[1], modules.length + all.length + 1); all.push(record);
      for (const child of record[8] ?? []) reserve(child);
    };
    reserve(unit.record);
    const ids = [];
    for (const record of all) {
      const [version, wire, arity, captures, wat, symbols, codes, keywords] = record;
      if (![4, 5].includes(version) || keywords !== null) throw Error('Unsupported code record');
      const id = names.get(wire), name = 'code_' + id; ids.push(id);
      const compiled = inventory(wat, path.join(out, name), policy, versions);
      modules.push({name, code_id: id, version: 4, signature: 17, role: 23,
        symbol_mode: version === 5 ? 'root-cells' : 'values',
        arity: [arity[1], arity[2], !!arity[3], !!arity[4], !!arity[5], arity[6]], captures,
        ...compiled, symbols: (symbols ?? []).map(([wire, index]) => ({wire, index})),
        codes: (codes ?? []).map(name => {
          if (!names.has(name)) throw Error('Unknown nested code: ' + name);
          return {name, code_id: names.get(name)};
        })});
    }
    const descriptor = unit.install_record ?? unit.record;
    units.push({name: unit.name, symbol_count: unit.symbol_count,
      record_version: descriptor[0], record_sha256: sha256(JSON.stringify(descriptor)),
      root: names.get(unit.name), modules: ids});
  }
  const codeSet = {version: 1, packaging: PACKAGING, ...versions, modules};
  return encodeTargetBundle({codeSet, units, fasl,
    readBytes: name => fs.readFileSync(path.join(out, name + '.wasm')),
    readTemplate: name => fs.readFileSync(path.join(out, name + '.template.wasm'))});
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const [records, fasl, out, versions, policy, producer] = process.argv.slice(2);
  const {inventory} = await import(pathToFileURL(producer));
  const read = name => JSON.parse(fs.readFileSync(name));
  fs.writeFileSync(out + '.w32bundle', materialize({records: read(records), fasl: fs.readFileSync(fasl),
    out, versions: read(versions), policy: read(policy), inventory}));
}
