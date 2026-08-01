// Чек-листы с сохранением в localStorage. Состояние — на устройстве участника.
(function () {
  var KEY = "splav2026:checks";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  function updateProgress(list) {
    var name = list.getAttribute("data-list");
    var boxes = list.querySelectorAll('input[type=checkbox]');
    var done = 0;
    boxes.forEach(function (b) { if (b.checked) done++; });
    var label = list.querySelector('[data-progress="' + name + '"]');
    if (label) label.textContent = "Собрано " + done + " из " + boxes.length;
  }

  document.querySelectorAll('.checklist input[type=checkbox]').forEach(function (box) {
    var key = box.getAttribute("data-key");
    if (state[key]) box.checked = true;
    box.addEventListener("change", function () {
      if (box.checked) state[key] = 1; else delete state[key];
      save();
      updateProgress(box.closest(".checklist"));
    });
  });

  document.querySelectorAll(".checklist").forEach(updateProgress);
})();
