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
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get(
    "CCL_WASM_BUILD_DIR",
    str(Path(__file__).resolve().parents[2] / "build" / "wasm32"),
))
from abi_constants import *  # noqa: F403,E402


PAGE_SIZE = 4096
NUM_SECTIONS = 5

# nrs layout (arm-constants.s)
NRS_ORIGIN = DNODE_SIZE - FULLTAG_NIL
NRS_SYMBOL_COUNT = 35
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
WASM_MODULES_INDEX = 33
WASM_CONST_POOLS_INDEX = 34

COMPILED_CONST_VALUE = 23
# Entry indices: WASM_CONST_ENTRY_INDEX from ABI contract, sequential after that.
# Index 203 (WASM_CONST_ENTRY_INDEX + 1) is reserved/unused.
_STUB_BASE = WASM_CONST_ENTRY_INDEX + 2
COMPILED_MODULES = [
    ("ccl_const_entry", WASM_CONST_ENTRY_INDEX, 1, "wasm_return_constant", COMPILED_CONST_VALUE << FIXNUM_SHIFT),
    ("ccl_fixnum_add_entry", _STUB_BASE + 0, 1, "wasm_return_fixnum_add", None),
    ("ccl_fixnum_sub_entry", _STUB_BASE + 1, 1, "wasm_return_fixnum_sub", None),
    ("ccl_fixnum_mul_entry", _STUB_BASE + 2, 1, "wasm_return_fixnum_mul", None),
    ("ccl_fixnum_ash_entry", _STUB_BASE + 3, 1, "wasm_return_fixnum_ash", None),
    ("ccl_fixnum_logand_entry", _STUB_BASE + 4, 1, "wasm_return_fixnum_logand", None),
    ("ccl_fixnum_logior_entry", _STUB_BASE + 5, 1, "wasm_return_fixnum_logior", None),
    ("ccl_fixnum_logxor_entry", _STUB_BASE + 6, 1, "wasm_return_fixnum_logxor", None),
    ("ccl_fixnum_lognot_entry", _STUB_BASE + 7, 1, "wasm_return_fixnum_lognot", None),
    ("ccl_fixnum_neg_entry", _STUB_BASE + 8, 1, "wasm_return_fixnum_neg", None),
    ("ccl_if_entry", _STUB_BASE + 9, 1, "wasm_if", (T_VALUE, NIL_VALUE)),
    ("ccl_if_arg_entry", _STUB_BASE + 10, 1, "wasm_if_arg", 17 << FIXNUM_SHIFT),
    ("ccl_identity_entry", _STUB_BASE + 11, 1, "wasm_identity", None),
    ("ccl_identity_y_entry", _STUB_BASE + 12, 1, "wasm_identity_y", None),
]


def align(value: int, align_to: int) -> int:
    return (value + align_to - 1) & ~(align_to - 1)


def write_u32(buf: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", buf, offset, value & 0xFFFFFFFF)


def push_u8(buf: bytearray, byte: int) -> None:
    buf.append(byte & 0xFF)


def push_uleb(buf: bytearray, value: int) -> None:
    v = value
    while True:
        byte = v & 0x7F
        v >>= 7
        if v:
            byte |= 0x80
        push_u8(buf, byte)
        if not v:
            break


def push_sleb32(buf: bytearray, value: int) -> None:
    v = value
    while True:
        byte = v & 0x7F
        sign_bit = byte & 0x40
        v >>= 7
        done = (v == 0 and sign_bit == 0) or (v == -1 and sign_bit != 0)
        if not done:
            byte |= 0x80
        push_u8(buf, byte)
        if done:
            break


def push_string(buf: bytearray, text: str) -> None:
    data = text.encode("ascii")
    push_uleb(buf, len(data))
    buf.extend(data)


def section(section_id: int, contents: bytearray) -> bytearray:
    out = bytearray()
    push_u8(out, section_id)
    push_uleb(out, len(contents))
    out.extend(contents)
    return out


def build_const_module_bytes(const_value: int, export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 3)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_uleb(types, 0)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_constant")
    push_u8(imports, 0x00)
    push_uleb(imports, 1)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 2)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 2)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x41)
    push_sleb32(body, const_value)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


