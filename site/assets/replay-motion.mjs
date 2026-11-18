export function unit(value, start = 0, end = 1) {
  return Math.max(0, Math.min(1, (value - start) / (end - start)));
}

function ease(value, start, end) {
  const p = unit(value, start, end);
  return p * p * (3 - 2 * p);
}

const stages = [
  [0, "#trace-2", "case", "Case opened"],
  [.18, "#trace-3", "carrier", "Carrier evidence"],
  [.35, "#trace-4", "replacement", "Receipt returned"],
  [.48, "#trace-4", "moving", "Receipt in transit"],
  [.78, "#trace-5", "closed", "Receipt accepted"],
  [.92, "#trace-5", "verified", "Independent verification passed"],
];

export function storyFrame(value) {
  const progress = unit(value);
  let index = 0;
  while (stages[index + 1]?.[0] <= progress) index += 1;
  const [, hash, phase, label] = stages[index];
  const caseAway = ease(progress, .10, .235);
  const carrierIn = ease(progress, .12, .225);
  const carrierAway = ease(progress, .285, .435);
  const sourceIn = ease(progress, .29, .425);
  const expansion = ease(progress, .35, .465);
  const transfer = unit(progress, .48, .78);
  const accepted = ease(progress, .76, .87);

  return {
    progress, hash, phase, label, caseAway, carrierIn, carrierAway, sourceIn,
    case: (1 - caseAway) ** 2,
    carrier: carrierIn * (1 - carrierAway),
    source: sourceIn * (1 - .72 * ease(progress, .57, .92)),
    destination: ease(progress, .40, .64),
    receipt: progress >= .35,
    tokenSize: .53 + .47 * expansion - .045 * accepted,
    tokenAngle: -9 * (1 - expansion) + 4 * Math.sin(Math.PI * transfer) - 2 * accepted,
    tokenOpacity: ease(progress, .35, .405),
    path: ease(progress, .385, .48),
    transfer,
    accepted,
    note: ease(progress, .48, .54) * (1 - ease(progress, .81, .90)),
    verification: ease(progress, .92, .961),
  };
}

// Seek inside a region so normal subpixel scroll rounding cannot select a neighbour.
export function inspectAt(hash) {
  return ({
    "#trace-1": 0,
    "#trace-2": 0,
    "#trace-3": .24,
    "#trace-4": .44,
    "#trace-5": .85,
    "#trace-6": .98,
    "#trace-7": .98,
  })[hash] ?? 0;
}
