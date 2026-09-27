// All eight package fields must retain their sole referents across movement.
setup(1024);
const packageCells = Array.from({length: 8}, (_, i) => cons((i + 101) * 4));
const packageObject = node(98, packageCells);
put(EXTERNAL, packageObject);
for (let iteration = 0; iteration < 2; iteration++) {
  const before = get(EXTERNAL), from = t(56), end = t(52);
  collect(); poison(from, end);
  const moved = get(EXTERNAL);
  assert.notEqual(moved, before);
  assert.equal(get(moved - 6), 8 * 256 + 98);
  packageCells.forEach((_, i) => assert.equal(get(get(moved - 2 + 4 * i) + 3), (i + 101) * 4));
}
pass('package-eight-fields-move');
for (const count of [0, 7, 9]) {
  setup(); const packageObject = node(98, Array(count).fill(N));
  put(EXTERNAL, packageObject);
  refused('package-wrong-count-' + count, collect, 'collection refused 2');
}
setup();
const truncatedPackage = node(98, Array(8).fill(N));
put(EXTERNAL, truncatedPackage); set(48, t(48) - 8);
refused('package-truncated', collect, 'collection refused 2');
