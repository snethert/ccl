import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {link,unitsFromCodeSet} from '../loader/archive-link.mjs';
import {inventoryArchive} from '../loader/archive-inventory.mjs';
const [out]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(out+'/'+n));
const units=unitsFromCodeSet(read('boot/code-set.json')),stem=out+'/boot/artifacts/boot.archive';
fs.mkdirSync(out+'/boot/artifacts',{recursive:true});
const archive=await inventoryArchive(stem,read('policy.json'),read('versions.json'),{...link({units,outWat:stem+'.wat'}),boot:true});
const {write}=await import(pathToFileURL(out+'/write.mjs'));
console.log(write(out+'/boot',out+'/boot/artifacts',read('policy.json'),read('versions.json'),undefined,archive));

fs.writeFileSync(stem+'.json',JSON.stringify(archive));
