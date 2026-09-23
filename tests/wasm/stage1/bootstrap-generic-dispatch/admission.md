# Admission and observations

The existing object-base, span, function header, side-vector and entry checks
remain in force. The inherited funcallable and keyword-metadata suites exercise
them. New function metadata checks isolate pool tag, header extent, header kind,
minimum prefix length, whole prefix extent and magic. The writer refuses an
ordinary function, a non-fixnum and a negative fixnum without changing its word.
The read-only metadata prefix is trusted compiler output: it is not a proof
that arbitrary owner-supplied argument bits describe executable code.

The population scanner admits only three fields, an available 16-byte object,
a zero GC link and type 0 or 1 (tagged 0 or 4). Each has moving and pinned
refusals, including the four-field termination shape. The moving extent test
is additionally implied by the common object-size boundary; it remains explicit.
Positive checks trace the shared child through both moved and pinned populations.
The collector never treats a refused population as an untraced opaque object.

All new function metadata exists only under the bootstrap entry. Ordinary
legacy arity/debug metadata still uses its own validated schema. A funcallable's
LFUN-KEYVECT now truthfully returns NIL, as native does, rather than exposing the
template's key vector or retaining the earlier fixture's checked refusal.

Arbitrary malformed class/CPL/method graphs are outside the trusted image
contract. Primitive span and shape failures remain checked boundaries; this
packet does not call the projected graph an untrusted image parser. The image
builder still owes real class-table/global installation on the cross-dumped heap.
