const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const canObserve = typeof IntersectionObserver === "function";

if (canObserve && !reducedMotion.matches) {
  const reveals = new IntersectionObserver((entries, observer) => {
    for (const entry of entries) {
      if (entry.intersectionRatio < 0.15) continue;
      entry.target.parentElement.classList.add("chapter-entering");
      observer.unobserve(entry.target);
    }
  }, {threshold: 0.15});
  document.querySelectorAll("[data-chapter-reveal] h2").forEach(heading => reveals.observe(heading));
}

const replay = document.querySelector("[data-replay]");
if (replay) {
  const chapter = document.getElementById("replay");
  const links = [...replay.querySelectorAll("nav a")];
  const panels = new Map([...replay.querySelectorAll("[data-evidence]")]
    .map(panel => ["#" + panel.id, panel]));
  const pane = replay.querySelector(".replay-pane");
  const controls = replay.querySelector(".replay-controls");
  const play = controls.querySelector("[data-play-toggle]");
  const restart = controls.querySelector("[data-restart]");
  const result = replay.querySelector(".replay-result p");
  const token = replay.querySelector(".receipt-token");
  const svg = replay.querySelector(".receipt-track svg");
  const connector = svg.querySelector("path");
  const length = connector.getTotalLength();
  const {width, height} = svg.viewBox.baseVal;
  const cues = [
    {at: 0, hash: "#trace-2", phase: "case"},
    {at: 1400, hash: "#trace-3", phase: "carrier"},
    {at: 2800, hash: "#trace-4", phase: "replacement"},
    {at: 4200, hash: "#trace-4", phase: "moving"},
    {at: 5000, hash: "#trace-5", phase: "closed"},
    {at: 6300, hash: "#trace-5", phase: "verified"},
  ];
  const duration = 7000;

  let active;
  let elapsed = 0;
  let startedAt = null;
  let frame;
  let autoplay;
  let inView = false;

  function show(hash) {
    if (active === hash) return;
    active = hash;
    for (const [id, panel] of panels) panel.hidden = id !== hash;
    for (const link of links) {
      if (link.hash === hash) {
        link.setAttribute("aria-current", link.closest("ol") ? "step" : "true");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  function render(time) {
    const cue = cues.findLast(item => item.at <= time);
    show(cue.hash);
    const changed = replay.dataset.phase !== cue.phase;
    if (changed) {
      replay.dataset.phase = cue.phase;
      result.hidden = cue.phase !== "verified";
      token.hidden = time < cues[2].at;
    }
    if (!token.hidden && (changed || cue.phase === "moving")) {
      const departure = cues[3].at;
      const arrival = cues[4].at;
      const progress = Math.min(1, Math.max(0, (time - departure) / (arrival - departure)));
      const point = connector.getPointAtLength(length * progress);
      token.style.left = (100 * point.x / width) + "%";
      token.style.top = (100 * point.y / height) + "%";
    }
  }

  function buttons() {
    const playing = startedAt !== null;
    play.textContent = playing ? "Pause" : "Play";
    play.disabled = !playing && elapsed === duration;
  }

  function stopAuto() {
    autoplay?.disconnect();
    autoplay = undefined;
  }

  function tick(now) {
    const time = Math.min(duration, Math.max(0, elapsed + now - startedAt));
    render(time);
    if (time < duration) {
      frame = requestAnimationFrame(tick);
    } else {
      elapsed = duration;
      startedAt = null;
      buttons();
    }
  }

  function start() {
    if (startedAt !== null || document.hidden || elapsed === duration) return;
    stopAuto();
    startedAt = performance.now();
    render(elapsed);
    buttons();
    frame = requestAnimationFrame(tick);
  }

  function pause() {
    if (startedAt === null) return;
    elapsed = Math.min(duration, elapsed + performance.now() - startedAt);
    startedAt = null;
    cancelAnimationFrame(frame);
    render(elapsed);
    buttons();
  }

  function inspect(hash) {
    stopAuto();
    pause();
    elapsed = cues.find(item => item.hash === hash)?.at ?? 0;
    delete replay.dataset.phase;
    result.hidden = false;
    token.hidden = true;
    show(hash);
    buttons();
  }

  for (const link of links) {
    link.addEventListener("click", event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        return;
      }
      event.preventDefault();
      if (location.hash !== link.hash) history.pushState(null, "", link.hash);
      inspect(link.hash);
    });
  }

  play.addEventListener("click", () => {
    if (startedAt !== null) pause();
    else start();
  });
  restart.addEventListener("click", () => {
    pause();
    replay.querySelectorAll(".recorded[open]").forEach(details => { details.open = false; });
    elapsed = 0;
    start();
  });

  // Pause before a keyboard or pointer disclosure opens, and handle direct DOM changes too.
  replay.addEventListener("click", event => {
    const summary = event.target.closest(".recorded summary");
    if (summary && !summary.parentElement.open) {
      stopAuto();
      pause();
    }
  });
  replay.addEventListener("toggle", event => {
    if (event.target.matches(".recorded[open]")) {
      stopAuto();
      pause();
    }
  }, true);

  function restore() {
    if (panels.has(location.hash)) inspect(location.hash);
    else if (!autoplay && !replay.dataset.phase && (location.hash === "#replay" || !location.hash)) {
      inspect(cues[0].hash);
    }
  }

  addEventListener("hashchange", restore);
  addEventListener("popstate", restore);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
    else if (autoplay && inView) start();
  });
  reducedMotion.addEventListener("change", event => {
    if (event.matches) {
      stopAuto();
      pause();
    }
  });

  controls.hidden = false;
  replay.dataset.enhanced = "";
  if (panels.has(location.hash)) {
    inspect(location.hash);
    requestAnimationFrame(() => chapter.scrollIntoView());
  } else if (reducedMotion.matches || !canObserve) {
    inspect(cues[0].hash);
  } else {
    render(0);
    autoplay = new IntersectionObserver(([entry]) => {
      inView = entry.intersectionRatio >= 0.24;
      if (autoplay && inView && !document.hidden) start();
    }, {threshold: 0.24});
    autoplay.observe(pane);
  }
}
