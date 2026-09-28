"""Share legacy recount checkpoints by all compiler and setup inputs."""
from pathlib import Path
import common as c
import storage


def prepare(out, source, command, env, here, pins, kernel, image):
    driver_roots=(here,here.parent/'bootstrap-recipes',here.parent/'registration')
    identity=dict(proposal=c.inventory(out/'proposal'),inputs=pins['inputs'],
                  kernel=c.sha(kernel),image=c.sha(image),
                  drivers={str(p.relative_to(c.ROOT)):c.sha(p)
                           for root in driver_roots for p in c.files(root)},
                  checkpoint_driver=c.sha(Path(__file__)))
    key=c.digest(identity)
    with storage.lock(c.DEFAULT_CACHE/'.build-locks'/key,exclusive=True):
        entry=c.cache_read(c.DEFAULT_CACHE,'compiler',key)
        rebuilt=entry is None
        if rebuilt:
            with c.cache_write(c.DEFAULT_CACHE,'compiler',key) as stage:
                c.command(command,stage/'setup.log',dict(env,RECOUNT_OUTPUT=str(stage)+'/'),source,timeout=120)
                if not (stage/'compiler.image').is_file():raise ValueError('missing compiler checkpoint')
                c.save(stage/'environment.json',identity)
            entry=c.cache_read(c.DEFAULT_CACHE,'compiler',key)
        c.clone(entry,out,dirs_exist_ok=True)
        (out/'cache-manifest.json').unlink()
        c.save(out/'compiler-reference.json',dict(key=key,rebuilt=rebuilt,
               image=str(entry/'compiler.image'),sha256=c.sha(entry/'compiler.image')))
