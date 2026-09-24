import {createHash} from 'node:crypto';
import {manifest as primitiveManifest} from '../namespace-primitives/fixtures.mjs';

export function manifest() {
  const result=primitiveManifest();
  const text={
    '/ccl/unicode.txt':'Aλ😀\nsecond\r\nlast',
    '/ccl/boundary.txt':'x'.repeat(2047)+'λ😀\n'+'y'.repeat(8124)+'λ\n',
    '/ccl/crlf.txt':'one\r\ntwo\r\nlast'
  };
  for(const [path,value] of Object.entries(text)) {
    const bytes=new TextEncoder().encode(value);
    result.entries.push({path,kind:'file',bytes,sha256:createHash('sha256').update(bytes).digest('hex')});
  }
  return result;
}
