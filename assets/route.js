// Карта опорных точек маршрута на Яндекс.Картах (JS API 2.1).
(function () {
  var pts = window.ROUTE_POINTS || [];
  var el = document.getElementById("map");
  if (!el || !pts.length) return;

  function fallback() {
    // Если карта не загрузилась (нет ключа / нет сети) — показать ссылку.
    el.classList.add("map-fallback");
    el.innerHTML =
      '<p>Карта не загрузилась. Открой точки маршрута в ' +
      '<a href="https://yandex.ru/maps/?pt=' + pts[0].lon + "," + pts[0].lat +
      '&z=11" target="_blank" rel="noopener">Яндекс.Картах</a>.</p>';
  }

  if (!window.ymaps || !ymaps.ready) { fallback(); return; }

  ymaps.ready(function () {
    try {
      var map = new ymaps.Map(el, {
        center: [pts[0].lat, pts[0].lon],
        zoom: 11,
        controls: ["zoomControl", "fullscreenControl", "typeSelector"]
      }, { suppressMapOpenBlock: true });

      map.behaviors.disable("scrollZoom"); // не перехватываем скролл страницы

      var coords = [];
      pts.forEach(function (p) {
        coords.push([p.lat, p.lon]);
        map.geoObjects.add(new ymaps.Placemark([p.lat, p.lon], {
          balloonContentHeader: p.name,
          balloonContentBody:
            (p.purpose ? p.purpose + "<br>" : "") +
            '<span style="color:#888">' + p.lat + ", " + p.lon + "</span>",
          balloonContentFooter:
            '<a href="https://yandex.ru/maps/?pt=' + p.lon + "," + p.lat +
            '&z=15&l=sat" target="_blank" rel="noopener">Открыть точку</a>',
          hintContent: p.name
        }, { preset: p.preset }));
      });

      map.setBounds(ymaps.util.bounds.fromPoints(coords), {
        checkZoomRange: true, zoomMargin: 30
      });
    } catch (e) {
      fallback();
    }
  });
})();
