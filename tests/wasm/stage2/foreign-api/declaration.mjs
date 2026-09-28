export const declaration=sha256=>({version:1,name:'example',sha256,policy:'per-worker',
 memory:{export:'memory',minimum:1,maximum:4},tables:[],initialization:{kind:'export',name:'initialize'},
 buffers:{allocate:'allocate',release:'release',maximumBytes:65536},
 imports:[{module:'host',name:'collect',params:[],results:[]},{module:'host',name:'observe',params:['i32'],results:[]}],
 exports:[['initialize',[],[]],['echo',['i32','i64','f32','f64'],['i32','i64','f32','f64']],['mode',['i32'],[]],
 ['allocate',['i32'],['i32']],['release',['i32'],[]],['releases',[],['i32']],['run',['i32','i32','i32'],['i32']]]
 .map(([name,params,results])=>({name,params,results,...(name==='run'?{ranges:[{pointer:0,length:1,access:'readwrite',encoding:'utf-8'}]}:{})}))});