def build_if_module_bytes(true_value: int, false_value: int, export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 3)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_uleb(types, 0)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 4)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_lisp_nil")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_constant")
    push_u8(imports, 0x00)
    push_uleb(imports, 1)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 2)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 4)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 3)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x46)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x41)
    push_sleb32(body, false_value)
    push_u8(body, 0x10)
    push_uleb(body, 2)
    push_u8(body, 0x05)
    push_u8(body, 0x41)
    push_sleb32(body, true_value)
    push_u8(body, 0x10)
    push_uleb(body, 2)
    push_u8(body, 0x0B)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


def build_if_arg_module_bytes(else_value: int, export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 3)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_uleb(types, 0)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 5)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_lisp_nil")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_constant")
    push_u8(imports, 0x00)
    push_uleb(imports, 1)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 2)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 5)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 4)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x46)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x41)
    push_sleb32(body, else_value)
    push_u8(body, 0x10)
    push_uleb(body, 2)
    push_u8(body, 0x05)
    push_u8(body, 0x10)
    push_uleb(body, 3)
    push_u8(body, 0x0B)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


def build_identity_module_bytes(export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 2)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 1)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 1)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 2)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


def build_identity_y_module_bytes(export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 2)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_return_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 1)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 1)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 2)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


def build_noncommutative_call_import_module_bytes(import_name: str, export_name: str) -> bytes:
    """Build module bytes for a non-commutative binary op.

    Funcall convention delivers args as arg_y=x (first/left), arg_z=y (second/right).
    The helper uses compiler convention: arg_z=x (left), arg_y=y (right).
    Emit a swap (get_arg_y, get_arg_z, set_arg_y, set_arg_z) before calling the helper.
    """
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    # type 0: () → i32   (pending_throw_p, get_arg_y, get_arg_z)
    # type 1: () → void  (the helper)
    # type 2: (i32) → void  (set_arg_y, set_arg_z)
    push_uleb(types, 3)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)
    push_u8(types, 0x60)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_uleb(types, 0)

    imports = bytearray()
    # func 0: wasm_pending_throw_p () → i32
    # func 1: the helper           () → void
    # func 2: wasm_get_arg_y       () → i32
    # func 3: wasm_get_arg_z       () → i32
    # func 4: wasm_set_arg_y  (i32) → void
    # func 5: wasm_set_arg_z  (i32) → void
    push_uleb(imports, 6)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, import_name)
    push_u8(imports, 0x00)
    push_uleb(imports, 1)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_arg_y")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_get_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, "wasm_set_arg_y")
    push_u8(imports, 0x00)
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_set_arg_z")
    push_u8(imports, 0x00)
    push_uleb(imports, 2)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 1)  # local func: type 1 () → void

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 6)  # local func after 6 func imports

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)           # 0 locals
    # check pending throw
    push_u8(body, 0x10)
    push_uleb(body, 0)           # call func 0: wasm_pending_throw_p
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)          # return
    push_u8(body, 0x0B)          # end if
    # swap: arg_y (funcall x) → arg_z, arg_z (funcall y) → arg_y
    push_u8(body, 0x10)
    push_uleb(body, 2)           # call func 2: wasm_get_arg_y → stack: [x]
    push_u8(body, 0x10)
    push_uleb(body, 3)           # call func 3: wasm_get_arg_z → stack: [x, y]
    push_u8(body, 0x10)
    push_uleb(body, 4)           # call func 4: wasm_set_arg_y → arg_y=y, stack: [x]
    push_u8(body, 0x10)
    push_uleb(body, 5)           # call func 5: wasm_set_arg_z → arg_z=x
    # call the helper
    push_u8(body, 0x10)
    push_uleb(body, 1)           # call func 1: the helper
    push_u8(body, 0x0B)          # end
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


