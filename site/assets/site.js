const replay = document.querySelector("[data-replay]");
if (replay) {
  const links = [...replay.querySelectorAll("nav a")];
  const panels = new Map([...replay.querySelectorAll("[data-evidence]")]
    .map(panel => ["#" + panel.id, panel]));
  const firstAction = "#trace-2";

  function show(hash) {
    if (!panels.has(hash)) return;
    for (const [id, panel] of panels) panel.hidden = id !== hash;
    for (const link of links) {
      if (link.hash === hash) {
        link.setAttribute("aria-current", link.closest("ol") ? "step" : "true");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  for (const link of links) {
    link.addEventListener("click", event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        return;
      }
      event.preventDefault();
      if (location.hash !== link.hash) history.pushState(null, "", link.hash);
      show(link.hash);
    });
  }

  function restore() {
    if (panels.has(location.hash)) show(location.hash);
    else if (location.hash === "#replay" || !location.hash) show(firstAction);
  }

  addEventListener("hashchange", restore);
  addEventListener("popstate", restore);
  show(panels.has(location.hash) ? location.hash : firstAction);

  if (panels.has(location.hash)) {
    requestAnimationFrame(() => document.getElementById("replay").scrollIntoView());
  }
}
