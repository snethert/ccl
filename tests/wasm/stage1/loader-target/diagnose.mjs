// Optional, reversible observation of a generated module. This is diagnostic
// evidence only: admit the original image first, then replace one entry pair.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

export function observeChecks({out, row, env, capabilities, start, regions, report, sourceFile, imports}) {
  const source = fs.readFileSync(sourceFile ?? out + '/boot/artifacts/' + row.name + '.wat', 'utf8');
  const marker = '(func $implicit_error_details ';
  assert.equal(source.split(marker).length, 2);
  const begin = source.indexOf(marker), body = source.indexOf('(if ', begin);
  assert(body > begin);
  let wat = source.slice(0, body) +
    '(call $observe_check (local.get $kind) (local.get $datum) (local.get $expected))' + source.slice(body);
  const rawChecks = [];
  wat = wat.replace(/\(throw \$call_error \(i32.const (\d+)\)\)/g, (throwCode, kind, offset) => {
    const functions = [...wat.slice(0, offset).matchAll(/\(func \$([^\s()]+)/g)];
    const name = functions.at(-1)?.[1];
    const index = rawChecks.length;
    rawChecks.push({index, kind: Number(kind), function: name});
    const operand = wat.slice(0, offset).match(/\(if \(i32.and (\(i32.load offset=\d+ \(local.get \$\w+\)\)) \(i32.const 3\)\) \(then $/)?.[1];
    const datum = ['object_base', 'resolve'].includes(name) ? '(local.get $node)' : operand ?? '(i32.const 77825)';
    const expected = name === 'object_base' ? '(local.get $header)' : '(i32.const 77825)';
    // Keep THROW as the enclosing instruction: wrapping it in a void block
    // changes validation in value-producing branches and shifts label depth.
    return `(throw $call_error (block (result i32) (call $observe_check (i32.const ${-1000 - index}) ${datum} ${expected}) (i32.const ${kind})))`;
  });
  wat = wat.replaceAll('(call $object_base (i32.load offset=40 (local.get $context))',
    '(call $object_base (block (result i32) (call $observe_check (i32.const -999998) (local.get $self) (local.get $context)) (i32.load offset=40 (local.get $context)))');
  wat = wat.replace('(drop (call $object_base (local.get $node) (i32.const 32) (i32.const 1578))) (local.get $node))',
    '(call $observe_check (i32.const -999997) (local.get $symbol) (local.get $node)) (drop (call $object_base (local.get $node) (i32.const 32) (i32.const 1578))) (local.get $node))');
  wat = wat.replace('(module ', '(module (import "observe" "check" (func $observe_check (param i32 i32 i32))) ')
    .replace('(memory 1 32769)', '(memory 1 32769 shared)');
  const path = out + '/observe-' + row.code_id;
  fs.writeFileSync(path + '.wat', wat);
  execFileSync('/usr/local/bin/wat2wasm', ['--enable-all', path + '.wat', '-o', path + '.wasm']);
  const bytes = fs.readFileSync(path + '.wasm');
  const reference = r => Object.hasOwn(r, 'heap') ? start + r.heap + r.tag :
    Object.hasOwn(r, 'immediate') ? r.immediate :
      regions.find(region => region.name === r.region).start + r.offset + r.tag;
  const instance = new WebAssembly.Instance(new WebAssembly.Module(bytes), {
    ...(imports ?? {env, ...capabilities,
    symbols: Object.fromEntries(row.symbols.map(s => [s.wire, reference(s.reference)])),
    codes: Object.fromEntries(row.codes.map(c => [c.name, c.code_id * 4]))}),
    observe: {check: report}
  });
  return {instance, evidence: {code: row.code_id, originalWat: sha256(source),
    observedWat: sha256(wat), observedBinary: sha256(bytes), rawChecks, diagnosticOnly: true}};
}
