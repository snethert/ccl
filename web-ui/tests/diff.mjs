export function diffSnapshots(a, b) {
  if (a === b) return null;
  const linesA = a.split("\n");
  const linesB = b.split("\n");
  const max = Math.max(linesA.length, linesB.length);
  for (let i = 0; i < max; i += 1) {
    const left = linesA[i];
    const right = linesB[i];
    if (left !== right) {
      return { line: i + 1, left, right };
    }
  }
  return { line: 1, left: linesA[0], right: linesB[0] };
}

export function formatDiff(diff) {
  if (!diff) return "";
  return [
    `Difference at line ${diff.line}:`,
    `- ${diff.left ?? ""}`,
    `+ ${diff.right ?? ""}`
  ].join("\n");
}
