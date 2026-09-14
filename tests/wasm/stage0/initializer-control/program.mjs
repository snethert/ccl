// Three independent initializer chains, each in its own hand-built module.
export function program(module) {
  if(!Number.isInteger(module)||module<0||module>2)throw Error('module index');
  return `(module
    (import "host" "memory" (memory 1 1))
    (import "host" "failure" (tag $failure (param i32)))
    ${[0,1,2].map(j=>{
      const i=module*3+j;
      return `(func (export "init_${i}") (result i32)
        ${j?`(if (i32.ne (i32.load (i32.const ${64+4*(i-1)})) (i32.const 1)) (then unreachable))`:''}
        (i32.store (i32.const ${16+4*i}) (i32.const 1))
        (i32.store (i32.add (i32.const 128) (i32.mul (i32.load (i32.const 4)) (i32.const 4))) (i32.const ${i}))
        (i32.store (i32.const 4) (i32.add (i32.load (i32.const 4)) (i32.const 1)))
        (i32.store (i32.const ${192+4*i}) (i32.const ${(i+1)*10}))
        (if (i32.and (i32.load (i32.const 0)) (i32.const ${1<<i}))
          (then (throw $failure (i32.const ${i}))))
        (i32.store (i32.const ${64+4*i}) (i32.const 1))
        (i32.const ${100+i}))`;
    }).join('\n')})`;
}
