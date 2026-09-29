// Node supplies the same resident byte fixture as the browser embedding.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createForeignFixture} from './fixture.mjs';
export function create(context) {
 return createForeignFixture(context,{bytes:new Uint8Array(fs.readFileSync(context.config.library)),assert});
}
