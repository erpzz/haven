export function parse(v) {
  const [core, pre] = v.split('-');
  return { parts: core.split('.'), pre: pre ? pre.split('.') : [] };
}

// -1, 0 or 1. A prerelease sorts before its release; numeric identifiers compare as numbers.
export function compare(a, b) {
  const x = parse(a), y = parse(b);
  for (let i = 0; i < 3; i++) {
    if (x.parts[i] !== y.parts[i]) return x.parts[i] < y.parts[i] ? -1 : 1;
  }
  const n = Math.max(x.pre.length, y.pre.length);
  for (let i = 0; i < n; i++) {
    if (x.pre[i] === undefined) return -1;
    if (y.pre[i] === undefined) return 1;
    if (x.pre[i] !== y.pre[i]) return x.pre[i] < y.pre[i] ? -1 : 1;
  }
  return 0;
}

export const sort = (vs) => [...vs].sort(compare);
