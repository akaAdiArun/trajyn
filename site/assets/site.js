const replay = document.querySelector("[data-replay]");
if (replay) {
  const steps = [...replay.querySelectorAll("[data-step]")];
  const links = [...replay.querySelectorAll(".replay-index a")];
  const previous = replay.querySelector("[data-prev]");
  const next = replay.querySelector("[data-next]");
  const position = replay.querySelector("[data-position]");
  let index = 0;

  function select(i) {
    index = Math.min(Math.max(i, 0), steps.length - 1);
    steps.forEach((step, n) => { step.hidden = n !== index; });
    links.forEach((link, n) => {
      if (n === index) link.setAttribute("aria-current", "step");
      else link.removeAttribute("aria-current");
    });
    previous.disabled = index === 0;
    next.disabled = index === steps.length - 1;
    position.textContent = `Step ${index + 1} of ${steps.length}`;
  }

  const onHash = () => {
    const match = steps.findIndex(step => `#${step.id}` === location.hash);
    if (match !== -1) select(match);
    else if (location.hash === "#replay") select(0);
  };
  previous.addEventListener("click", () => select(index - 1));
  next.addEventListener("click", () => select(index + 1));
  links.forEach((link, i) => link.addEventListener("click", () => select(i)));
  addEventListener("hashchange", onHash);
  replay.querySelector(".replay-controls").hidden = false;
  select(0);
  onHash();
}
