# Admission clauses

`check.mjs` names the directed cases, retained in `namespace.json`. Manifest
validation publishes no session or mutable state until the complete tree passes.

| Predicate | Observation |
| --- | --- |
| plain record; own required/data fields; no extras/accessors | non-record, missing-field, unknown-field, getter-not-invoked |
| version, entries array and capacity | version, entry-array, entry-limit |
| configurable bounds integral, positive, no larger than ceilings | limit-integer, limit-positive, limit-bound, limit-field; common predicate for each limit |
| path string, nonempty, NUL/backslash-free, scalar Unicode and byte length | eight path cases; both character and UTF-8 byte limits |
| canonical absolute manifest path, no empty/dot/parent components | four noncanonical cases |
| unique path, file/directory kind | duplicate, symlink |
| nonshared Uint8Array, bytes present | not-bytes, shared-bytes, hash-only |
| digest shape and equality | malformed-digest, wrong-digest |
| aggregate copied-byte budget | total-bytes |
| directory has no byte/digest payload | directory-bytes, directory-digest |
| root exists and is a directory; parents exist and are directories | no-root, absent-parent, file-parent. Root's directory-kind test also follows from cwd and its directory ancestors; retained as a direct structural diagnostic. |
| cwd/cclRoot canonical existing directories | cwd-not-directory, ccl-root-not-directory; canonical validator shared with paths |
| runtime path prefix is a directory; final item exists | file-traversal, file-trailing-slash, missing-name |
| numeric live handle and right kind | stale, unknown, fractional, each wrong-kind method and cross-session handle; Integer(fd) is redundant given Map membership in locally allocated integer IDs |
| correct open kind and read-only mode | open-directory, open-file-as-directory, write-open |
| active capacity and nonrecycled fixnum ID capacity | open-limit, lifetime-handle-exhaustion; failed open does not consume an ID |
| read offset/count are nonnegative safe integers; bounded count and sum | eight range cases; invalid READ preserves position |
| seek offset integral; origin enumerated; sum safe/nonnegative | seek-fractional, seek-origin, seek-before-start, seek-overflow; position preserved |

Positive state cases observe private byte snapshots, returned copies, identity
independence from manifest ordering, cwd binding, independent positions/sessions,
EOF and directory-end stability. Six complete-check mutants cover omitted digest,
borrowed owner bytes, exposed result view, recycled IDs, missing handle limits
and PREAD moving the cursor. Equivalent clauses are not claimed as isolated by a
mutant. Directory `size: 0` and sorted names are protocol choices, not native
inode metadata or native enumeration order.
