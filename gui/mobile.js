// Console College — phone/tablet mode. Loaded before app.js by mobile_web.py only (never by the desktop window).
"use strict";
(function () {
  const coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  window.CC_MOBILE = coarse || window.innerWidth < 900;
  if (!window.CC_MOBILE) return;
  document.documentElement.classList.add("mobile");
  if (window.navigator.standalone) document.documentElement.classList.add("standalone");
  // iOS: keep the layout pinned to the visible area when the keyboard opens or the toolbar moves.
  const setVH = () => {
    const h = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    document.documentElement.style.setProperty("--vvh", h + "px");
    const top = document.getElementById("top");
    if (top) document.documentElement.style.setProperty("--toph", top.getBoundingClientRect().height + "px");
    window.scrollTo(0, 0);
  };
  setVH();
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", setVH);
    window.visualViewport.addEventListener("scroll", () => window.scrollTo(0, 0));
  }
  window.addEventListener("orientationchange", () => setTimeout(() => window.dispatchEvent(new Event("resize")), 250));
  // Hand the "Copy screen" job to the phone's clipboard only (the server has none).
  document.addEventListener("DOMContentLoaded", () => {
    setVH();
    const line = document.getElementById("line");
    if (line) { line.setAttribute("autocapitalize", "off"); line.setAttribute("autocorrect", "off");
      line.setAttribute("enterkeyhint", "send"); line.placeholder = "Type an answer, or tap a key"; }
    const copy = document.getElementById("copy");
    if (copy) copy.textContent = "Copy";
  });
})();
