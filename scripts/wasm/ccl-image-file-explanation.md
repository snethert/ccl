## What a CCL “image” file is

A Clozure CL “image” (`*.image`) is an archived snapshot of the Lisp heap: functions, symbols, packages, compiled code, global variables, and the rest of the in-memory Lisp world. You start CCL by launching the small “kernel” executable, and the kernel then locates and loads the heap image to reconstruct that Lisp world. ([Clozure CL][1])

If you use `CCL:SAVE-APPLICATION`, you’re writing out a modified heap image (optionally with the kernel prepended, producing a single executable file). ([Clozure CL][1])

Mentally: the kernel is the body, the image is the brain, and `save-application` is how you pickle the brain for later use.

---

## High-level file layout

From the kernel’s perspective (as implemented in `lisp-kernel/image.c` / `image.h`), a CCL image file is:

1. **Optional arbitrary prefix bytes** (could be an executable kernel, a shell script wrapper, or anything).
2. **Section data** for multiple heap “areas”, stored page-aligned.
3. **A header and section table** describing those areas.
4. **A trailer at the very end** that tells the kernel where the header lives.

The crucial trick: the **header can be anywhere**; the kernel finds it using the trailer at EOF. This is specifically to make “kernel prepended to image” work without needing a fancy container format. ([GitHub][2])

---

## The trailer: how the kernel finds the header

At the very end of the file is an `openmcl_image_file_trailer`:

* `sig0`, `sig1`, `sig2` (signature words)
* `delta` (a signed offset from end-of-file back to the start of the header) ([GitHub][2])

The loader does (simplified):

* Seek to EOF
* Read the trailer (and verify the signature)
* Use `delta` (expected to be negative) to seek backward to the header location ([GitHub][3])

So the file ends with “**here’s the magic stamp, and here’s how far back the real map starts**.”

---

## The header: what metadata is stored

The header struct is `openmcl_image_file_header`. Key fields:

* 4 signature words (`sig0..sig3`), which are defined as:

  * `IMAGE_SIG0` = `'Open'`
  * `IMAGE_SIG1` = `'MCLI'`
  * `IMAGE_SIG2` = `'mage'`
  * `IMAGE_SIG3` = `'File'` ([GitHub][2])
    (This is why older internal naming still says “OpenMCLImageFile”.)

* `timestamp` (time of save) ([GitHub][2])

* `nsections` (how many heap sections are in this image) ([GitHub][2])

* `abi_version` (checked against the kernel’s supported min/max) ([GitHub][3])

* `flags` (must match the kernel’s `PLATFORM` constant; otherwise “saved for another platform”) ([GitHub][3])

* **Image base addresses**:

  * `canonical_image_base_*`
  * `actual_image_base_*` ([GitHub][2])

Those base addresses exist because the heap contains **raw tagged pointers**. If the heap can’t be mapped at the exact addresses it was saved from, the kernel may need to **relocate** those pointers by applying a constant bias. The loader computes:

* `bias = image_base - ACTUAL_IMAGE_BASE(header)` ([GitHub][3])

Finally, on 64-bit there’s:

* `section_data_offset_high/low`: a signed offset from the end of the section headers to the first section’s data (used because CCL can write section data earlier and put the headers later). ([GitHub][2])

---

## Section headers: what each section describes

Immediately associated with the file header is an array of `openmcl_image_section_header` entries:

* `code` — which kind of memory area this is (dynamic, readonly, etc.)
* `memory_size` — bytes to map for this section
* `static_dnodes` — extra per-section info used at least for the dynamic heap (saved from `tenured_area->static_dnodes`) ([GitHub][2])

The actual on-disk section data is **page-aligned**, and the code repeatedly calls `seek_to_next_page(fd)` to ensure alignment when reading/writing. ([GitHub][3])

---

## The five heap sections CCL writes (NUM_IMAGE_SECTIONS = 5)

CCL currently writes **five** sections (`NUM_IMAGE_SECTIONS 5`). ([GitHub][2])

