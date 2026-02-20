#!/usr/bin/env python3
"""Generate the CCL WASM ABI contract and cross-language validation artifacts.

Canonical source: C headers in lisp-kernel/.
Outputs:
  build/wasm32/abi-contract.json     — machine-readable ABI contract
  build/wasm32/abi-validate.h        — C _Static_assert header
  build/wasm32/abi-validate.lisp     — Lisp load-time assertions
  scripts/wasm/lib/abi-constants.mjs — JS ES module (generated constants)
  build/wasm32/abi_constants.py      — Python module (generated constants)

This script extracts constants from C headers by regex (not a preprocessor).
All target constants are simple #define NAME VALUE or #define NAME EXPR
where EXPR uses previously-defined constants. Struct layouts are parsed from
typedef struct blocks. Enums are parsed from enum { ... } blocks.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _strip_c_comments(text: str) -> str:
    """Remove C block and line comments, preserving line count."""
    # Block comments
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group().count('\n'), text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r'//[^\n]*', '', text)
    return text


def _expand_macros(expr: str) -> str:
    """Expand known function-like C macros in an expression string."""
    # Expand SUBTAG(tag, subtag) -> ((tag) | ((subtag) << ntagbits))
    # Expand IMM_SUBTAG(subtag) -> SUBTAG(fulltag_immheader, (subtag))
    # Expand NODE_SUBTAG(subtag) -> SUBTAG(fulltag_nodeheader, (subtag))
    changed = True
    limit = 10
    while changed and limit > 0:
        changed = False
        limit -= 1
        new = re.sub(
            r'\bIMM_SUBTAG\s*\(([^)]+)\)',
            r'((fulltag_immheader) | ((\1) << ntagbits))',
            expr,
        )
        if new != expr:
            expr = new
            changed = True
        new = re.sub(
            r'\bNODE_SUBTAG\s*\(([^)]+)\)',
            r'((fulltag_nodeheader) | ((\1) << ntagbits))',
            expr,
        )
        if new != expr:
            expr = new
            changed = True
        new = re.sub(
            r'\bSUBTAG\s*\(([^,]+),\s*([^)]+)\)',
            r'((\1) | ((\2) << ntagbits))',
            expr,
        )
        if new != expr:
            expr = new
            changed = True
        # make_header(subtag, count) -> (count << num_subtag_bits) | subtag
        new = re.sub(
            r'\bmake_header\s*\(([^,]+),\s*([^)]+)\)',
            r'((\2) << num_subtag_bits | (\1))',
            expr,
        )
        if new != expr:
            expr = new
            changed = True
        # fixnum_bitmask(n) -> (1 << ((n) + fixnumshift))
        new = re.sub(
            r'\bfixnum_bitmask\s*\(([^)]+)\)',
            r'(1 << ((\1) + fixnumshift))',
            expr,
        )
        if new != expr:
            expr = new
            changed = True
    return expr


def _eval_expr(expr: str, syms: dict[str, int]) -> int:
    """Evaluate a simple C integer expression using known symbols."""
    expr = expr.strip()
    # Remove trailing 'u' or 'U' suffix
    expr = re.sub(r'[uU]$', '', expr)
    # Expand function-like macros
    expr = _expand_macros(expr)
    # Replace known symbols (longest first to avoid partial matches)
    for name, val in sorted(syms.items(), key=lambda x: -len(x[0])):
        expr = re.sub(r'\b' + re.escape(name) + r'\b', str(val), expr)
    # Sanity: only allow digits, parens, operators, whitespace, hex
    if not re.match(r'^[\s\d\+\-\*\/\%\(\)\<\>\&\|\^\~xXaAbBcCdDeEfF]+$', expr):
        raise ValueError(f"Cannot evaluate expression: {expr!r}")
    try:
        return int(eval(expr, {"__builtins__": {}}))  # noqa: S307
    except Exception as e:
        raise ValueError(f"Failed to evaluate {expr!r}: {e}") from e


def extract_defines(text: str, syms: dict[str, int] | None = None) -> dict[str, int]:
    """Extract #define NAME VALUE from preprocessed C text."""
    if syms is None:
        syms = {}
    results: dict[str, int] = {}
    for m in re.finditer(r'^\s*#\s*define\s+(\w+)\s+(.+?)$', text, re.MULTILINE):
        name = m.group(1)
        value_str = m.group(2).strip()
        # Skip macro-like defines with parameters
        if '(' in name:
            continue
        # Skip string/char defines
        if value_str.startswith('"') or value_str.startswith("'"):
            continue
        try:
            val = _eval_expr(value_str, {**syms, **results})
            results[name] = val
        except (ValueError, SyntaxError):
            pass  # Skip non-numeric defines
    return results


