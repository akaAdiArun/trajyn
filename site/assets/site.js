import { inspectAt, storyFrame, unit } from "./replay-motion.mjs";

const root = document.documentElement;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const hero = document.querySelector("[data-scroll-hero]");
const headings = [...document.querySelectorAll("[data-motion-heading]")];
const fork = document.querySelector("[data-motion-fork]");
const marks = document.querySelector("[data-motion-marks]");
const architecture = document.querySelector("[data-motion-rule]");
const track = document.querySelector("[data-story-track]");
const sticky = track.querySelector(".story-sticky");
const replay = track.querySelector("[data-replay]");
const pane = replay.querySelector(".replay-pane");
const scene = replay.querySelector(".evidence-scene");
const paths = [...scene.querySelectorAll(".evidence-path")].map(svg => {
  const connector = svg.querySelector("[data-receipt-path]");
  return {svg, connector, length: connector.getTotalLength()};
});
const phaseLabel = scene.querySelector("[data-scene-phase]");
const phaseStatus = replay.querySelector("[data-accessible-phase]");
const links = [...replay.querySelectorAll("nav a")];
const panels = new Map([...pane.querySelectorAll("[data-evidence]")]
  .map(panel => ["#" + panel.id, panel]));
const controls = replay.querySelector(".replay-controls");
const play = controls.querySelector("[data-play-toggle]");
const restart = controls.querySelector("[data-restart]");
const recordsButton = controls.querySelector("[data-inspect]");
const introRestart = hero.querySelector("[data-intro-restart]");
const meter = controls.querySelector("progress");
const result = replay.querySelector(".replay-result p");
const token = replay.querySelector(".receipt-token");
const duration = 14500;
const first = "#trace-2";

let playing = null;
let reading = null;
let active;
let lastPaint;
let motion = false;
let requestedHash;
let geometry;
let dirty = true;
let frame = 0;

function value(element, name, amount, suffix = "") {
  const cssValue = amount.toFixed(4) + suffix;
  if (element.style.getPropertyValue(name) !== cssValue) {
    element.style.setProperty(name, cssValue);
  }
}

function show(hash) {
  if (active === hash) return;
  active = hash;
  for (const [id, panel] of panels) panel.hidden = id !== hash;
  for (const link of links) {
    if (link.hash === hash) link.setAttribute("aria-current", link.closest("ol") ? "step" : "true");
    else link.removeAttribute("aria-current");
  }
  pane.scrollTop = 0;
}

function render(progress, record) {
  const state = storyFrame(progress);
  const hash = record ?? state.hash;
  if (lastPaint?.progress === progress && lastPaint.hash === hash) return;
  lastPaint = {progress, hash};
  show(hash);
  if (replay.dataset.phase !== state.phase) {
    replay.dataset.phase = state.phase;
    phaseLabel.textContent = state.label;
    phaseStatus.textContent = state.label;
  }
  meter.value = state.progress;
  result.hidden = state.phase !== "verified";
  token.hidden = !state.receipt;
  const effects = {
    "--case": state.case,
    "--case-away": state.caseAway,
    "--carrier": state.carrier,
    "--carrier-in": state.carrierIn,
    "--carrier-away": state.carrierAway,
    "--source": state.source,
    "--source-in": state.sourceIn,
    "--destination": state.destination,
    "--input": state.accepted,
    "--path": state.path,
    "--transfer": state.transfer,
    "--note": state.note,
    "--verified": state.verification,
  };
  for (const [key, amount] of Object.entries(effects)) value(scene, key, amount);
  if (state.receipt) {
    const {connector, length} = geometry.path;
    const point = connector.getPointAtLength(length * state.transfer);
    value(token, "--token-x", point.x * geometry.scaleX, "px");
    value(token, "--token-y", point.y * geometry.scaleY, "px");
    value(token, "--token-angle", state.tokenAngle, "deg");
    value(token, "--token-size", state.tokenSize);
    value(token, "--token-opacity", state.tokenOpacity);
  }
}

function measure() {
  // Layout reads happen only after a resize, a disclosure, or a mode change.
  const y = scrollY;
  const viewport = innerHeight;
  const bounds = track.getBoundingClientRect();
  const heroBounds = hero.getBoundingClientRect();
  function entry(element, from, to) {
    const top = element.getBoundingClientRect().top + y;
    return [top - viewport * from, top - viewport * to];
  }
  const path = paths.find(({svg}) => svg.clientWidth > 0);
  const {width, height} = path.svg.viewBox.baseVal;
  const view = path.svg.getBoundingClientRect();
  geometry = {
    story: bounds.top + y - parseFloat(getComputedStyle(sticky).top),
    distance: Math.max(1, bounds.height - sticky.offsetHeight),
    path,
    scaleX: view.width / width,
    scaleY: view.height / height,
    hero: [heroBounds.top + y, heroBounds.top + y + heroBounds.height * .70],
    headings: headings.map(heading => entry(heading, .96, .58)),
    fork: entry(fork, .98, .57),
    marks: entry(marks, 1, .51),
    architecture: entry(architecture, .96, .53),
  };
  lastPaint = undefined;
  dirty = false;
}

function renderSurroundings(y) {
  const exit = unit(y, ...geometry.hero);
  value(hero, "--hero-exit", exit);
  value(hero, "--hero-rewind", exit * .38);
  headings.forEach((heading, index) => {
    const entry = unit(y, ...geometry.headings[index]);
    value(heading, "--heading", entry);
    value(heading, "--explanation", unit(entry, .22, 1));
  });
  const split = unit(y, ...geometry.fork);
  value(fork, "--fork-stem", unit(split, 0, .26));
  value(fork, "--fork", unit(split, .18, 1));
  const emphasis = unit(y, ...geometry.marks);
  value(marks, "--baseline-marks", unit(emphasis, 0, .64));
  value(marks, "--procedure-marks", unit(emphasis, .34, 1));
  value(architecture, "--architecture", unit(y, ...geometry.architecture));
}