In `save_application_internal`, the sections are taken from these areas, in this order:

1. `nilreg_area`
2. `readonly_area`
3. `active_dynamic_area`
4. `managed_static_area`
5. `static_cons_area` ([GitHub][3])

Each is written as a raw memory dump of that area’s bytes (`writebuf(fd, a->low, n)`), aligned to pages. ([GitHub][3])

### 1) Static / “nilreg” area (AREA_STATIC): where NIL and critical globals live

When loading, the kernel treats the `AREA_STATIC` section specially:

* It records it as `nilreg_area`.
* It computes the address of `NIL` at a fixed offset inside that section (e.g. `a->low + (1024*4) + fulltag_nil` on x86-64) and calls `set_nil(image_nil)`. ([GitHub][3])

This area is where CCL keeps “things the kernel must find without asking Lisp politely,” including low-level globals and the **nilreg symbols** (like `%toplevel-function%`, `*package*`, etc.). Those symbols are addressed via macros like `nrs_symbol(...)` and `lisp_global(...)` in `lisp_globals.h`. ([GitHub][4])

If the heap image were a city, this area is city hall: boring, necessary, and full of paperwork that must not move.

### 2) Read-only / “pure” area (AREA_READONLY): stuff unlikely to become garbage

This section is mapped with RX protection (read/execute) in the loader. ([GitHub][3])

On the Lisp side, `SAVE-APPLICATION` can “purify” before saving: it moves objects expected to stick around into a special area that the GC doesn’t need to scan in the normal way. ([Clozure CL][1])

So, this section commonly contains “frozen” constants, code-related objects, and other long-lived data.

### 3) Dynamic heap area (AREA_DYNAMIC): the main GC-managed heap

This is the big one: most conses, arrays, instances, functions created at runtime, etc.

The internals documentation describes that the kernel reserves a large virtual address range and maps the initial heap image into it, then maps extra space beyond it based on thresholds. ([Clozure CL][5])

The image file stores the dynamic heap as raw heap bytes; after mapping, the kernel may make parts executable (`xMakeDataExecutable(...)`). ([GitHub][3])

### 4) Managed static area (AREA_MANAGED_STATIC): special GC-managed region + extra bitmaps

This area is loaded by mapping its bytes, and then (if non-empty) mapping additional pages immediately after it for a bitmap (“refbits”) and building a secondary index. ([GitHub][3])

When saving, CCL also writes extra refbits bytes for the managed static area right after the section data (page-aligned). ([GitHub][3])

You don’t need the full GC theory to get the point: **this section has extra sidecar metadata** because the collector wants fast answers to “does managed-static point into dynamic space?” without reading the entire novel every time.

### 5) Static cons area (AREA_STATIC_CONS): non-moving cons cells adjacent to the heap

The loader comment (and the user-level docs) explain the idea:

* Static conses are like cons cells except the GC never moves them.
* The memory for static conses is physically adjacent to (immediately precedes) the dynamic heap and is collected but not compacted. ([Clozure CL][6])

CCL keeps it as a separate image section “for now.” ([GitHub][3])

If normal cons cells are housecats (they wander and occasionally knock things over), static conses are statues: they don’t move, and that’s the entire selling point.

---

## What the bytes *inside* those sections look like (tagged Lisp objects)

A CCL image is not a portable serialization format. It is—very intentionally—**a memory image**, full of the same tagged words CCL uses at runtime.

From the internals docs:

* Objects are allocated on **double-node boundaries** (aligned so low bits are available for tagging).
* A tagged “node” uses low bits to encode type/tag info, and the remaining bits are either an immediate value or an aligned address.
* A uvector header word contains type info in the low byte and an element count in the rest of the word. ([Clozure CL][5])

That’s why mapping works: the kernel can map those pages back into memory and the pointers are immediately meaningful—*if* the address layout matches, or after relocation if it doesn’t.

---

## Relocation: what happens if the image can’t be mapped at the same base address

Because the image contains raw pointers, the kernel tries to map sections where they “should” go. If it can’t, it computes a constant `bias` and rewrites pointers in the mapped areas.