def extract_structs(text: str) -> dict[str, list[str]]:
    """Extract typedef struct { fields... } name; patterns."""
    structs: dict[str, list[str]] = {}
    pattern = re.compile(
        r'typedef\s+struct\s+(\w+)?\s*\{([^}]*)\}\s*(\w+)\s*;',
        re.DOTALL
    )
    for m in pattern.finditer(text):
        name = m.group(3)
        body = m.group(2)
        fields: list[str] = []
        for line in body.splitlines():
            line = line.strip().rstrip(';').strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            # Extract field name (last word before possible array brackets)
            parts = line.split()
            if len(parts) >= 2:
                field_name = parts[-1]
                # Strip pointer stars
                field_name = field_name.lstrip('*')
                # Strip array dimensions
                field_name = re.sub(r'\[.*\]', '', field_name)
                if field_name and field_name.isidentifier():
                    fields.append(field_name)
        structs[name] = fields
    return structs


def extract_enum(text: str, syms: dict[str, int]) -> dict[str, int]:
    """Extract enum { NAME = VALUE, ... } blocks."""
    results: dict[str, int] = {}
    for m in re.finditer(r'enum\s*\{([^}]*)\}', text, re.DOTALL):
        body = m.group(1)
        current = 0
        for entry in body.split(','):
            entry = entry.strip()
            if not entry:
                continue
            eq = entry.find('=')
            if eq >= 0:
                name = entry[:eq].strip()
                value_str = entry[eq+1:].strip()
                try:
                    current = _eval_expr(value_str, {**syms, **results})
                except (ValueError, SyntaxError):
                    continue
            else:
                name = entry.strip()
            if name.isidentifier():
                results[name] = current
                current += 1
    return results


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_all(repo_root: Path) -> dict:
    """Extract all ABI constants from C headers."""
    kernel_dir = repo_root / "lisp-kernel"

    # Read and preprocess source files
    constants_h = _strip_c_comments((kernel_dir / "constants.h").read_text())
    arm_h = _strip_c_comments((kernel_dir / "arm-constants.h").read_text())
    host_h = _strip_c_comments((kernel_dir / "wasm-host.h").read_text())
    stubs_c = _strip_c_comments((kernel_dir / "wasm-kernel-stubs.c").read_text())

    # Build symbol table from constants.h first (arm-constants.h includes it)
    syms: dict[str, int] = {}
    syms.update(extract_defines(constants_h, syms))
    syms.update(extract_defines(arm_h, syms))
    syms.update(extract_defines(host_h, syms))

    # Extract structs from constants.h and arm-constants.h
    all_structs = {}
    all_structs.update(extract_structs(constants_h))
    all_structs.update(extract_structs(arm_h))

    # Extract enum from wasm-kernel-stubs.c
    enum_vals = extract_enum(stubs_c, syms)

    # --- Assemble contract ---

    # Tag constants
    tag_names = [
        "ntagbits", "nlisptagbits", "nfixnumtagbits", "num_subtag_bits",
        "fixnumshift", "fixnum_shift", "fulltagmask", "tagmask", "fixnummask",
        "ncharcodebits", "charcode_shift", "node_size", "node_shift",
        "tag_fixnum", "tag_list", "tag_misc", "tag_imm",
        "fulltag_even_fixnum", "fulltag_nil", "fulltag_nodeheader",
        "fulltag_imm", "fulltag_odd_fixnum", "fulltag_cons",
        "fulltag_misc", "fulltag_immheader",
        "misc_header_offset", "misc_subtag_offset", "misc_data_offset",
        "misc_dfloat_offset", "t_offset", "nil_value",
    ]
    tags: dict[str, int] = {}
    for name in tag_names:
        if name not in syms:
            raise SystemExit(f"Missing tag constant: {name}")
        tags[name] = syms[name]

    # Subtag constants
    subtag_names = [
        "subtag_bignum", "subtag_ratio", "subtag_single_float",
        "subtag_double_float", "subtag_complex",
        "subtag_bit_vector", "subtag_complex_double_float_vector",
        "subtag_complex_single_float_vector", "subtag_double_float_vector",
        "subtag_s16_vector", "subtag_u16_vector",
        "subtag_s8_vector", "subtag_u8_vector",
        "subtag_simple_base_string", "subtag_fixnum_vector",
        "subtag_s32_vector", "subtag_u32_vector", "subtag_single_float_vector",
        "subtag_vectorH", "subtag_arrayH", "subtag_simple_vector",
        "subtag_macptr", "subtag_dead_macptr", "subtag_code_vector",
        "subtag_creole", "subtag_complex_single_float", "subtag_complex_double_float",
        "subtag_pseudofunction", "subtag_catch_frame", "subtag_function",
        "subtag_basic_stream", "subtag_symbol", "subtag_lock",
        "subtag_hash_vector", "subtag_pool", "subtag_weak",
        "subtag_package", "subtag_slot_vector", "subtag_instance",
        "subtag_struct", "subtag_istruct", "subtag_value_cell", "subtag_xfunction",
        "subtag_character",
    ]
    subtags: dict[str, int] = {}
    for name in subtag_names:
        if name not in syms:
            raise SystemExit(f"Missing subtag constant: {name}")
        subtags[name] = syms[name]

    # Register indices
    reg_names_ordered = [
        "imm0", "imm1", "imm2", "rcontext",
        "arg_z", "arg_y", "arg_x",
        "temp0", "temp1", "temp2",
        "vsp", "Rfn", "allocptr", "Rsp", "Rlr", "Rpc",
    ]
    registers: dict[str, int] = {}
    for name in reg_names_ordered:
        if name not in syms:
            raise SystemExit(f"Missing register constant: {name}")
        registers[name] = syms[name]

    reg_aliases = {
        "fname": "temp1", "nfn": "temp2",
        "nargs": "imm2", "allocbase": "temp0",
        "next_method_context": "temp1",
    }

    # Kernel opcodes
    opcode_names = [
        "KERNEL_OP_CAPS", "KERNEL_OP_LOG",
        "KERNEL_OP_STREAM_WRITE", "KERNEL_OP_STREAM_READ",
        "KERNEL_OP_TIME_NOW", "KERNEL_OP_STREAM_OPEN", "KERNEL_OP_STREAM_CLOSE",
        "KERNEL_OP_COMPILED_MODULES_REFRESH",
        "KERNEL_OP_FS_PROBE", "KERNEL_OP_FS_TRUENAME", "KERNEL_OP_FS_DIRECTORY",
        "KERNEL_OP_FS_FILE_WRITE_DATE", "KERNEL_OP_FS_RENAME", "KERNEL_OP_FS_DELETE",
        "KERNEL_OP_FS_ENSURE_DIRS", "KERNEL_OP_FS_DELETE_EMPTY_DIR", "KERNEL_OP_FS_DELETE_TREE",
        "KERNEL_OP_STREAM_SEEK", "KERNEL_OP_STREAM_TRUNCATE",
        "KERNEL_OP_UI_POLL", "KERNEL_OP_UI_RENDER", "KERNEL_OP_UI_MEASURE_TEXT",
        "KERNEL_OP_RUNTIME_EVENT", "KERNEL_OP_RUNTIME_COMMAND_POLL",
    ]
    opcodes: dict[str, int] = {}
    for name in opcode_names:
        if name not in syms:
            raise SystemExit(f"Missing kernel opcode: {name}")
        opcodes[name] = syms[name]

    status_names = ["KERNEL_STATUS_PENDING", "KERNEL_STATUS_DONE", "KERNEL_STATUS_ERROR"]
    statuses: dict[str, int] = {}
    for name in status_names:
        if name not in syms:
            raise SystemExit(f"Missing kernel status: {name}")
        statuses[name] = syms[name]

    stream_kind_names = [
        "KERNEL_STREAM_KIND_PIPE", "KERNEL_STREAM_KIND_NAMED_RO", "KERNEL_STREAM_KIND_FILE",
    ]
    stream_kinds: dict[str, int] = {}
    for name in stream_kind_names:
        if name not in syms:
            raise SystemExit(f"Missing stream kind: {name}")
        stream_kinds[name] = syms[name]

    file_mode_names = [
        "WASM_FILE_MODE_READ", "WASM_FILE_MODE_WRITE", "WASM_FILE_MODE_CREATE",
        "WASM_FILE_MODE_TRUNCATE", "WASM_FILE_MODE_APPEND",
    ]
    file_modes: dict[str, int] = {}
    for name in file_mode_names:
        if name not in syms:
            raise SystemExit(f"Missing file mode: {name}")
        file_modes[name] = syms[name]

    # Boot entry and named subprim indices from enum
    boot_entry_names = [
        "WASM_BOOT_ENTRY_INDEX", "WASM_TEST_ENTRY_INDEX", "WASM_CONST_ENTRY_INDEX",
    ]
    boot_entries: dict[str, int] = {}
    for name in boot_entry_names:
        if name not in enum_vals:
            raise SystemExit(f"Missing boot entry index: {name}")
        boot_entries[name] = enum_vals[name]

    named_subprim_names = [
        "WASM_SUBPRIM_FUNCALL_INDEX", "WASM_SUBPRIM_MKCATCH1V_INDEX",
        "WASM_SUBPRIM_MKUNWIND_INDEX", "WASM_SUBPRIM_VALUES_INDEX",
        "WASM_SUBPRIM_NTHROWVALUES_INDEX", "WASM_SUBPRIM_NTHROW1VALUE_INDEX",
    ]
    named_subprims: dict[str, int] = {}
    for name in named_subprim_names:
        if name not in enum_vals:
            raise SystemExit(f"Missing named subprim index: {name}")
        named_subprims[name] = enum_vals[name]

    # Object layouts — only the structs we need to validate
    target_structs = {
        "cons": {"c_name": "cons", "fields": ["cdr", "car"]},
        "lispsymbol": {
            "c_name": "lispsymbol",
            "fields": ["header", "pname", "vcell", "fcell",
                        "package_predicate", "flags", "plist", "binding_index"],
        },
        "ratio": {"c_name": "ratio", "fields": ["header", "numer", "denom"]},
        "macptr": {"c_name": "macptr", "fields": ["header", "address", "class", "type"]},
        "xmacptr": {
            "c_name": "xmacptr",
            "fields": ["header", "address", "class", "type", "flags", "link"],
        },
        "package": {
            "c_name": "package",
            "fields": ["header", "itab", "etab", "used", "used_by", "names", "shadowed"],
        },
    }

    # Validate struct fields match what we parsed
    layouts: dict[str, dict] = {}
    for key, spec in target_structs.items():
        c_name = spec["c_name"]
        expected_fields = spec["fields"]
        parsed = all_structs.get(c_name, [])
        if parsed and parsed != expected_fields:
            raise SystemExit(
                f"Struct {c_name} field mismatch:\n"
                f"  expected: {expected_fields}\n"
                f"  parsed:   {parsed}"
            )
        field_size = syms.get("node_size", 4)
        layouts[key] = {
            "c_name": c_name,
            "fields": expected_fields,
            "field_size": field_size,
            "total_size": len(expected_fields) * field_size,
        }

    # Internal consistency checks
    assert tags["fulltag_cons"] == 5, f"fulltag_cons must be 5, got {tags['fulltag_cons']}"
    assert tags["fulltag_misc"] == 6, f"fulltag_misc must be 6, got {tags['fulltag_misc']}"
    assert tags["node_size"] == 4, f"node_size must be 4, got {tags['node_size']}"

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_from": [
            "lisp-kernel/arm-constants.h",
            "lisp-kernel/constants.h",
            "lisp-kernel/wasm-host.h",
            "lisp-kernel/wasm-kernel-stubs.c",
        ],
        "tag_constants": tags,
        "subtag_constants": subtags,
        "registers": {
            "indices": registers,
            "ordered_names": reg_names_ordered,
            "aliases": reg_aliases,
        },
        "kernel_ops": {
            "status_codes": statuses,
            "opcodes": opcodes,
            "stream_kinds": stream_kinds,
            "file_modes": file_modes,
        },
        "boot_entries": boot_entries,
        "named_subprim_indices": named_subprims,
        "object_layouts": layouts,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_json(out_dir: Path, contract: dict) -> None:
    path = out_dir / "abi-contract.json"
    path.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n")
    print(f"  wrote {path}")


