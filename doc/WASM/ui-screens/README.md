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

The source meets §29's semantics rule: the discovery words are links, the
action chips and every selectable row are buttons, fields are inputs with
labels, the checkbox and the slider are inputs, and rows that hold a control
are groups. The renders are unchanged by it; the keyboard and a screen
reader are not.

The screens are worked examples, not evidence. They are dark-theme only; the
light variant is registered as undecided in §27.

| # | Screen | Goals it illustrates | sha256 (first 16) |
| --- | --- | --- | --- |
| 1 | [At rest](01-at-rest.png) | G1–G5 | `51833e2b22f25ba2` |
| 2 | [Type-directed narrowing](02-type-directed-narrowing.png) | G6, G8 | `358706c4d809e118` |
| 3 | [Verbs from nouns](03-verbs-from-nouns.png) | G7 | `0472c63fc4113c75` |
| 4 | [Files as objects](04-files-as-objects.png) | G9, G10, G10.1 | `f39a50127208ed1a` |
| 5 | [The shelf](05-the-shelf.png) | G9.1, G9.2, G11, G12 | `da3a4109fef7081d` |
| 6 | [Break, fix, resume](06-break-fix-resume.png) | G13–G15 | `6ad1e04c2c90049e` |
| 7 | [The image explains itself](07-the-image-explains-itself.png) | G16–G18 | `b2ab8a9e4917e4b8` |
| 8 | [Named layouts](08-named-layouts.png) | G19 | `b4021f539b4f9135` |
| 9 | [Tear off to the host](09-tear-off-to-the-host.png) | G20 | `7165b106a3ca9b97` |
| 10 | [Compare without windows](10-compare-without-windows.png) | G21 | `44c300c88a96b2d9` |
| 11 | [Views live inline](11-views-live-inline.png) | G9.1, G22 | `8c188d5f78e76eda` |
| 12 | [Settings with provenance](12-settings-with-provenance.png) | G24–G27 | `89b90d0e22240ba5` |
| 13 | [Divergence as a break](13-divergence-as-a-break.png) | G10.4 | `c86aa2ec8dd317b2` |
| 14 | [Systems, not directories](14-systems-not-directories.png) | G30–G32 | `69b498f2cddf7a4c` |
| 15 | [The definition and its plan](15-the-definition-and-its-plan.png) | G33 | `1fe968f6190b5bf1` |
| 16 | [Foreign material](16-foreign-material.png) | G34–G37 | `cdd652f42da8293d` |
| 17 | [Interrupting a computation](17-interrupting-a-computation.png) | G38–G41 | `d6ec013dbead35f4` |
| 18 | [Activities](18-activities.png) | G42–G44 | `2c02b11183d93be2` |
| 19 | [Warnings as presentations](19-warnings-as-presentations.png) | G48, G49 | `170b7919c2e00867` |
| 20 | [The inspector keeps a trail](20-the-inspector-keeps-a-trail.png) | G56 | `120fe8660fcb3198` |
| 21 | [A dialog from the argument types](21-a-dialog-from-the-argument-types.png) | G25, G54, G55 | `b58e171b52b98a60` |
| 22 | [The image, and its snapshots](22-the-image-and-its-snapshots.png) | G50–G52, G78 | `583d06ef22a63f84` |
| 23 | [Undo, honestly](23-undo-honestly.png) | G57, G58 | `051fd0c1c6390dd8` |
