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
- the palette is the original's — near-white text, a muted grey for values
  and provenance, a dimmer grey for labels — with only the dimmest tier
  lifted from `#747783` to `#7f828d` to clear the §29 floor; the warm row
  tints are the original's exactly, and each means one thing (§28): chosen,
  pointed at, in progress, the current menu item;
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
| 1 | [At rest](01-at-rest.png) | G1–G5 | `3fb37b5227d37792` |
| 2 | [Type-directed narrowing](02-type-directed-narrowing.png) | G6, G8 | `2e3064cc971540f2` |
| 3 | [Verbs from nouns](03-verbs-from-nouns.png) | G7 | `d40f4416007b46e5` |
| 4 | [Files as objects](04-files-as-objects.png) | G9, G10, G10.1 | `d67158d00ec5cb83` |
| 5 | [The shelf](05-the-shelf.png) | G9.1, G9.2, G11, G12 | `427808082085d147` |
| 6 | [Break, fix, resume](06-break-fix-resume.png) | G13–G15 | `57f93ad6c96d0150` |
| 7 | [The image explains itself](07-the-image-explains-itself.png) | G16–G18 | `94e823d6bf7e593a` |
| 8 | [Named layouts](08-named-layouts.png) | G19 | `7d701785b140db2e` |
| 9 | [Tear off to the host](09-tear-off-to-the-host.png) | G20 | `20db9e54b7ce3fda` |
| 10 | [Compare without windows](10-compare-without-windows.png) | G21 | `41a21e834f8a2698` |
| 11 | [Views live inline](11-views-live-inline.png) | G9.1, G22 | `9fd0f67aaf66524f` |
| 12 | [Settings with provenance](12-settings-with-provenance.png) | G24–G27 | `d413992081bb4522` |
| 13 | [Divergence as a break](13-divergence-as-a-break.png) | G10.4 | `49f48e889801161f` |
| 14 | [Systems, not directories](14-systems-not-directories.png) | G30–G32 | `943c80d8eb59a901` |
| 15 | [The definition and its plan](15-the-definition-and-its-plan.png) | G33 | `204a2fb20d2387f8` |
| 16 | [Foreign material](16-foreign-material.png) | G34–G37 | `146211d0cb1ac480` |
| 17 | [Interrupting a computation](17-interrupting-a-computation.png) | G38–G41 | `be46e67a50230804` |
| 18 | [Activities](18-activities.png) | G42–G44 | `e9c98de270767350` |
| 19 | [Warnings as presentations](19-warnings-as-presentations.png) | G48, G49 | `ad10dfc9da66202f` |
| 20 | [The inspector keeps a trail](20-the-inspector-keeps-a-trail.png) | G56 | `3e0a185cef116ad1` |
| 21 | [A dialog from the argument types](21-a-dialog-from-the-argument-types.png) | G25, G54, G55 | `5623fef7c69767ea` |
| 22 | [The image, and its snapshots](22-the-image-and-its-snapshots.png) | G50–G52, G78 | `7f23b399f3a7a5ad` |
| 23 | [Undo, honestly](23-undo-honestly.png) | G57, G58 | `d327db2426cb4e2c` |
