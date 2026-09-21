# Audit 134 clarification

The current retained heap census has **seven**, not eight, entries in the EQUAL
`*combined-methods*` table. The earlier name-based probe reported eight after
adding an entry during observation. The heap snapshot captures before compiling
the attribution/reporting form and records seven. `execution/census.json` and
`execution/dependencies.json` in STAGE1-BOOTSTRAP-HEAP-CENSUS-R1 are correct;
only the “eight-entry” sentence in its pinned README is stale.

The original README remains byte-identical to the reviewed packet so its replay
and source pins remain valid. This clarification is not an evidence rerun and
does not alter any recorded count, acceptance criterion or executable source.

The 22 population objects comprise **21 ordinary weak lists and one empty
terminatable alist**, with 739 members in the ordinary lists. Ordinary strong
retention does not qualify native termination behavior.

The census describes the pinned macOS image. Re-run the census and attribution
against the port's cross-dumped heap before choosing its actual table capacities,
installing roots, or claiming image/bootstrap qualification. Native counts are
neither port measurements nor upper bounds on later growth.

Audit 134 found no defect and closed both audit-133 findings. The proposal remains
unaccepted and unintegrated pending the user's acceptance; LL15 is still open.
