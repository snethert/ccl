# Building CCL WASM

**Last Updated:** 2026-02-15

This guide covers how to build the CCL WASM port from source.

---

## Quick Start

**Most users:** Just run these commands to build everything:

```bash
cd /path/to/ccl
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

That's it! The script will:
- Auto-detect your toolchain
- Build the WASM kernel
- Compile runtime modules
- Create necessary images

**Build artifacts** will be in `build/wasm32/`:
```
build/wasm32/
├── kernel/wasmcl.wasm       # WASM kernel binary
├── images/*.image           # Heap images
└── modules/*.json           # Compiled modules
```

---

## Prerequisites

### macOS (Homebrew)

```bash
brew install llvm lld wasi-libc
```

That's all you need. The `env.sh` script auto-detects Homebrew installations.

### Linux (Ubuntu/Debian/Mint)

```bash
sudo apt install clang-18 lld-18 wasi-libc
```

Or use your distribution's package manager equivalent.

### Verification

Check your toolchain:

```bash
source scripts/wasm/env.sh
```

You should see output like:

```
CCL WASM Environment Configured
================================
Platform:      macos
Compiler:      /usr/local/opt/llvm/bin/clang
Linker:        /usr/local/opt/lld/bin/wasm-ld
Target:        wasm32-unknown-unknown
Build Dir:     /Users/you/ccl/build/wasm32
...
```

---

## Building

### Full Build (Recommended)

Rebuild everything from scratch:

```bash
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

### Incremental Build

Build only what changed:

```bash
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh --no-force
```

### Build Individual Components

**Kernel only:**
```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

**Boot image only:**
```bash
scripts/wasm/build-wasm-boot.sh
```

**Runtime modules only:**
```bash
scripts/wasm/compile-wasm-fasls.sh
```

---

## Environment Variables

All build paths can be customized via environment variables. Set them **before** sourcing `env.sh`:

### Toolchain

| Variable | Description | Default |
|----------|-------------|---------|
| `CCL_WASM_CC` | C compiler | `clang` (auto-detected) |
| `CCL_WASM_LD` | WASM linker | `wasm-ld` (auto-detected) |
| `CCL_WASM_TARGET` | Target triple | `wasm32-unknown-unknown` |
| `CCL_WASM_SYSROOT` | WASI sysroot path | (auto-detected) |

### Build Directories

| Variable | Description | Default |
|----------|-------------|---------|
| `CCL_WASM_BUILD_DIR` | Root build directory | `build/wasm32` |
| `CCL_WASM_KERNEL_DIR` | Kernel output | `$BUILD_DIR/kernel` |
| `CCL_WASM_IMAGES_DIR` | Image files | `$BUILD_DIR/images` |
| `CCL_WASM_MODULES_DIR` | Module files | `$BUILD_DIR/modules` |
| `CCL_WASM_SUBPRIMS_DIR` | Subprims module | `$BUILD_DIR/subprims` |

### Compiler Flags

| Variable | Description | Default |
|----------|-------------|---------|
| `CCL_WASM_OPT` | Optimization level | `-O2` |
| `CCL_WASM_DEBUG` | Debug symbols | `-g` |
| `CCL_WASM_CFLAGS` | Additional compiler flags | (empty) |
| `CCL_WASM_LDFLAGS` | Additional linker flags | (empty) |

### Example: Custom Build Directory

```bash
export CCL_WASM_BUILD_DIR=/tmp/my-build
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

### Example: Debug Build

```bash
export CCL_WASM_OPT=-O0
export CCL_WASM_DEBUG=-g3
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

### Example: Custom Toolchain

```bash
export CCL_WASM_CC=/usr/local/bin/clang-19
export CCL_WASM_LD=/usr/local/bin/wasm-ld
export CCL_WASM_SYSROOT=/opt/wasi-sdk/share/wasi-sysroot
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

---

## Testing

After building, run the smoke tests to verify everything works:

```bash
# All smoke tests
node doc/wasm/js/all-smoke.mjs

# Individual tests
node doc/wasm/js/kernel-request-smoke.mjs
node doc/wasm/js/compiler-smoke.mjs
```

**Note:** Test suite is limited. See [README.md](README.md) for current test status.

---

## Cleaning

Remove all build artifacts:

```bash
make -C lisp-kernel/wasm32 clean
rm -rf build/wasm32
```

---

## Troubleshooting

### "Missing Homebrew dependencies" (macOS)

**Problem:** `env.sh` says it can't find llvm/lld/wasi-libc

**Solution:**
```bash
brew install llvm lld wasi-libc
```

### "Could not auto-detect WASM toolchain" (Linux)

**Problem:** `env.sh` can't find clang or wasm-ld

**Solution:** Install via package manager:
```bash
# Ubuntu/Debian
sudo apt install clang-18 lld-18 wasi-libc

# Fedora
sudo dnf install clang lld wasi-libc

# Arch
sudo pacman -S clang lld wasi-libc
```

### "fatal error: 'errno.h' file not found"

**Problem:** Compiler can't find WASI headers

**Solution 1 (Recommended):** Let `env.sh` auto-detect:
```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

**Solution 2:** Set sysroot manually:
```bash
export CCL_WASM_SYSROOT=/path/to/wasi-sysroot
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

**On macOS:** Ensure you're using Homebrew clang, not Apple clang:
```bash
# Wrong (Apple clang, won't work)
which clang
# /usr/bin/clang

# Right (Homebrew clang, works)
/usr/local/opt/llvm/bin/clang --version
```

**On Linux:** Headers should be in `/usr/include/wasm32-wasi` or `/usr/share/wasi-sysroot/include`.

### Build fails with "No rule to make target"

**Problem:** Make can't find source files

**Solution:** Ensure you're in the repository root and running make from there:
```bash
cd /path/to/ccl
make -C lisp-kernel/wasm32
```

### "wasm-ld: error: unknown argument"

**Problem:** Linker doesn't support required flags

**Solution:** Update to a newer version of lld:
```bash
# macOS
brew upgrade lld

# Linux
# Use lld-18 or newer
```

Minimum versions:
- clang: 15+ (18+ recommended)
- lld: 15+ (18+ recommended)

### Build artifacts end up in wrong location

**Problem:** Files in `doc/wasm/js/` instead of `build/wasm32/`

**Cause:** Old build system used `doc/` for artifacts

**Solution:** Set environment variables explicitly:
```bash
export CCL_WASM_BUILD_DIR=$(pwd)/build/wasm32
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

### "Permission denied" when running scripts

**Problem:** Scripts not executable

**Solution:**
```bash
chmod +x scripts/wasm/*.sh
```

---

## Advanced Configuration

### Using a Different Target

The default target is `wasm32-unknown-unknown` (freestanding WASM). To use WASI:

```bash
export CCL_WASM_TARGET=wasm32-wasi
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

**Note:** CCL WASM is designed to work **without** a WASI runtime. The kernel compiles with WASI headers for development convenience but links freestanding. See [decisions.md](decisions.md) ADR-0005.

### Custom Compiler Flags

Add warnings or extra checks:

```bash
export CCL_WASM_CFLAGS="-Wall -Wextra -Werror"
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

### Makefile Help

The Makefile includes built-in help:

```bash
make -C lisp-kernel/wasm32 help
```

---

## Build System Architecture

### Directory Structure

```
ccl/
├── build/                  # Build artifacts (gitignored)
│   └── wasm32/
│       ├── kernel/         # wasmcl.wasm
│       ├── images/         # *.image files
│       ├── modules/        # *.json, *.bin, *.idx
│       └── subprims/       # subprims.wasm
├── lisp-kernel/wasm32/     # C kernel source
│   ├── Makefile            # Kernel build
│   └── config.mk           # Default configuration
├── scripts/wasm/           # Build scripts
│   ├── env.sh              # Environment setup
│   └── rebuild-everything.sh  # Full rebuild orchestrator
└── doc/wasm/               # Documentation only (no artifacts)
```

### How It Works

1. **env.sh** detects your platform and toolchain, exports environment variables
2. **Makefile** reads variables from `config.mk`, builds kernel to `build/wasm32/kernel/`
3. **rebuild-everything.sh** orchestrates full dependency-ordered rebuild
4. All artifacts go to **build/** directory (gitignored)

### Legacy Note

**Old behavior (before 2026-02-15):** Build artifacts were placed in `doc/wasm/js/`

**New behavior:** All artifacts go to `build/wasm32/`

If you have old artifacts, clean them:
```bash
rm -f doc/wasm/js/wasmcl.wasm doc/wasm/js/subprims.wasm
rm -f doc/wasm/*.image doc/wasm/*.json doc/wasm/*.bin doc/wasm/*.idx
```

---

## See Also

- **[README.md](README.md)** - Current implementation status
- **[roadmap.md](roadmap.md)** - Development roadmap
- **[decisions.md](decisions.md)** - Architectural decisions
- **[macos-setup.md](macos-setup.md)** - macOS-specific setup details (if needed)
- **[linux-setup.md](linux-setup.md)** - Linux-specific setup details (if needed)

---

## Getting Help

- **Build problems:** Check this troubleshooting section first
- **Missing features:** See [README.md](README.md) for current status
- **Questions:** Check [project-overview.md](project-overview.md) for architecture

**Note:** This is experimental software under active development. Some features are broken or incomplete. See [README.md](README.md) for what actually works vs what's documented.
