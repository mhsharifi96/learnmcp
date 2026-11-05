// Turns the relative invite path into an absolute URL and wires the copy button.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".learnmcp-invite").forEach(function (wrap) {
    var input = wrap.querySelector("input");
    input.value = new URL(wrap.dataset.path, window.location.origin).toString();
    wrap.querySelector(".learnmcp-copy").addEventListener("click", function (e) {
      navigator.clipboard.writeText(input.value).then(function () {
        e.target.textContent = "Copied";
        setTimeout(function () { e.target.textContent = "Copy"; }, 1500);
      });
    });
  });
});
