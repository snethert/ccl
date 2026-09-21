# Bootstrap execution inputs and portable I/O constants

Adds 31 executed original CCL definitions to the accepted 301. The backend is
unchanged. This is an auxiliary proposal, with no LL15 slot credit or ready-image
claim. The carry packet is accepted and integrated at f63a4a3b on Steve's
“Accept and integrate”; audit 150 is imported verbatim at ecf98002.

| Result | Retained run |
| --- | ---: |
| Original definitions executed | 332 (+31) |
| With a non-NIL witness | 318 (+28) |
| Native cases | 2,913 |
| Target comparisons | 11,652 |
| Equal to native / declared signed-zero differences | 11,648 / 4 |
| Collections between / during calls | 5,826 / 366 |
| Historical admitted / diagnostic denominator | 1,864 / 2,492 |

The input table exercises pooled list operations, buffer conversions and positions,
line-termination settings, string-stream read/peek/unread, lock/semaphore status,
lock pointer accessors, type records, periodic-task state and FASL value publication.
Native returns, mutated arguments and per-case special-variable post-state are
compared below and above 2 GiB, before and after moving collection. NIL-only and
non-NIL witness counts remain separate. Lock pointer fields use tagged sentinels;
no operating-system pointer is dereferenced. Native I/O structures have a portable
class-name list in their target descriptor; this does not implement class metadata.
Pools and input structures are pinned fixture objects with traced fields, not a
claim that every such header can move. Generated allocations and their live
references do move. The ordinary CCL definitions are neither rewritten nor renamed.

The source proposal gives SEEK_SET, SEEK_CUR, EINTR, EEXIST, ENFILE and EMFILE uses
explicit Wasm branches in seven CCL files. Target constants declare the portable
file-provider domain (0, 1, 4, 17, 23, 24); they are not values queried from the
browser, Node or macOS. A provider must translate its errors to this domain.
Actual file I/O, descriptor ownership and foreign calls remain owed.
`linux-files` leaves both the Wasm module list and its startup load sequence.
The other seventeen target module lists are unchanged.

The corrected target list has 56 files: 39 read completely, with 2,027 definitions
parsed and 1,582 admitted. Seventeen files still stop at real foreign references;
this remains a lower bound. The historical 2,492-definition diagnostic is retained
separately. No reader environment pretends that the remaining foreign calls exist.

## Native source qualification

The registered native build passes 21,843 tests. 150 of 164 FASLs are byte-identical;
the twelve source artifacts have identical decoded executable bytes and non-location
data. The two registration artifacts have the declared target-only additions.
Restoring original sources restores all 164 FASLs. Existing architecture state and
all seventeen existing target module lists are equal.

Reader equivalence is proved compositionally: inverse substitution restores every
surrounding source byte, and CCL's real reader reads each substituted form identically
under each of the seventeen existing target feature sets and TARGET package bindings
(136 file/profile joins). Full-file reading on all profiles would load unrelated
Windows foreign definitions absent from the macOS database; that attempted check
is retained as a development failure, not reported as a complete read.

The local nonexecuting FASL decoder adds U1 UTF-8 strings, counted characters and
raw float bit records needed by l1-streams. The source-note comparison additionally
records and ignores parent source-note links for level-1.lisp: its reader conditional
moves one load's note from the child to the enclosing MACROLET. File identities,
code and all other constants remain exact. All note spans are bounded and retained.

## Replay

From a checkout with the sibling evidence store:

```
python3 tests/wasm/stage1/bootstrap-inputs/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-inputs-r1 \
  --output /tmp/ccl-inputs-review
```

This rebuilds the compiler and modules, runs every native input and all target
comparisons, reruns the reader-substitution matrix, and requires every deterministic
execution file to equal the packet. Full native R6/R6a is bound by source hashes;
it is not needlessly rebuilt for an unchanged proposal. To rerun that build:

```
python3 tests/wasm/stage1/bootstrap-inputs/native.py \
  --evidence ../ccl-evidence --work /tmp/ccl-inputs-native-review-work \
  --output /tmp/ccl-inputs-native-review
```

Audit-150 F1 is repaired by the accepted integration's child execution adapter.
Its documented target command was rerun from a clean detached checkout of f63a4a3b:
885 files identical, 40 collector checks passing. This packet binds that result.
The collector is unchanged, so the new corpus reuses those checks by binary hash.

ASSQ remains target Lisp, handler-class and spread refusals remain executed, and
four native literal-zero subtraction differences remain declared. No new lowering,
C service, JS service, foreign-call implementation or timing claim is introduced.
