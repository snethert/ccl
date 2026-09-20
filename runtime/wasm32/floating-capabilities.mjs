import {numericCapabilities,admitNumericCapabilities} from './numeric-capabilities.mjs';
import {lispFloatService} from './service.mjs';
const associations=new WeakMap();
export function floatingCapabilities(options){
 const {integerBytes,integerDigest,...floating}=options;
 const numeric=numericCapabilities({...options,bytes:integerBytes,digest:integerDigest});
 const bundle=Object.freeze({ensure:numeric.ensure,integer:numeric.calculate,floating:lispFloatService(floating)});
 associations.set(bundle,numeric);return bundle;
}
export function admitFloatingCapabilities(bundle,env){
 const numeric=associations.get(bundle);if(!numeric)throw Error('FLOATING_CAPABILITY');
 admitNumericCapabilities(numeric,env);return bundle;
}