# Non-commutative binary op helpers that need funcall→compiler convention swap.
_NONCOMMUTATIVE_IMPORTS = {"wasm_return_fixnum_sub", "wasm_return_fixnum_ash"}


def build_call_import_module_bytes(import_name: str, export_name: str) -> bytes:
    out = bytearray([0x00, 0x61, 0x73, 0x6D, 0x01, 0x00, 0x00, 0x00])

    types = bytearray()
    push_uleb(types, 2)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 1)
    push_u8(types, 0x7F)
    push_u8(types, 0x60)
    push_uleb(types, 0)
    push_uleb(types, 0)

    imports = bytearray()
    push_uleb(imports, 2)
    push_string(imports, "ccl")
    push_string(imports, "wasm_pending_throw_p")
    push_u8(imports, 0x00)
    push_uleb(imports, 0)
    push_string(imports, "ccl")
    push_string(imports, import_name)
    push_u8(imports, 0x00)
    push_uleb(imports, 1)

    funcs = bytearray()
    push_uleb(funcs, 1)
    push_uleb(funcs, 1)

    exports = bytearray()
    push_uleb(exports, 1)
    push_string(exports, export_name)
    push_u8(exports, 0x00)
    push_uleb(exports, 2)

    code = bytearray()
    body = bytearray()
    push_uleb(body, 0)
    push_u8(body, 0x10)
    push_uleb(body, 0)
    push_u8(body, 0x04)
    push_u8(body, 0x40)
    push_u8(body, 0x0F)
    push_u8(body, 0x0B)
    push_u8(body, 0x10)
    push_uleb(body, 1)
    push_u8(body, 0x0B)
    push_uleb(code, 1)
    push_uleb(code, len(body))
    code.extend(body)

    for sec in (
        section(1, types),
        section(2, imports),
        section(3, funcs),
        section(7, exports),
        section(10, code),
    ):
        out.extend(sec)

    return bytes(out)


class DynamicBuilder:
    def __init__(self, size: int, base: int) -> None:
        self.buf = bytearray(size)
        self.base = base
        self.off = 0

    def alloc(self, size: int, align_to: int = DNODE_SIZE) -> int:
        size = align(size, align_to)
        off = self.off
        self.off += size
        if self.off > len(self.buf):
            raise RuntimeError(f"dynamic area overflow: need {self.off} bytes, have {len(self.buf)}")
        return off

    def alloc_function(self, entry_fixnum: int) -> int:
        off = self.alloc(16)
        write_u32(self.buf, off + 0, FUNCTION_HEADER)
        write_u32(self.buf, off + 4, entry_fixnum)
        write_u32(self.buf, off + 8, entry_fixnum)
        write_u32(self.buf, off + 12, 0)
        return self.base + off + FULLTAG_MISC

    def alloc_u8_vector(self, data: bytes, subtag: int = SUBTAG_U8_VECTOR) -> int:
        data_bytes = bytes(data)
        off = self.alloc(4 + len(data_bytes), align_to=DNODE_SIZE)
        header = (len(data_bytes) << NUM_SUBTAG_BITS) | subtag
        write_u32(self.buf, off, header)
        self.buf[off + 4 : off + 4 + len(data_bytes)] = data_bytes
        return self.base + off + FULLTAG_MISC

    def alloc_base_string(self, text: str) -> int:
        data = text.encode("ascii")
        count = len(data)
        off = self.alloc(4 + count * 4)
        header = (count << NUM_SUBTAG_BITS) | SUBTAG_SIMPLE_BASE_STRING
        write_u32(self.buf, off, header)
        for i, ch in enumerate(data):
            write_u32(self.buf, off + 4 + i * 4, ch)
        return self.base + off + FULLTAG_MISC

    def alloc_simple_vector(self, elements: list[int]) -> int:
        count = len(elements)
        off = self.alloc(4 + count * 4)
        header = (count << NUM_SUBTAG_BITS) | SUBTAG_SIMPLE_VECTOR
        write_u32(self.buf, off, header)
        for i, value in enumerate(elements):
            write_u32(self.buf, off + 4 + i * 4, value)
        return self.base + off + FULLTAG_MISC

    def alloc_cons(self, car: int, cdr: int) -> int:
        off = self.alloc(8)
        write_u32(self.buf, off + 0, cdr)  # CDR at offset 0 (CCL/ARM convention)
        write_u32(self.buf, off + 4, car)  # CAR at offset 4
        return self.base + off + FULLTAG_CONS

    def alloc_list(self, items: list[int], nil_value: int) -> int:
        lst = nil_value
        for item in reversed(items):
            lst = self.alloc_cons(item, lst)
        return lst

