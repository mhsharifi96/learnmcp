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

// Quiz page: show the prompt fields or the question list depending on the chosen mode.
document.addEventListener("DOMContentLoaded", function () {
  var radios = document.querySelectorAll('input[name="mode"]');
  if (!radios.length) return;
  var aiRows = [".field-prompt", ".field-ai_question_count"].map(function (s) { return document.querySelector(s); });
  var questions = document.getElementById("questions-group");
  function update() {
    var checked = document.querySelector('input[name="mode"]:checked');
    var ai = checked && checked.value === "ai";
    aiRows.forEach(function (row) { if (row) row.style.display = ai ? "" : "none"; });
    if (questions) questions.style.display = ai ? "none" : "";
  }
  radios.forEach(function (r) { r.addEventListener("change", update); });
  update();
});
