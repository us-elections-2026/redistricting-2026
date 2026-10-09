// 신·구 선거구 지도 나란히 — 이동·확대 동기화. 페이지의 <div class="mappair" data-st="tx"> 하나당 한 쌍.
// GeoJSON 속성: cd(예 "TX-28"), m(2024 대선 마진, 양수=D+, 없으면 null), hl(영향 구 여부)
(function () {
  const D = [25, 113, 194], R = [201, 42, 42];
  const mix = (c, t) => c.map(x => Math.round(255 + (x - 255) * t));
  function fill(m) {
    if (m === null || m === undefined) return "#dee2e6";
    const t = Math.min(Math.abs(m), 30) / 30 * 0.85 + 0.15;
    const c = mix(m > 0 ? D : R, t);
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }
  const fmt = m => (m === null || m === undefined) ? "마진 미확인" : `2024 대선 ${m > 0 ? "D" : "R"}+${Math.abs(m).toFixed(1)}`;

  function makeMap(el, data) {
    const map = L.map(el, { zoomSnap: 0.25, scrollWheelZoom: false, attributionControl: true });
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors", maxZoom: 12
    }).addTo(map);
    const layer = L.geoJSON(data, {
      style: f => ({
        fillColor: fill(f.properties.m), fillOpacity: 0.78,
        color: f.properties.hl ? "#111" : "#fff", weight: f.properties.hl ? 2 : 0.7
      }),
      onEachFeature: (f, l) => {
        l.bindTooltip(`<b>${f.properties.cd}</b><br>${fmt(f.properties.m)}`, { sticky: true });
        if (f.properties.hl) l.on("add", () => l.bringToFront());
      }
    }).addTo(map);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 12, pane: "shadowPane" }).addTo(map);
    return { map, layer };
  }

  async function init(box) {
    const st = box.dataset.st;
    const [oldG, newG] = await Promise.all(
      ["old", "new"].map(k => fetch(`${box.dataset.base || "../"}data/geo/${st}_${k}.geojson`).then(r => r.ok ? r.json() : null))
    );
    const a = makeMap(box.querySelector(".map-old"), oldG);
    const b = newG ? makeMap(box.querySelector(".map-new"), newG) : null;
    a.map.fitBounds(a.layer.getBounds());
    if (!b) { box.querySelector(".map-new").innerHTML = '<p class="nomap">신 지도 경계 파일 미확보</p>'; return; }
    b.map.fitBounds(a.layer.getBounds());
    let lock = false;
    const sync = (src, dst) => src.on("move", () => {
      if (lock) return; lock = true; dst.setView(src.getCenter(), src.getZoom(), { animate: false }); lock = false;
    });
    sync(a.map, b.map); sync(b.map, a.map);
  }
  document.addEventListener("DOMContentLoaded", () => document.querySelectorAll(".mappair").forEach(init));
})();
