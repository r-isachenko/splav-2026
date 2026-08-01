// Карта опорных точек маршрута (Leaflet + OpenStreetMap).
(function () {
  var pts = window.ROUTE_POINTS || [];
  var el = document.getElementById("map");
  if (!el || !window.L || !pts.length) return;

  var map = L.map(el, { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);

  var bounds = [];
  pts.forEach(function (p) {
    bounds.push([p.lat, p.lon]);
    L.circleMarker([p.lat, p.lon], {
      radius: 7, color: "#00000033", weight: 1,
      fillColor: p.color, fillOpacity: 0.95
    }).addTo(map).bindPopup(
      '<strong>' + p.name + '</strong><br>' +
      (p.purpose ? p.purpose + '<br>' : '') +
      '<span style="color:#888">' + p.lat + ', ' + p.lon + '</span><br>' +
      '<a href="https://yandex.ru/maps/?pt=' + p.lon + ',' + p.lat +
      '&z=15&l=sat" target="_blank" rel="noopener">Открыть в Яндекс.Картах</a>'
    );
  });

  map.fitBounds(bounds, { padding: [30, 30] });
  // клик по карте включает колесо, чтобы не мешать скроллу страницы
  map.on("click", function () { map.scrollWheelZoom.enable(); });
})();
