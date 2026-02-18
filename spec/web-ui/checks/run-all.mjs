#!/usr/bin/env node
/**
 * Run all web-ui conformance checks.
 *
 * Usage: node spec/web-ui/checks/run-all.mjs
 *
 * Exit code 0 = all pass, 1 = any failure, 2 = no checks found.
 */

import { readdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fork } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));

const files = (await readdir(__dirname))
  .filter(f => f.endsWith('.test.mjs'))
  .sort();

if (files.length === 0) {
  console.error('No conformance check files found.');
  process.exit(2);
}

let totalPass = 0;
let totalFail = 0;
let totalSkip = 0;

for (const file of files) {
  const path = join(__dirname, file);
  const contractName = file.replace('.test.mjs', '');
  console.log(`\n--- ${contractName} ---`);

  try {
    const mod = await import(path);
    if (typeof mod.run === 'function') {
      const result = await mod.run();
      totalPass += result.pass ?? 0;
      totalFail += result.fail ?? 0;
      totalSkip += result.skip ?? 0;
    } else {
      console.log('  (no run() export — skipped)');
      totalSkip += 1;
    }
  } catch (err) {
    console.error(`  ERROR: ${err.message}`);
    totalFail += 1;
  }
}

console.log(`\n=== Summary ===`);
console.log(`PASS: ${totalPass}  FAIL: ${totalFail}  SKIP: ${totalSkip}`);
process.exit(totalFail > 0 ? 1 : 0);
