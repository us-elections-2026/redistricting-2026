#!/usr/bin/env python3
"""주별 신·구 선거구 경계 → data/geo/<st>_{old,new}.geojson (단순화·속성 cd/m/hl)

구 지도: Census 2024 cartographic boundary cb_2024_us_cd119_500k (2024 선거에 쓴 119대 의회 선거구)
신 지도: data/geo_sources.json 에 주별 원본 경로·지역구 번호 열을 적는다.
사용법: python3.11 scripts/make_geo.py <cd119 shp 경로>
"""
import json
import os
import sys

import geopandas as gpd

ROOT = os.path.join(os.path.dirname(__file__), "..")
FIPS = {"TX": "48", "CA": "06", "FL": "12", "OH": "39", "NC": "37", "TN": "47", "LA": "22", "AL": "01", "UT": "49"}


def write(gdf, st, kind, margins, hl):
    gdf = gdf.to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.buffer(0)  # 무효 폴리곤 보정(TN 원본 1건)
    gdf["geometry"] = gdf.geometry.simplify(0.003, preserve_topology=True)
    feats = []
    for _, r in gdf.iterrows():
        cd = r["cd"]
        feats.append({"type": "Feature", "geometry": r.geometry.__geo_interface__,
                      "properties": {"cd": cd, "m": margins.get(cd), "hl": cd in hl}})
    fc = {"type": "FeatureCollection", "features": feats}
    p = os.path.join(ROOT, "data", "geo", f"{st.lower()}_{kind}.geojson")
    json.dump(fc, open(p, "w"), separators=(",", ":"))
    print(p, len(feats), os.path.getsize(p) // 1024, "KB")


def main(cd119):
    allcd = gpd.read_file(cd119)
    src = json.load(open(os.path.join(ROOT, "data", "geo_sources.json"))) if os.path.exists(
        os.path.join(ROOT, "data", "geo_sources.json")) else {}
    for st, fp in FIPS.items():
        s = json.load(open(os.path.join(ROOT, "data", "states", f"{st.lower()}.json"), encoding="utf-8"))
        hl = set(s.get("trend_districts", []))
        old_m = {d["district"]: d.get("old_pres_margin_2024") for d in s["districts"]}
        new_m = {d["district"]: d.get("new_pres_margin_2024") for d in s["districts"]}
        g = allcd[allcd.STATEFP == fp].copy()
        g["cd"] = st + "-" + g["CD119FP"].astype(int).map(lambda n: f"{max(n, 1):02d}")
        write(g, st, "old", old_m, hl)
        if st in src:
            n = gpd.read_file(os.path.expanduser(src[st]["path"]))
            n = n[n[src[st]["col"]].astype(str).str.extract(r"(\d+)")[0].astype(float) > 0]
            n["cd"] = st + "-" + n[src[st]["col"]].astype(str).str.extract(r"(\d+)")[0].astype(int).map(lambda x: f"{x:02d}")
            write(n, st, "new", new_m, hl)


if __name__ == "__main__":
    main(sys.argv[1])
