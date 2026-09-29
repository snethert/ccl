export const declaration=sha256=>({version:1,name:'example',sha256,policy:'per-worker',
 memory:{export:'memory',minimum:1,maximum:4},tables:[{export:"callbacks",minimum:1,maximum:128}],
 callbacks:[{name:"integer",table:"callbacks",params:["i32"],results:["i32"],error:[-1]},
 {name:"scalars",table:"callbacks",params:["i32","i64","f32","f64"],results:["i32","i64","f32","f64"],error:[-1,-2n,-3,-4]},
 {name:"void",table:"callbacks",params:[],results:[],error:[]}],initialization:{kind:'export',name:'initialize'},
 buffers:{allocate:'allocate',release:'release',maximumBytes:65536},
 imports:[{module:'host',name:'collect',params:[],results:[]},{module:'host',name:'observe',params:['i32'],results:[]}],
 exports:[['cb-call',['i32','i32'],['i32']],['cb-twice',['i32','i32'],['i32']],['cb-trap',['i32','i32'],['i32']],
 ['cb-after',[],['i32']],['cb-saved',['i32'],['i32']],['cb-scalars',['i32','i32','i64','f32','f64'],['i32','i64','f32','f64']],['cb-void',['i32'],[]],['initialize',[],[]],['echo',['i32','i64','f32','f64'],['i32','i64','f32','f64']],['mode',['i32'],[]],
 ['allocate',['i32'],['i32']],['release',['i32'],[]],['releases',[],['i32']],['run',['i32','i32','i32'],['i32']]]
 .map(([name,params,results])=>({name,params,results,...(name==='run'?{ranges:[{pointer:0,length:1,access:'readwrite',encoding:'utf-8'}]}:{}) ,...(['cb-call','cb-twice','cb-trap','cb-scalars','cb-void'].includes(name)?{callbacks:[{parameter:0,type:name==='cb-scalars'?'scalars':name==='cb-void'?'void':'integer'}]}:{})}))});
