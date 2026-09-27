// Link records from all files into one runtime tier; preserve every FASL byte.
import fs from 'node:fs';
import {link,unitsFromRecords} from '../loader/archive-link.mjs';
import {inventoryArchive} from '../loader/archive-inventory.mjs';
import {encodeTargetContainer} from '../../../../runtime/wasm32/target-bundle.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const out=process.argv[2],read=n=>JSON.parse(fs.readFileSync(out+'/'+n));
const manifest=read('bundles.json'),units=[];
for(const file of manifest.files){
 const records=read(file.stem+'.records.json');
 if(records.units.some(u=>!Array.isArray(u.symbol_identities)))throw Error('Missing producer symbol identities: '+file.path);
 units.push(...unitsFromRecords(records,{},file.path));
}
const stem=out+'/runtime.archive';
const archive=await inventoryArchive(stem,read('policy.json'),read('versions.json'),link({units,outWat:stem+'.wat'}));
fs.writeFileSync(stem+'.json',JSON.stringify(archive));
manifest.archive={file:'runtime.archive.wasm',sha256:archive.binary_sha256,manifest:'runtime.archive.json',manifest_sha256:sha256(fs.readFileSync(stem+'.json'))};
for(const file of manifest.files){
 const bytes=encodeTargetContainer({units:archive.units.filter(u=>u.file===file.path).map(u=>u.name),
  archive_sha256:archive.binary_sha256,fasl:fs.readFileSync(out+'/'+file.stem+'.w32fsl')});
 file.bundle=file.stem+'.w32bundle';file.sha256=sha256(bytes);fs.writeFileSync(out+'/'+file.bundle,bytes);
}
fs.writeFileSync(out+'/bundle-manifest.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({functions:archive.function_count,units:archive.units.length,helpers:archive.helpers.length,
 roots:archive.root_cells,bytes:fs.statSync(stem+'.wasm').size}));
