import assert from "node:assert/strict";
import test from "node:test";
import { inspectAt, storyFrame } from "../site/assets/replay-motion.mjs";

test("stage thresholds select the archived records and clamp at both ends", () => {
  for (const [progress, phase, hash] of [
    [-.1, "case", "#trace-2"],
    [.1799, "case", "#trace-2"],
    [.18, "carrier", "#trace-3"],
    [.35, "replacement", "#trace-4"],
    [.48, "moving", "#trace-4"],
    [.78, "closed", "#trace-5"],
    [.92, "verified", "#trace-5"],
    [1.1, "verified", "#trace-5"],
  ]) {
    assert.equal(storyFrame(progress).phase, phase);
    assert.equal(storyFrame(progress).hash, hash);
  }
  assert.equal(storyFrame(-.1).progress, 0);
  assert.equal(storyFrame(1.1).progress, 1);
  assert.equal(storyFrame(.919).verification, 0);
  assert.equal(storyFrame(.98).verification, 1);
});

test("the receipt follows a continuous path and reverse passes reproduce every state", () => {
  const checkpoints = [0, .20, .40, .48, .50, .60, .70, .78, .80, .95, 1];
  const forward = checkpoints.map(storyFrame);
  for (let round = 0; round < 2; round += 1) {
    assert.deepEqual([...checkpoints].reverse().map(storyFrame), [...forward].reverse());
    assert.deepEqual(checkpoints.map(storyFrame), forward);
  }
  assert.equal(storyFrame(.3499).receipt, false);
  assert.equal(storyFrame(.35).receipt, true);
  assert.equal(storyFrame(.48).transfer, 0);
  assert.equal(storyFrame(.78).transfer, 1);
  assert(Math.abs(storyFrame(.63).transfer - .5) < 1e-10);
  assert(storyFrame(.50).transfer < storyFrame(.60).transfer);
  assert(storyFrame(.60).transfer < storyFrame(.70).transfer);
});

test("evidence documents trade emphasis and the receipt expands before it travels", () => {
  assert(storyFrame(.05).case > storyFrame(.20).case);
  assert(storyFrame(.25).carrier > storyFrame(.38).carrier);
  assert(storyFrame(.37).tokenSize < storyFrame(.46).tokenSize);
  assert(storyFrame(.54).source > storyFrame(.77).source);
  assert(storyFrame(.54).destination < storyFrame(.77).destination);
  assert(storyFrame(.77).accepted < storyFrame(.86).accepted);
  assert.equal(storyFrame(.88).verification, 0);
});

test("manual links seek inside their action region and reach the verified record", () => {
  for (const hash of ["#trace-2", "#trace-3", "#trace-4", "#trace-5"]) {
    assert.equal(storyFrame(inspectAt(hash)).hash, hash);
  }
  assert.equal(storyFrame(inspectAt("#trace-6")).verification, 1);
  assert.equal(storyFrame(inspectAt("#trace-7")).verification, 1);
});
