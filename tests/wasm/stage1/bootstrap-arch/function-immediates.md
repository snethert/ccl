# O-5 proposal: funcallable-instance immediates

Pending the user's layout decision. This packet does not implement it.

The ordinary D1 function object occupies 32 bytes: header at 0, code ID at
4, captured-cell vector at 8, version at 12, arity at 16, debug at 20,
literal pool at 24, and padding at 28. Neither the environment nor the
literal pool is spare storage. The installer checks both against the module
manifest. Reusing either would break existing closures or entry validation.

Recommended: a distinct seven-field function-header shape for funcallable
instances, still occupying 32 bytes. Offset 28 would hold a tagged pointer
to a separate ordinary vector. Its elements would preserve CCL's logical
`nth-immediate` indices: code descriptor, class wrapper, slots vector,
dispatch table, discriminating code, hash, and bits. `gf.slots` is index 2
in `library/lispequ.lisp`. Ordinary six-field function objects remain as-is.

The alternative is an enlarged function object with dedicated fields. It
would change allocation size and require more object-layout migration.

The proposed vector requires one new traced field and validation in the
collector, owner image inventory, installer, materializer, snapshot reader,
and generated entry checks. Only admitted funcallable-instance shapes
would expose `nth-immediate`; native code vectors remain unavailable.
Construction must publish a fully initialized vector before its function
object becomes callable, and both reads and writes must validate shape and
bounds. Tests must move a generic function with only its slots vector's
contents reachable through it, while preserving ordinary captured closures,
metadata identity, redefinition and lazy dispatch. Slot storage alone does
not implement a generic-function discriminator or CLOS bootstrap.
