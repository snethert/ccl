# IDE reference screens

The twenty-three reference screens for [ui-overview.md](../ui-overview.md),
numbered as in its §32. This is the second set: the first, delivered as page
images in `CLIM_IDE_Screen_4.pdf`, was replaced after the document's second
revision applied Codex's review and the modal-editing decision (§20). The
original images remain in git history at d51d6d35.

**The screens are source now.** Each one is a section of
[src/screens.html](src/screens.html), styled by [src/screens.css](src/screens.css),
which holds the design tokens and the shared components (pane header, command
line, documentation line, overlays, code, rows). Open `screens.html` in a
browser to see all twenty-three with captions, or append `?screen=N` for one
frame at exactly 1440 × 900. [src/render.sh](src/render.sh) renders the PNGs
with headless Chrome at 3× (4320 × 2700); the IBM Plex faces are vendored
under `src/fonts/` so the render needs no network.

What changed from the first set, all from §33 of the document:

- every ⌘-chord is a leader sequence (`SPC …`), and editable panes show the
  editor's mode beside the buffer state;
- screen 1's documentation line reads the caret's form in normal mode, and a
  plain click in insert mode places the caret (G5);
- screen 3's commands carry their declared explanation, key and consequence
  (G7); screen 7 says *known callers* with the source of each (G16);
- the ring is the shelf (screen 5); screen 11 shows an expired presentation
  (G9.1);
- screen 6 lists only restarts the program established, and its fixture
  establishes them; screen 13 states image facts as facts of this image;
- screens 12 and 21 put typed entry before the slider (G25);
- screens 17 and 22 say *restore*, not *resume*, and screen 22 shows pinned
  objects and the age of the last checkpoint (G51, G78);
- the recessed grey is `#8e939d`, which clears the §29 contrast floor on
  every ground it is used on;
- the fixture tells one story: one set of commit identities, and the scan
  limit lives in the project settings file on every screen.

The screens are worked examples, not evidence. They are dark-theme only; the
light variant is registered as undecided in §27.

| # | Screen | Goals it illustrates | sha256 (first 16) |
| --- | --- | --- | --- |
| 1 | [At rest](01-at-rest.png) | G1–G5 | `0ab1371a1017d233` |
| 2 | [Type-directed narrowing](02-type-directed-narrowing.png) | G6, G8 | `d31041d7f0f9d341` |
| 3 | [Verbs from nouns](03-verbs-from-nouns.png) | G7 | `b0211bae6a6b347c` |
| 4 | [Files as objects](04-files-as-objects.png) | G9, G10, G10.1 | `f39a50127208ed1a` |
| 5 | [The shelf](05-the-shelf.png) | G9.1, G9.2, G11, G12 | `da3a4109fef7081d` |
| 6 | [Break, fix, resume](06-break-fix-resume.png) | G13–G15 | `4dc19352ec8c44f5` |
| 7 | [The image explains itself](07-the-image-explains-itself.png) | G16–G18 | `b2ab8a9e4917e4b8` |
| 8 | [Named layouts](08-named-layouts.png) | G19 | `a4c0b684b8a1a240` |
| 9 | [Tear off to the host](09-tear-off-to-the-host.png) | G20 | `7165b106a3ca9b97` |
| 10 | [Compare without windows](10-compare-without-windows.png) | G21 | `44c300c88a96b2d9` |
| 11 | [Views live inline](11-views-live-inline.png) | G9.1, G22 | `7e891db327faf952` |
| 12 | [Settings with provenance](12-settings-with-provenance.png) | G24–G27 | `75e497e2c4bf3c11` |
| 13 | [Divergence as a break](13-divergence-as-a-break.png) | G10.4 | `d950108eb95607e7` |
| 14 | [Systems, not directories](14-systems-not-directories.png) | G30–G32 | `dcc10f396d4b1fed` |
| 15 | [The definition and its plan](15-the-definition-and-its-plan.png) | G33 | `1fe968f6190b5bf1` |
| 16 | [Foreign material](16-foreign-material.png) | G34–G37 | `fe34438e349c2ebe` |
| 17 | [Interrupting a computation](17-interrupting-a-computation.png) | G38–G41 | `d1a4ae6d82e6d404` |
| 18 | [Activities](18-activities.png) | G42–G44 | `2c02b11183d93be2` |
| 19 | [Warnings as presentations](19-warnings-as-presentations.png) | G48, G49 | `c033830ef1bcc661` |
| 20 | [The inspector keeps a trail](20-the-inspector-keeps-a-trail.png) | G56 | `120fe8660fcb3198` |
| 21 | [A dialog from the argument types](21-a-dialog-from-the-argument-types.png) | G25, G54, G55 | `6eee6e888db1d348` |
| 22 | [The image, and its snapshots](22-the-image-and-its-snapshots.png) | G50–G52, G78 | `0ae118d352c79fb8` |
| 23 | [Undo, honestly](23-undo-honestly.png) | G57, G58 | `36fd985b4e632daa` |