def write_c_header(out_dir: Path, contract: dict) -> None:
    tags = contract["tag_constants"]
    subtags = contract["subtag_constants"]
    regs = contract["registers"]["indices"]
    opcodes = contract["kernel_ops"]["opcodes"]
    statuses = contract["kernel_ops"]["status_codes"]
    stream_kinds = contract["kernel_ops"]["stream_kinds"]
    file_modes = contract["kernel_ops"]["file_modes"]
    boot = contract["boot_entries"]
    layouts = contract["object_layouts"]

    lines: list[str] = []
    lines.append("/* AUTO-GENERATED by generate_abi_contract.py — DO NOT EDIT */")
    lines.append("#ifndef CCL_ABI_VALIDATE_H")
    lines.append("#define CCL_ABI_VALIDATE_H")
    lines.append("")
    lines.append("/* Prerequisites: stddef.h, constants.h, wasm-host.h")
    lines.append("   (provided by wasm-constants-bridge.h before this include) */")
    lines.append("")

    # Tag constants
    lines.append("/* Tag constants */")
    for name, val in tags.items():
        lines.append(f'_Static_assert({name} == {val}, "ABI contract: {name}");')
    lines.append("")

    # Subtag constants
    lines.append("/* Subtag constants */")
    for name, val in subtags.items():
        lines.append(f'_Static_assert({name} == {val}, "ABI contract: {name}");')
    lines.append("")

    # Register indices
    lines.append("/* Register indices */")
    for name, val in regs.items():
        lines.append(f'_Static_assert({name} == {val}, "ABI contract: {name}");')
    lines.append("")

    # Kernel opcodes
    lines.append("/* Kernel opcodes */")
    for name, val in opcodes.items():
        lines.append(f'_Static_assert({name} == 0x{val:08x}u, "ABI contract: {name}");')
    lines.append("")

    # Status codes
    lines.append("/* Kernel status codes */")
    for name, val in statuses.items():
        lines.append(f'_Static_assert({name} == {val}u, "ABI contract: {name}");')
    lines.append("")

    # Stream kinds
    lines.append("/* Stream kinds */")
    for name, val in stream_kinds.items():
        lines.append(f'_Static_assert({name} == {val}u, "ABI contract: {name}");')
    lines.append("")

    # File modes
    lines.append("/* File modes */")
    for name, val in file_modes.items():
        lines.append(f'_Static_assert({name} == 0x{val:x}u, "ABI contract: {name}");')
    lines.append("")

    # Object layouts — sizeof and offsetof
    lines.append("/* Object layouts */")
    for key, layout in layouts.items():
        c_name = layout["c_name"]
        total = layout["total_size"]
        lines.append(f'_Static_assert(sizeof(struct {c_name}) == {total}, '
                      f'"ABI contract: sizeof({c_name})");')
        for i, field in enumerate(layout["fields"]):
            offset = i * layout["field_size"]
            lines.append(f'_Static_assert(offsetof(struct {c_name}, {field}) == {offset}, '
                          f'"ABI contract: {c_name}.{field} offset");')
    lines.append("")

    lines.append("#endif /* CCL_ABI_VALIDATE_H */")
    lines.append("")

    path = out_dir / "abi-validate.h"
    path.write_text("\n".join(lines))
    print(f"  wrote {path}")


