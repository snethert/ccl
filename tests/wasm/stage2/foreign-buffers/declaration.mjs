export function declaration(digest,encoding='bytes',access='readwrite') {
 const ranges=[{pointer:0,length:1,access,encoding}];
 return {version:1,name:'buffer-fixture',sha256:digest,policy:'per-worker',
  memory:{export:'memory',minimum:1,maximum:4},tables:[],initialization:{kind:'none'},
  buffers:{allocate:'allocate',release:'release',maximumBytes:65536},
  imports:[{module:'host',name:'collect',params:[],results:[]},
           {module:'host',name:'observe',params:['i32','i32'],results:[]}],
  exports:[{name:'mode',params:['i32'],results:[]},{name:'releases',params:[],results:['i32']},
           ...['allocate','allocate-alias'].map(name=>({name,params:['i32'],results:['i32']})),
           ...['release','release-alias'].map(name=>({name,params:['i32'],results:[]})),
           ...['run','run-alias'].map(name=>({name,params:['i32','i32','i32'],results:['i32'],ranges}))]};
}
