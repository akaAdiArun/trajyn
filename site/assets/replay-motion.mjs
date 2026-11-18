export function unit(value, start = 0, end = 1) {
  return Math.max(0, Math.min(1, (value - start) / (end - start)));
}

const stages = [
  [0, "#trace-2", "case", 0, .25, 0],
  [.15, "#trace-3", "carrier", .25, .50, .15],
  [.32, "#trace-4", "replacement", .50, .59, .32],
  [.49, "#trace-4", "moving", .59, 1, .32],
  [.80, "#trace-5", "closed", 1, 1, .80],
  [.94, "#trace-5", "verified", 1, 1, .80],
];

export function storyFrame(value) {
  const progress = unit(value);
  let index = 0;
  while (stages[index + 1]?.[0] <= progress) index += 1;
  const [start, hash, phase, routeFrom, routeTo, evidenceStart] = stages[index];
  const fraction = unit(progress, start, stages[index + 1]?.[0] ?? 1);
  return {
    progress,
    hash,
    phase,
    route: routeFrom + fraction * (routeTo - routeFrom),
    receipt: progress >= .32,
    transfer: unit(progress, .49, .80),
    evidence: unit(progress, evidenceStart, evidenceStart + .06),
    verification: unit(progress, .94, .97),
  };
}

// Seek inside a region so normal subpixel scroll rounding cannot select a neighbour.
export function inspectAt(hash) {
  return {
    "#trace-1": 0,
    "#trace-2": 0,
    "#trace-3": .21,
    "#trace-4": .38,
    "#trace-5": .86,
    "#trace-6": .98,
    "#trace-7": .98,
  }[hash] ?? 0;
}