def write_lisp(out_dir: Path, contract: dict) -> None:
    tags = contract["tag_constants"]
    subtags = contract["subtag_constants"]
    boot = contract["boot_entries"]
    named_sp = contract["named_subprim_indices"]

    # Map C names to Lisp names
    def c_to_lisp(name: str) -> str:
        return name.replace("_", "-")

    lines: list[str] = []
    lines.append(";;; AUTO-GENERATED by generate_abi_contract.py — DO NOT EDIT")
    lines.append(";;; Load-time assertions: cross-check wasm-arch.lisp against abi-contract.json")
    lines.append("")
    lines.append('(in-package "WASM")')
    lines.append("")
    lines.append("(eval-when (:compile-toplevel :load-toplevel :execute)")
    lines.append("  (flet ((abi-check (name expected actual)")
    lines.append('           (unless (eql expected actual)')
    lines.append('             (error "ABI contract violation: ~A expected ~D got ~D"')
    lines.append("                    name expected actual))))")
    lines.append("")

    # Tag constants — guarded by boundp since not all C constants have
    # Lisp equivalents (e.g. node_shift exists in C but not wasm-arch.lisp).
    # The C _Static_assert still validates these; Lisp checks what it defines.
    lines.append("    ;; Tag constants")
    for c_name, val in tags.items():
        lisp_name = c_to_lisp(c_name)
        lines.append(f"    (when (boundp '{lisp_name})")
        lines.append(f'      (abi-check "{lisp_name}" {val} (symbol-value \'{lisp_name})))')
    lines.append("")

    # Key subtags (the ones most likely to cause bugs)
    lines.append("    ;; Key subtag constants")
    key_subtags = [
        "subtag_symbol", "subtag_function", "subtag_simple_vector",
        "subtag_u8_vector", "subtag_simple_base_string", "subtag_cons",
        "subtag_bignum", "subtag_ratio", "subtag_macptr",
        "subtag_catch_frame", "subtag_character",
    ]
    for c_name in key_subtags:
        if c_name in subtags:
            lisp_name = c_to_lisp(c_name)
            lines.append(f"    (when (boundp '{lisp_name})")
            lines.append(f'      (abi-check "{lisp_name}" {subtags[c_name]} (symbol-value \'{lisp_name})))')
    lines.append("")

    # Named subprim index cross-checks — guarded since *wasm-subprim-names*
    # may not be bound in all loading contexts (e.g. cross-compiler bootstrap).
    lines.append("    ;; Named subprim indices (cross-check against *wasm-subprim-names*)")
    sp_to_lisp_sym = {
        "WASM_SUBPRIM_FUNCALL_INDEX": ".SPfuncall",
        "WASM_SUBPRIM_MKCATCH1V_INDEX": ".SPmkcatch1v",
        "WASM_SUBPRIM_MKUNWIND_INDEX": ".SPmkunwind",
        "WASM_SUBPRIM_VALUES_INDEX": ".SPvalues",
        "WASM_SUBPRIM_NTHROWVALUES_INDEX": ".SPnthrowvalues",
        "WASM_SUBPRIM_NTHROW1VALUE_INDEX": ".SPnthrow1value",
    }
    lines.append("    (when (boundp '*wasm-subprim-names*)")
    for c_name, idx in named_sp.items():
        lisp_sym = sp_to_lisp_sym.get(c_name)
        if lisp_sym:
            lines.append(
                f'      (abi-check "{c_name}" {idx}'
                f" (position '{lisp_sym} *wasm-subprim-names*))"
            )
    lines.append("")

    # Subprims count
    lines.append("      ;; Subprims count (must match generated subprims-map.json)")
    lines.append('      (abi-check "subprims-count" +wasm-subprims-count+')
    lines.append("                 (length *wasm-subprim-names*))")
    lines.append("    )  ;; end when boundp *wasm-subprim-names*")
    lines.append("")

    lines.append("    ))")  # close flet and eval-when
    lines.append("")

    path = out_dir / "abi-validate.lisp"
    path.write_text("\n".join(lines))
    print(f"  wrote {path}")