function currentProgress() {
  return unit(scrollY, geometry.story, geometry.story + geometry.distance);
}

function seek(progress) {
  window.scrollTo({top: geometry.story + geometry.distance * progress, behavior: "instant"});
  return scrollY;
}

function refresh() {
  dirty = true;
  schedule();
}

function stop() {
  if (playing) play.textContent = "Play";
  playing = null;
}

function clearReading() {
  reading = null;
  showRecords(false);
}

function showRecords(open) {
  replay.toggleAttribute("data-inspecting", motion && open);
  recordsButton.setAttribute("aria-expanded", String(motion && open));
  recordsButton.textContent = motion && open ? "Return to scene" : "Inspect record";
  pane.hidden = motion && !open;
}

function closeRecords() {
  replay.querySelectorAll(".recorded[open]").forEach(details => { details.open = false; });
}

function inspect(hash, open = false) {
  stop();
  const panel = panels.get(hash);
  showRecords(open || !panel.hasAttribute("data-action"));
  if (!motion) {
    show(hash);
    return;
  }
  if (dirty) measure();
  const progress = inspectAt(hash);
  reading = {hash, progress, position: scrollY};
  render(progress, hash);
  measure();
  reading.position = seek(progress);
}

function update(now) {
  frame = 0;
  if (!motion) return;
  if (dirty) measure();
  if (requestedHash !== undefined) {
    const hash = requestedHash;
    requestedHash = undefined;
    if (panels.has(hash)) inspect(hash, true);
    else clearReading();
  }

  if (playing) {
    const progress = unit(playing.from + Math.max(0, now - playing.start) / duration);
    playing.position = seek(progress);
    if (progress === 1) stop();
  }
  renderSurroundings(scrollY);
  render(reading?.progress ?? currentProgress(), reading?.hash);
  if (playing) schedule();
}

function schedule() {
  if (motion && !frame) frame = requestAnimationFrame(update);
}

function playFrom(rewind = false) {
  if (!motion || document.hidden) return;
  if (dirty) measure();
  const position = reading?.progress ?? currentProgress();
  stop();
  clearReading();
  closeRecords();
  measure();
  const from = rewind || position >= .999 ? 0 : position;
  playing = {from, start: performance.now(), position: seek(from)};
  play.textContent = "Pause";
  schedule();
}

function holdRecord() {
  stop();
  if (motion && dirty) measure();
  if (motion) reading = {hash: active, progress: reading?.progress ?? currentProgress(), position: scrollY};
  showRecords(true);
  refresh();
}

for (const link of links) {
  link.addEventListener("click", event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (location.hash !== link.hash) history.pushState(null, "", link.hash);
    inspect(link.hash);
    schedule();
  });
}

play.addEventListener("click", () => playing ? stop() : playFrom());
restart.addEventListener("click", () => playFrom(true));
recordsButton.addEventListener("click", () => {
  if (pane.hidden) holdRecord();
  else {
    clearReading();
    closeRecords();
    refresh();
  }
});
introRestart.addEventListener("click", () => {
  root.classList.remove("hero-entering");
  window.scrollTo({top: 0, behavior: "instant"});
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (motion) root.classList.add("hero-entering");
  }));
});
replay.addEventListener("toggle", event => {
  if (!event.target.matches(".recorded")) return;
  if (event.target.open) holdRecord();
  else refresh();
}, true);
// A disclosure takes control before the native toggle event is delivered.
replay.addEventListener("click", event => {
  const summary = event.target.closest(".recorded summary");
  if (summary && !summary.parentElement.open) holdRecord();
});

function restore() {
  stop();
  if (motion) {
    requestedHash = location.hash;
    schedule();
  } else {
    inspect(panels.has(location.hash) ? location.hash : first);
  }
}
addEventListener("hashchange", restore);
addEventListener("popstate", restore);
addEventListener("scroll", () => {
  if (playing && Math.abs(scrollY - playing.position) > 2) stop();
  if (reading && Math.abs(scrollY - reading.position) > 2) {
    clearReading();
    closeRecords();
  }
  schedule();
}, {passive: true});
addEventListener("wheel", stop, {passive: true});
addEventListener("touchmove", stop, {passive: true});
addEventListener("blur", stop);
addEventListener("keydown", event => {
  if (event.key === " " && event.target.closest("button, summary, a, input, select, textarea")) return;
  if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) stop();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stop();
  else refresh();
});
addEventListener("resize", refresh);
if (typeof ResizeObserver === "function") {
  const observer = new ResizeObserver(refresh);
  observer.observe(document.body);
  observer.observe(sticky);
}

function configure() {
  stop();
  clearReading();
  motion = !reduced.matches && CSS.supports("position", "sticky");
  root.toggleAttribute("data-scroll-story", motion);
  controls.hidden = !motion;
  introRestart.hidden = !motion;
  scene.hidden = !motion;
  showRecords(false);
  if (motion) {
    refresh();
    restore();
  } else {
    root.classList.remove("hero-entering");
    delete replay.dataset.phase;
    token.hidden = true;
    result.hidden = false;
    restore();
  }
}

show(first);
if (!reduced.matches && !location.hash && scrollY < 40) root.classList.add("hero-entering");
reduced.addEventListener("change", configure);
configure();
