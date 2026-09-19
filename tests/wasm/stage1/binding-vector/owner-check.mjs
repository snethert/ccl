if(!c.owner||(!c.owner.baseDelta&&c.owner.vectorBase===undefined))assert(Array.from({length:get(108)},(_,i)=>load(get(104)+4*i)).every(x=>x===243),c.id+': grown vector restored');
if(c.vectorCheck){assert.equal(get(108),c.vectorCheck.cap,c.id+': independent capacity');assert.equal(get(48)-heap,c.vectorCheck.allocated,c.id+': independent allocation');}
