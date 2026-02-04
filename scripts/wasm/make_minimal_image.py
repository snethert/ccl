#!/usr/bin/env python3
"""Generate a minimal OpenMCL image for WASM bring-up.

This creates a small image with:
- nilreg/static area (symbols + globals)
- tiny dynamic area with a stub function object

The function entrypoint is a fixnum table index (WASM ABI).
Keep the entrypoint index in sync with the kernel boot stub.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


PAGE_SIZE = 4096
NUM_SECTIONS = 5

# ARM/WASM32 layout constants (keep in sync with lisp-kernel/arm-constants.h)
FULLTAG_NIL = 1
FULLTAG_MISC = 6
FULLTAG_NODEHEADER = 2
FULLTAG_IMM = 3
NTAGBITS = 3
NUM_SUBTAG_BITS = 8
FIXNUM_SHIFT = 2
DNODE_SIZE = 8

SUBTAG_SYMBOL = FULLTAG_NODEHEADER | (7 << NTAGBITS)
SUBTAG_FUNCTION = FULLTAG_NODEHEADER | (5 << NTAGBITS)

SYMBOL_ELEMENT_COUNT = 7
FUNCTION_ELEMENT_COUNT = 2

SYMBOL_HEADER = (SYMBOL_ELEMENT_COUNT << NUM_SUBTAG_BITS) | SUBTAG_SYMBOL
FUNCTION_HEADER = (FUNCTION_ELEMENT_COUNT << NUM_SUBTAG_BITS) | SUBTAG_FUNCTION

# nil_value / static base (arm-constants.h)
NIL_BASE = 0x04000000
NIL_VALUE = NIL_BASE + FULLTAG_NIL
STATIC_BASE = 0x03FFF000

# nrs layout (arm-constants.s)
NRS_ORIGIN = DNODE_SIZE - FULLTAG_NIL
NRS_SYMBOL_COUNT = 33
SYMBOL_SIZE = 32

# area.h (WASM32 follows the ARM lowmem layout)
PURESPACE_RESERVE = 64 << 20

# openmcl image constants
SIG0 = (ord("O") << 24) | (ord("p") << 16) | (ord("e") << 8) | ord("n")
SIG1 = (ord("M") << 24) | (ord("C") << 16) | (ord("L") << 8) | ord("I")
SIG2 = (ord("m") << 24) | (ord("a") << 16) | (ord("g") << 8) | ord("e")
SIG3 = (ord("F") << 24) | (ord("i") << 16) | (ord("l") << 8) | ord("e")

ABI_VERSION = 1045
PLATFORM = 39  # PLATFORM_OS_WASM | PLATFORM_CPU_WASM | PLATFORM_WORD_SIZE_32
ACTUAL_IMAGE_BASE = 0x10000000  # keep above nilreg/static addresses

# area codes (area.h, fixnumshift = 2)
AREA_READONLY = 4 << 2
AREA_STATIC_CONS = 6 << 2
AREA_MANAGED_STATIC = 7 << 2
AREA_STATIC = 8 << 2
AREA_DYNAMIC = 9 << 2


TOPLCATCH_INDEX = 15
TOPLFUNC_INDEX = 16


def align(value: int, align_to: int) -> int:
    return (value + align_to - 1) & ~(align_to - 1)


def write_u32(buf: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", buf, offset, value & 0xFFFFFFFF)


def symbol_ptr(index: int) -> int:
    addr = NIL_BASE + (NRS_ORIGIN + index * SYMBOL_SIZE)
    return addr + FULLTAG_MISC


def build_static_area(function_ptr: int) -> bytearray:
    static_size = 2 * PAGE_SIZE
    buf = bytearray(static_size)

    unbound = FULLTAG_IMM | (6 << NTAGBITS)

    symbol_base = (NIL_VALUE + NRS_ORIGIN) - STATIC_BASE
    for i in range(NRS_SYMBOL_COUNT):
        off = symbol_base + (i * SYMBOL_SIZE)
        write_u32(buf, off + 0, SYMBOL_HEADER)

        vcell = unbound
        if i == 0:  # T
            vcell = symbol_ptr(i)
        elif i == 1:  # NIL
            vcell = NIL_VALUE
        elif i == TOPLCATCH_INDEX:
            vcell = symbol_ptr(i)
        elif i == TOPLFUNC_INDEX:
            vcell = function_ptr

        # pname, vcell, fcell, package-predicate, flags, plist, binding-index
        write_u32(buf, off + 4, NIL_VALUE)
        write_u32(buf, off + 8, vcell)
        write_u32(buf, off + 12, unbound)
        write_u32(buf, off + 16, NIL_VALUE)
        write_u32(buf, off + 20, 0)
        write_u32(buf, off + 24, NIL_VALUE)
        write_u32(buf, off + 28, 0)

    return buf


def build_dynamic_area(entry_fixnum: int) -> bytearray:
    dynamic_size = PAGE_SIZE * 16  # 64 KiB
    buf = bytearray(dynamic_size)

    # Function object at offset 0.
    write_u32(buf, 0, FUNCTION_HEADER)
    write_u32(buf, 4, entry_fixnum)
    write_u32(buf, 8, entry_fixnum)
    write_u32(buf, 12, 0)  # padding

    return buf


def build_image(entry_index: int, output_path: Path) -> None:
    entry_fixnum = entry_index << FIXNUM_SHIFT
    function_ptr = ACTUAL_IMAGE_BASE + PURESPACE_RESERVE + FULLTAG_MISC

    static_bytes = build_static_area(function_ptr)
    dynamic_bytes = build_dynamic_area(entry_fixnum)

    sections = [
        (AREA_STATIC, static_bytes, 0),
        (AREA_READONLY, b"", 0),
        (AREA_DYNAMIC, dynamic_bytes, 0),
        (AREA_MANAGED_STATIC, b"", 0),
        (AREA_STATIC_CONS, b"", 0),
    ]

    header = struct.pack(
        "<16I",
        SIG0,
        SIG1,
        SIG2,
        SIG3,
        0,  # timestamp
        0,  # canonical image base
        ACTUAL_IMAGE_BASE,
        NUM_SECTIONS,
        ABI_VERSION,
        0,
        0,
        PLATFORM,
        0,
        0,
        0,
        0,
    )

    section_headers = bytearray()
    for code, data, static_dnodes in sections:
        section_headers += struct.pack(
            "<4I",
            code,
            0,  # area pointer (unused)
            len(data),
            static_dnodes,
        )

    out = bytearray()
    header_pos = 0
    out += header
    out += section_headers
    out += b"\x00" * (align(len(out), PAGE_SIZE) - len(out))

    for code, data, _static_dnodes in sections:
        out += b"\x00" * (align(len(out), PAGE_SIZE) - len(out))
        out += data

    trailer_size = 16
    eof_pos = len(out) + trailer_size
    delta = header_pos - eof_pos

    trailer = struct.pack("<IIIi", SIG0, SIG1, SIG2, delta)
    out += trailer

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="doc/wasm/minimal.image")
    parser.add_argument("--entrypoint-index", type=int, default=200)
    args = parser.parse_args()

    output_path = Path(args.output)
    build_image(args.entrypoint_index, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