def symbol_ptr(index: int) -> int:
    addr = NIL_BASE + (NRS_ORIGIN + index * SYMBOL_SIZE)
    return addr + FULLTAG_MISC


def build_static_area(function_ptr: int, compiled_modules_ptr: int) -> bytearray:
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
        elif i == WASM_MODULES_INDEX:
            vcell = compiled_modules_ptr
        elif i == WASM_CONST_POOLS_INDEX:
            vcell = NIL_VALUE

        # pname, vcell, fcell, package-predicate, flags, plist, binding-index
        write_u32(buf, off + 4, NIL_VALUE)
        write_u32(buf, off + 8, vcell)
        write_u32(buf, off + 12, unbound)
        write_u32(buf, off + 16, NIL_VALUE)
        write_u32(buf, off + 20, 0)
        write_u32(buf, off + 24, NIL_VALUE)
        write_u32(buf, off + 28, 0)

    return buf


def build_dynamic_area(entry_fixnum: int) -> tuple[bytearray, int, int]:
    dynamic_size = PAGE_SIZE * 16  # 64 KiB
    dynamic_base = ACTUAL_IMAGE_BASE + PURESPACE_RESERVE
    builder = DynamicBuilder(dynamic_size, dynamic_base)

    function_ptr = builder.alloc_function(entry_fixnum)

    entries: list[int] = []
    for export_name, entry_index, module_version, import_name, const_value in COMPILED_MODULES:
        if import_name == "wasm_return_constant":
            module_bytes = build_const_module_bytes(int(const_value), export_name)
        elif import_name == "wasm_if":
            true_value, false_value = const_value
            module_bytes = build_if_module_bytes(int(true_value), int(false_value), export_name)
        elif import_name == "wasm_if_arg":
            module_bytes = build_if_arg_module_bytes(int(const_value), export_name)
        elif import_name == "wasm_identity":
            module_bytes = build_identity_module_bytes(export_name)
        elif import_name == "wasm_identity_y":
            module_bytes = build_identity_y_module_bytes(export_name)
        elif import_name in _NONCOMMUTATIVE_IMPORTS:
            module_bytes = build_noncommutative_call_import_module_bytes(import_name, export_name)
        else:
            module_bytes = build_call_import_module_bytes(import_name, export_name)
        bytes_ptr = builder.alloc_u8_vector(module_bytes)
        name_ptr = builder.alloc_base_string(export_name)
        entry_fixnum_value = entry_index << FIXNUM_SHIFT
        version_fixnum_value = module_version << FIXNUM_SHIFT
        entry_vec = builder.alloc_simple_vector(
            [bytes_ptr, name_ptr, entry_fixnum_value, version_fixnum_value]
        )
        entries.append(entry_vec)

    registry_ptr = builder.alloc_list(entries, NIL_VALUE) if entries else NIL_VALUE
    return builder.buf, function_ptr, registry_ptr


def build_image(entry_index: int, output_path: Path) -> None:
    entry_fixnum = entry_index << FIXNUM_SHIFT
    dynamic_bytes, function_ptr, registry_ptr = build_dynamic_area(entry_fixnum)
    static_bytes = build_static_area(function_ptr, registry_ptr)

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
    parser.add_argument("--entrypoint-index", type=int, default=WASM_BOOT_ENTRY_INDEX)
    args = parser.parse_args()

    output_path = Path(args.output)
    build_image(args.entrypoint_index, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
