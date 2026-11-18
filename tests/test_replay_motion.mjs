import assert from "node:assert/strict";
import test from "node:test";
import { inspectAt, storyFrame } from "../site/assets/replay-motion.mjs";

test("recorded cues use the published scroll ranges and clamp at both ends", () => {
  for (const [progress, phase, hash] of [
    [-.1, "case", "#trace-2"],
    [.1499, "case", "#trace-2"],
    [.15, "carrier", "#trace-3"],
    [.32, "replacement", "#trace-4"],
    [.49, "moving", "#trace-4"],
    [.80, "closed", "#trace-5"],
    [.94, "verified", "#trace-5"],
    [1.1, "verified", "#trace-5"],
  ]) {
    assert.equal(storyFrame(progress).phase, phase);
    assert.equal(storyFrame(progress).hash, hash);
  }
  assert.equal(storyFrame(-.1).progress, 0);
  assert.equal(storyFrame(1.1).progress, 1);
  assert.equal(storyFrame(.939).verification, 0);
  assert.equal(storyFrame(.98).verification, 1);
});

test("handoff is continuous, reversible and independent of earlier samples", () => {
  const checkpoints = [0, .15, .32, .49, .52, .61, .75, .80, .94, 1];
  const forward = checkpoints.map(storyFrame);
  for (let round = 0; round < 2; round += 1) {
    assert.deepEqual([...checkpoints].reverse().map(storyFrame), [...forward].reverse());
    assert.deepEqual(checkpoints.map(storyFrame), forward);
  }
  assert.equal(storyFrame(.3199).receipt, false);
  assert.equal(storyFrame(.32).receipt, true);
  assert.equal(storyFrame(.49).transfer, 0);
  assert.equal(storyFrame(.80).transfer, 1);
  assert(storyFrame(.52).transfer < storyFrame(.61).transfer);
  assert(storyFrame(.61).transfer < storyFrame(.75).transfer);
  for (const boundary of [.15, .32, .49, .80, .94]) {
    assert(Math.abs(storyFrame(boundary).route - storyFrame(boundary - .000001).route) < .00001);
  }
});

test("manual action links seek inside their regions and archive links reach verification", () => {
  for (const hash of ["#trace-2", "#trace-3", "#trace-4", "#trace-5"]) {
    assert.equal(storyFrame(inspectAt(hash)).hash, hash);
  }
  assert.equal(storyFrame(inspectAt("#trace-6")).verification, 1);
  assert.equal(storyFrame(inspectAt("#trace-7")).verification, 1);
});
