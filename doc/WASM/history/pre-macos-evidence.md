# Historical evidence before the macOS reference decision

These are retained historical reports, not current platform requirements or reverified results. The original files and hashes remain in inputs.json.

| Target | Generated-code baseline | Behavioral baseline |
| --- | --- | --- |
| Historical H1 x86-64 Linux | Reported established (E1, E2): 164 FASLs; 163 identical across two same-host clean rebuilds; bin/compile-ccl.lx64fsl differs, cause uncharacterized. | Reported established: 21,925 ccl-tests passing on the rebuilt Lisp. |
| Historical H1 ARM64 Linux | Reported established by cross-compilation (E5): 126 FASLs, byte-identical across two same-host runs. | Historical native run pending. The previous report identified an H1 ARM64 workflow; verify availability on reproduction. U1 lacks that complete backend. |
| ARM, PPC, x86-32 | Pending the targets' interface databases and the recipe of E5 adapted per target. | Not planned; no hardware or CI identified. |

E4 is conversation-recorded execution evidence, with its archived trace pack pending. Its recorded profile is retained here, not remeasured or independently requalified by this revision. The x86-64 level-1 cold start makes 132 opens, 118 stats, 701 seeks, 6,627 reads, 128 closes, one getcwd and 747 readlinks (746 returning EINVAL: truename walking every path component through lisp_realpath); zero writes, zero directory reads, and no file-backed mmap of Lisp files. Non-FASL files touched are the boot image, /proc/self/exe (from which the kernel derives the ccl: host), /dev/tty, /proc/self/maps and /sys/devices/system/cpu/possible, and the interface database x86-headers64/libc/{records,types}.cdb opened while foreign-types loads. [E4]

[E1] CCL_Gate0_run_2026-09-10.zip Native Gate 0 on x86-64 Linux: commands, kernel/rebuild/test logs, bootstrap tarball digest (v1.13, sha256 dd7dcb16…), rebuilt kernel and image digests, 21,925 tests passing.

[E2] CCL_Gate0_followups_2026-09-10.zip Second clean rebuild: 163/164 FASLs identical, bin/compile-ccl.lx64fsl differing; ordered cold-start FASL list (122 files: 41 l1-fasls, 77 bin, 4 library) from strace -e openat.

[E4] Native cold-start syscall profile, 10 September 2026 strace -c and -e trace=openat,mmap,readlink over the x86-boot64 level-1 cold start: 132 openat, 118 newfstatat, 701 lseek, 6,627 read, 128 close, 747 readlink (746 EINVAL), 1 getcwd; no writes, no directory reads, no file-backed mmap of Lisp files; non-FASL files as listed in 05. Evidence status: conversation-recorded execution results; archived trace pack pending. Retain the exact commands, environment, raw traces and digests on recapture. These counts are not an archived-trace or requalified-runtime claim.

[E5] CCL_R6_arm64_cross_baseline_2026-09-10.zip cross-compile-linuxarm64.lisp (working module order and explicit setup-arm64-ftd), run log, and sha256 digests of all 126 .la64fsl files; two consecutive runs byte-identical. Requires arm64-headers from the v1.13-arm64-pre2 release tarball.


Generate U1 cross-target baselines with recipes validated against U1 and obtain native behavior separately where hardware or CI exists. The following ARM64 recipe belongs exclusively to historical H1/E5, whose complete backend is absent from U1; do not execute it as a U1 recipe. Historical recipe: load arm64-arch, arm64-asm, arm64env and arm64-lap in that order (the listed module order fails on a foreign host because arm64env uses register aliases arm64-asm defines), then the FFI environment modules, then the backend modules, then call setup-arm64-ftd explicitly, with the target's interface database extracted from its release tarball. The prior report identified a GitHub-hosted ubuntu-24.04-arm workflow for H1; current availability and evidence must be checked when reproducing it. ARM, PPC and x86-32 baselines are pending their interface databases. [E5]