In `load_openmcl_image`, after mapping sections, the loader calls `relocate_area_contents(area, bias)` on several areas when `bias` is non-zero. ([GitHub][3])

The relocation pass works by scanning the area and using the runtime’s tagging rules to decide which words are headers, which are raw data, and which are pointers that should be adjusted. You can see it branching on things like `fulltag_of`, `immheader_tag_p`, `header_subtag`, and skipping over ivectors/functions appropriately. ([GitHub][3])

So the image isn’t “position-independent” in the ELF sense; it’s “position-adjustable because Lisp pointers are tagged and the kernel knows where they hide.”

---

## MACPTRs and other “you can’t bring that on the plane” objects

A saved image is loaded into a *new* OS process. Raw foreign pointers from the old process are not trustworthy in the new one.

CCL handles this explicitly:

* `SAVE-APPLICATION` converts `MACPTR` objects into `DEAD-MACPTR` objects when saving (with an exception for null pointer / address 0). ([Clozure CL][1])

This corresponds to `prepare_to_write_dynamic_space(...)` in the kernel code, which walks memory and rewrites certain macptrs before writing. ([GitHub][3])

Translation: CCL refuses to ship you a suitcase full of live grenades labeled “probably fine.”

---

## 32-bit vs 64-bit wrinkle: where the header is written

The format allows the header to be “anywhere,” but the saving code makes this concrete:

* On **32-bit**, it writes the file header + section headers early, then writes section data. ([GitHub][3])
* On **64-bit**, it can write the section data first, then later write the header + section headers near the end, filling in `section_data_offset_*` so the loader can find the earlier section data. ([GitHub][3])

Either way, the trailer at EOF points back to the header. ([GitHub][3])

---

## What a CCL image does *not* contain

Even though people colloquially say “snapshot of the running system,” this image format is fundamentally about restoring the Lisp heap and boot state, not freezing an OS process mid-instruction.

Notably:

* It does not reliably preserve foreign heap objects (handled via MACPTR→DEAD-MACPTR). ([Clozure CL][1])
* It is platform- and ABI-specific (explicitly checked by the loader). ([GitHub][3])
* It does not aim to serialize OS resources like file descriptors in a meaningful, portable way (those are properties of the process, not the Lisp heap).

---

## A compact “map legend” of what you’d see in a `.image`

If you conceptually “dissect” a `.image`, you should expect:

* **Trailer (EOF):** signature + negative delta → header. ([GitHub][2])
* **Header:** signature, timestamp, ABI/platform checks, image base addresses, section count, (64-bit) data offset. ([GitHub][2])
* **Section table:** for each section: area code + byte size (+ some per-area metadata). ([GitHub][2])
* **Section payloads (page-aligned):**

  1. static/nilreg area (contains NIL and kernel globals) ([GitHub][3])
  2. readonly/pure area (often produced by purify) ([GitHub][3])
  3. dynamic heap area (main GC’d heap) ([GitHub][3])
  4. managed static area + extra refbits pages ([GitHub][3])
  5. static cons area (non-moving conses adjacent to heap) ([GitHub][3])

Everything in those payloads is mostly just **raw tagged Lisp memory**, which works because CCL’s runtime representation is designed to be mmapped back into place. ([Clozure CL][5])

[1]: https://ccl.clozure.com/manual/chapter4.9.html "Clozure CL Documentation"
[2]: https://raw.githubusercontent.com/Clozure/ccl/master/lisp-kernel/image.h "raw.githubusercontent.com"
[3]: https://raw.githubusercontent.com/Clozure/ccl/master/lisp-kernel/image.c "raw.githubusercontent.com"
[4]: https://raw.githubusercontent.com/Clozure/ccl/master/lisp-kernel/lisp_globals.h "raw.githubusercontent.com"
[5]: https://ccl.clozure.com/docs/build/internals.html "
Clozure CL Internals"
[6]: https://ccl.clozure.com/docs/static/ccl.html "
Clozure Common Lisp"
