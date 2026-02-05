export function createIdGenerator(prefix = "id") {
  let counter = 0;
  return function nextId() {
    const id = `${prefix}-${counter}`;
    counter += 1;
    return id;
  };
}
