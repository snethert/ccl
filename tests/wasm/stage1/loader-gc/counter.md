# Proposed collection-count extension

For the single-Worker copying profile, reserve TCR byte offset 204 for an
unboxed collection count (0 through 536870911). It is collector-owner state,
never a root. Existing TCR v2 fields and the 256-byte extent remain unchanged;
the [proposed extension](counter-schema.json) narrows the reserved interval to
[208, 256). It pins the existing TCR v2 schema without editing that historical
contract; integration must bind this extension with the collector/compiler.

The owner validates the admitted count at collection/allocation boundaries.
Its copying service increments exactly once in each successful transaction's
commit, alongside the roots and allocation pointers. This also covers direct
service calls in standalone collector fixtures. An allocation assurance that copies twice
increments twice. Refused collections, fast allocation assurances, and memory
growth alone do not advance it. Exhaustion refuses before any copying or root
publication; the count never wraps and cannot alias an old hash-table stamp.

The target `%GET-GC-COUNT` boxes this count as a fixnum. All three shared hash
stores retain their native expressions, including the explicit previous-count
stamp used to request rehashing. The extension and owner remain proposals;
multi-Worker collection and saved-image count rebasing are not admitted.
