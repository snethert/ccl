#!/usr/bin/env node
// Re-derive the boundary fixture's memory-ownership map from its retained
// link metadata using the retained planner: node ownership.mjs SOURCE_DIR LINKED_METADATA CONTRACT
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [sourceDir, metadataPath, contractPath] = process.argv.slice(2);
if (!sourceDir || !metadataPath || !contractPath) throw Error('usage: node ownership.mjs SOURCE_DIR LINKED_METADATA CONTRACT');
const { planMemory } = await import(pathToFileURL(path.join(sourceDir, 'runtime.mjs')).href);
const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
const contract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));
process.stdout.write(JSON.stringify(planMemory(metadata, contract)) + '\n');