def write_js(scripts_lib_dir: Path, contract: dict) -> None:
    tags = contract["tag_constants"]
    subtags = contract["subtag_constants"]
    regs = contract["registers"]
    opcodes = contract["kernel_ops"]["opcodes"]
    statuses = contract["kernel_ops"]["status_codes"]
    stream_kinds = contract["kernel_ops"]["stream_kinds"]
    file_modes = contract["kernel_ops"]["file_modes"]
    boot = contract["boot_entries"]
    named_sp = contract["named_subprim_indices"]
    layouts = contract["object_layouts"]

    lines: list[str] = []
    lines.append("/* AUTO-GENERATED by generate_abi_contract.py — DO NOT EDIT */")
    lines.append("")

    # Tag constants
    lines.append("// Tag system constants")
    js_tag_exports = {
        "NTAGBITS": tags["ntagbits"],
        "NLISPTAGBITS": tags["nlisptagbits"],
        "FIXNUM_SHIFT": tags["fixnumshift"],
        "FULLTAGMASK": tags["fulltagmask"],
        "TAGMASK": tags["tagmask"],
        "FIXNUMMASK": tags["fixnummask"],
        "NUM_SUBTAG_BITS": tags["num_subtag_bits"],
        "SUBTAG_MASK": (1 << tags["num_subtag_bits"]) - 1,
        "NODE_SIZE": tags["node_size"],
        "CHARCODE_SHIFT": tags["charcode_shift"],
        "TAG_FIXNUM": tags["tag_fixnum"],
        "TAG_LIST": tags["tag_list"],
        "TAG_MISC": tags["tag_misc"],
        "TAG_IMM": tags["tag_imm"],
        "FULLTAG_EVEN_FIXNUM": tags["fulltag_even_fixnum"],
        "FULLTAG_NIL": tags["fulltag_nil"],
        "FULLTAG_NODEHEADER": tags["fulltag_nodeheader"],
        "FULLTAG_IMM": tags["fulltag_imm"],
        "FULLTAG_ODD_FIXNUM": tags["fulltag_odd_fixnum"],
        "FULLTAG_CONS": tags["fulltag_cons"],
        "FULLTAG_MISC": tags["fulltag_misc"],
        "FULLTAG_IMMHEADER": tags["fulltag_immheader"],
        "MISC_HEADER_OFFSET": tags["misc_header_offset"],
        "MISC_DATA_OFFSET": tags["misc_data_offset"],
        "T_OFFSET": tags["t_offset"],
        "NIL_VALUE": tags["nil_value"],
    }
    for name, val in js_tag_exports.items():
        if val < 0:
            lines.append(f"export const {name} = {val};")
        elif val > 255:
            lines.append(f"export const {name} = 0x{val:x};")
        else:
            lines.append(f"export const {name} = {val};")
    lines.append("")

    # Key subtags (computed)
    lines.append("// Subtag constants")
    js_subtag_exports = {
        "SUBTAG_BIGNUM": subtags["subtag_bignum"],
        "SUBTAG_RATIO": subtags["subtag_ratio"],
        "SUBTAG_SINGLE_FLOAT": subtags["subtag_single_float"],
        "SUBTAG_DOUBLE_FLOAT": subtags["subtag_double_float"],
        "SUBTAG_COMPLEX": subtags["subtag_complex"],
        "SUBTAG_SYMBOL": subtags["subtag_symbol"],
        "SUBTAG_FUNCTION": subtags["subtag_function"],
        "SUBTAG_CATCH_FRAME": subtags["subtag_catch_frame"],
        "SUBTAG_SIMPLE_VECTOR": subtags["subtag_simple_vector"],
        "SUBTAG_VECTORH": subtags["subtag_vectorH"],
        "SUBTAG_ARRAYH": subtags["subtag_arrayH"],
        "SUBTAG_U8_VECTOR": subtags["subtag_u8_vector"],
        "SUBTAG_S8_VECTOR": subtags["subtag_s8_vector"],
        "SUBTAG_U16_VECTOR": subtags["subtag_u16_vector"],
        "SUBTAG_S16_VECTOR": subtags["subtag_s16_vector"],
        "SUBTAG_U32_VECTOR": subtags["subtag_u32_vector"],
        "SUBTAG_S32_VECTOR": subtags["subtag_s32_vector"],
        "SUBTAG_SINGLE_FLOAT_VECTOR": subtags["subtag_single_float_vector"],
        "SUBTAG_DOUBLE_FLOAT_VECTOR": subtags["subtag_double_float_vector"],
        "SUBTAG_FIXNUM_VECTOR": subtags["subtag_fixnum_vector"],
        "SUBTAG_SIMPLE_BASE_STRING": subtags["subtag_simple_base_string"],
        "SUBTAG_BIT_VECTOR": subtags["subtag_bit_vector"],
        "SUBTAG_MACPTR": subtags["subtag_macptr"],
        "SUBTAG_CODE_VECTOR": subtags["subtag_code_vector"],
        "SUBTAG_CHARACTER": subtags["subtag_character"],
        "SUBTAG_PSEUDOFUNCTION": subtags["subtag_pseudofunction"],
        "SUBTAG_VALUE_CELL": subtags["subtag_value_cell"],
        "SUBTAG_INSTANCE": subtags["subtag_instance"],
        "SUBTAG_LOCK": subtags["subtag_lock"],
        "SUBTAG_HASH_VECTOR": subtags["subtag_hash_vector"],
        "SUBTAG_PACKAGE": subtags["subtag_package"],
        "SUBTAG_WEAK": subtags["subtag_weak"],
        "SUBTAG_POOL": subtags["subtag_pool"],
        "SUBTAG_STRUCT": subtags["subtag_struct"],
        "SUBTAG_ISTRUCT": subtags["subtag_istruct"],
        "SUBTAG_SLOT_VECTOR": subtags["subtag_slot_vector"],
        "SUBTAG_BASIC_STREAM": subtags["subtag_basic_stream"],
        "SUBTAG_XFUNCTION": subtags["subtag_xfunction"],
    }
    for name, val in js_subtag_exports.items():
        lines.append(f"export const {name} = 0x{val:02x};")
    lines.append("")

    # Object layout offsets
    lines.append("// Object layout offsets")
    cons_layout = layouts["cons"]
    for i, field in enumerate(cons_layout["fields"]):
        offset = i * cons_layout["field_size"]
        lines.append(f"export const CONS_{field.upper()}_OFFSET = {offset};")
    symbol_layout = layouts["lispsymbol"]
    for i, field in enumerate(symbol_layout["fields"]):
        offset = i * symbol_layout["field_size"]
        lines.append(f"export const SYMBOL_{field.upper()}_OFFSET = {offset};")
    lines.append(f"export const SYMBOL_ELEMENT_COUNT = {len(symbol_layout['fields']) - 1};")
    func_layout = layouts.get("function", None)
    # Function layout isn't in constants.h as a struct, but we know it
    lines.append(f"export const FUNCTION_ELEMENT_COUNT = 2;")
    lines.append("")

    # Kernel status codes
    lines.append("// Kernel status codes")
    for name, val in statuses.items():
        lines.append(f"export const {name} = {val};")
    lines.append("")

    # Kernel opcodes
    lines.append("// Kernel request opcodes")
    for name, val in opcodes.items():
        lines.append(f"export const {name} = 0x{val:08x};")
    lines.append("")

    # Stream kinds
    lines.append("// Stream kinds")
    for name, val in stream_kinds.items():
        lines.append(f"export const {name} = {val};")
    lines.append("")

    # File modes
    lines.append("// File mode flags")
    for name, val in file_modes.items():
        lines.append(f"export const {name} = 0x{val:x};")
    lines.append("")

    # Boot entry indices
    lines.append("// Boot entry indices")
    for name, val in boot.items():
        lines.append(f"export const {name} = {val};")
    lines.append("")

    # Named subprim indices
    lines.append("// Named subprim indices")
    for name, val in named_sp.items():
        lines.append(f"export const {name} = {val};")
    lines.append("")

    # Register indices
    lines.append("// Register indices (GPR array)")
    for name, val in regs["indices"].items():
        js_name = f"REG_{name.upper()}"
        lines.append(f"export const {js_name} = {val};")
    lines.append("")

    # GPR names array (for diagnostics)
    lines.append("// GPR display names (indexed by register number)")
    gpr_display = []
    for name in regs["ordered_names"]:
        # Use common aliases where known
        aliases = regs["aliases"]
        display = name
        if name == "imm2":
            display = "nargs"
        elif name == "temp2":
            display = "nfn"
        elif name == "rcontext":
            display = "rctx"
        gpr_display.append(f'  "{display}"')
    lines.append("export const GPR_NAMES = [")
    lines.append(",\n".join(gpr_display))
    lines.append("];")
    lines.append("")

    path = scripts_lib_dir / "abi-constants.mjs"
    path.write_text("\n".join(lines))
    print(f"  wrote {path}")


