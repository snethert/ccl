# Read-only file host, version 1

The namespace accepts only file and directory entries. It has no symbolic links,
host-path fallback or mutable file contents. `runtime/wasm32/namespace.mjs`
enforces the entry-kind allowlist before constructing a session. Realpath is
lexical resolution within that admitted tree; it never consults a host filesystem.

Consequently the follow-links argument is evaluated and encoded in file-kind
requests, but cannot change an entry's kind. Wasm `%new-directory-p` uses realpath
then the directory-kind query under this no-links contract. Adding link entries
would require revisiting that implementation and its native lstat semantics.

Directory descriptors belong to the session. Open/read/close requests use the
same owned mailbox as file operations. End of enumeration returns NIL; it is not
a failed read. Mutation primitives report the named read-only-filesystem error;
they do not send a host filesystem operation.