def write_python(out_dir: Path, contract: dict) -> None:
    tags = contract["tag_constants"]
    subtags = contract["subtag_constants"]
    boot = contract["boot_entries"]
    layouts = contract["object_layouts"]

    lines: list[str] = []
    lines.append("# AUTO-GENERATED by generate_abi_contract.py — DO NOT EDIT")
    lines.append("")

    # Tag constants (matching names used in make_minimal_image.py)
    py_exports = {
        "FULLTAG_NIL": tags["fulltag_nil"],
        "FULLTAG_CONS": tags["fulltag_cons"],
        "FULLTAG_MISC": tags["fulltag_misc"],
        "FULLTAG_NODEHEADER": tags["fulltag_nodeheader"],
        "FULLTAG_IMM": tags["fulltag_imm"],
        "FULLTAG_IMMHEADER": tags["fulltag_immheader"],
        "NTAGBITS": tags["ntagbits"],
        "NUM_SUBTAG_BITS": tags["num_subtag_bits"],
        "FIXNUM_SHIFT": tags["fixnumshift"],
        "DNODE_SIZE": tags["node_size"] * 2,
        "NODE_SIZE": tags["node_size"],
    }
    lines.append("# Tag constants")
    for name, val in py_exports.items():
        lines.append(f"{name} = {val}")
    lines.append("")

    # Subtags (computed from tag constants)
    lines.append("# Subtag constants")
    py_subtags = {
        "SUBTAG_SYMBOL": subtags["subtag_symbol"],
        "SUBTAG_FUNCTION": subtags["subtag_function"],
        "SUBTAG_SIMPLE_VECTOR": subtags["subtag_simple_vector"],
        "SUBTAG_U8_VECTOR": subtags["subtag_u8_vector"],
        "SUBTAG_SIMPLE_BASE_STRING": subtags["subtag_simple_base_string"],
    }
    for name, val in py_subtags.items():
        lines.append(f"{name} = 0x{val:02x}")
    lines.append("")

    # Layout constants
    lines.append("# Object layout element counts")
    sym = layouts["lispsymbol"]
    lines.append(f"SYMBOL_ELEMENT_COUNT = {len(sym['fields']) - 1}")
    lines.append("FUNCTION_ELEMENT_COUNT = 2")
    lines.append("")

    # Computed headers
    lines.append("# Computed headers")
    lines.append(f"SYMBOL_HEADER = (SYMBOL_ELEMENT_COUNT << NUM_SUBTAG_BITS) | SUBTAG_SYMBOL")
    lines.append(f"FUNCTION_HEADER = (FUNCTION_ELEMENT_COUNT << NUM_SUBTAG_BITS) | SUBTAG_FUNCTION")
    lines.append("")

    # NIL / T / static layout
    lines.append("# NIL / T / static layout")
    lines.append(f"NIL_BASE = 0x{0x04000000:08x}")
    lines.append(f"NIL_VALUE = NIL_BASE + FULLTAG_NIL")
    lines.append(f"T_OFFSET = {tags['t_offset']}")
    lines.append(f"T_VALUE = NIL_VALUE + T_OFFSET")
    lines.append(f"STATIC_BASE = 0x03FFF000")
    lines.append(f"SYMBOL_SIZE = {sym['total_size']}")
    lines.append("")

    # Boot entry indices
    lines.append("# Boot entry indices")
    for name, val in boot.items():
        lines.append(f"{name} = {val}")
    lines.append("")

    path = out_dir / "abi_constants.py"
    path.write_text("\n".join(lines))
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    build_dir = repo_root / "build" / "wasm32"
    scripts_lib = repo_root / "scripts" / "wasm" / "lib"

    build_dir.mkdir(parents=True, exist_ok=True)

    print("Extracting ABI constants from C headers...")
    contract = extract_all(repo_root)

    print("Generating artifacts:")
    write_json(build_dir, contract)
    write_c_header(build_dir, contract)
    write_lisp(build_dir, contract)
    write_js(scripts_lib, contract)
    write_python(build_dir, contract)

    # Summary
    n_tags = len(contract["tag_constants"])
    n_subtags = len(contract["subtag_constants"])
    n_ops = len(contract["kernel_ops"]["opcodes"])
    n_layouts = sum(len(l["fields"]) for l in contract["object_layouts"].values())
    print(f"\nABI contract: {n_tags} tag constants, {n_subtags} subtags, "
          f"{n_ops} opcodes, {n_layouts} struct fields validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
