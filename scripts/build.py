#!/usr/bin/env python3
"""data/*.json → index.qmd · states/<st>.qmd · trends.qmd 생성.

페이지 본문은 전부 이 스크립트가 데이터에서 만든다(손으로 고치지 말 것 — 다음 빌드가 덮어쓴다).
수치는 data/에 출처 URL과 함께 있는 값만 쓴다. 없으면 '미확인'.
사용법: python3 scripts/build.py
"""
import collections
import html
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
ORDER = ["tx", "ca", "fl", "oh", "nc", "tn", "la", "al", "ut"]


def load(p):
    return json.load(open(os.path.join(ROOT, "data", p), encoding="utf-8"))


STATES = {st: load(f"states/{st}.json") for st in ORDER}
MO = load("states/mo.json")
LAND = load("landscape.json")
COOK = load("cook_history.json")
RATERS = load("raters_history.json")
LOG = load("district_log.json")
FEC = load("fec.json")
GEOSRC = load("geo_sources.json")
CHECKED = max(s.get("checked", "") for s in STATES.values())


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def cell(s):
    return str(s if s not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def mfmt(m, digits=1):
    if m is None:
        return '<span class="na">미확인</span>'
    if abs(m) < 0.05:
        return "동률"
    p = "D" if m > 0 else "R"
    v = abs(m)
    t = f"{v:.0f}" if float(v).is_integer() else f"{v:.{digits}f}"
    return f'<span class="m{p.lower()}">{p}+{t}</span>'


def delta(o, n):
    if o is None or n is None:
        return "—"
    d = n - o
    if abs(d) < 0.05:
        return "0"
    return f'<span class="m{"d" if d > 0 else "r"}">{"D" if d > 0 else "R"} 쪽 {abs(d):.1f}p</span>'


def flipped(d):
    o, n = d.get("old_pres_margin_2024"), d.get("new_pres_margin_2024")
    return o is not None and n is not None and o * n < 0


def rkey(r):
    """등급 문자열 → 색 키 (solid_d … solid_r / tossup)."""
    if not r:
        return None
    s = r.lower().replace("leans", "lean").replace("tilts", "lean").replace("tilt", "lean")
    if "toss" in s:
        return "tossup"
    for lvl in ("solid", "safe", "likely", "lean"):
        if lvl in s:
            side = "d" if re.search(r"\bd\b|dem", s) else "r" if re.search(r"\br\b|rep", s) else None
            if side:
                return f"{'solid' if lvl == 'safe' else lvl}_{side}"
    return None


RANK = {"solid_r": 0, "likely_r": 1, "lean_r": 2, "tossup": 3, "lean_d": 4, "likely_d": 5, "solid_d": 6}


def badge(r):
    k = rkey(r)
    return f'<span class="rt rt-{k or "na"}">{esc(r) if r else "—"}</span>'


def cook_now(cd):
    v = COOK["districts"].get(cd)
    return v["ratings"].get(COOK["dates"][-1]) if v else None


def link(url, text="출처"):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>' if url else ""


def host(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m[1] if m else url


def seats(o):
    if not o or o.get("D") is None:
        return "미확인"
    return f'D {o["D"]} · R {o["R"]}'


def front(title, subtitle=None, toc=True):
    lines = ["---", f'title: "{title}"']
    if subtitle:
        lines.append(f'subtitle: "{subtitle}"')
    if not toc:
        lines.append("toc: false")
    lines.append("---")
    lines.append("<!-- scripts/build.py 생성 파일 — 직접 수정 금지 -->\n")
    return "\n".join(lines)


def asof_line():
    return (f'<p class="as-of">조사 기준 {CHECKED} · Cook 등급 스냅샷 {COOK["dates"][-1]} · '
            f'FEC {FEC["as_of"]} · 일일 브리핑 {LOG["entries"][-1]["date"] if LOG["entries"] else "—"}까지</p>\n')


# ── 신·구 마진 덤벨 (SVG) ───────────────────────────────────────────────
def dumbbell(rows, width=640):
    """rows: [(label, old, new, href)] — 신·구 둘 다 있는 구만."""
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    if not rows:
        return ""
    lim = max(30, max(max(abs(r[1]), abs(r[2])) for r in rows))
    lim = min(60, (int(lim) // 10 + 1) * 10)
    L, Rr, rh, top = 92, 24, 20, 26
    W = width - L - Rr
    h = top + rh * len(rows) + 10
    x = lambda v: L + (max(-lim, min(lim, -v)) + lim) / (2 * lim) * W  # 왼쪽 = D
    out = [f'<svg class="dumbbell" viewBox="0 0 {width} {h}" role="img" aria-label="2024 대선 마진 신·구 비교">']
    for t in range(-lim, lim + 1, 10):
        xx = x(-t)
        out.append(f'<line x1="{xx:.1f}" y1="{top - 6}" x2="{xx:.1f}" y2="{h - 6}" class="{"axis0" if t == 0 else "grid"}"/>')
        lab = "0" if t == 0 else f'{"D" if t < 0 else "R"}+{abs(t)}'
        out.append(f'<text x="{xx:.1f}" y="{top - 10}" class="tick">{lab}</text>')
    for i, (lab, o, n, href) in enumerate(rows):
        y = top + i * rh + rh / 2
        a, b = x(o), x(n)
        out.append(f'<a href="{esc(href)}"><text x="{L - 8}" y="{y + 4:.1f}" class="lab">{esc(lab)}</text></a>')
        out.append(f'<line x1="{a:.1f}" y1="{y:.1f}" x2="{b:.1f}" y2="{y:.1f}" class="bar {"tod" if n > o else "tor"}"/>')
        out.append(f'<circle cx="{a:.1f}" cy="{y:.1f}" r="4" class="old"><title>{esc(lab)} 구 지도 {o:+.1f}</title></circle>')
        out.append(f'<circle cx="{b:.1f}" cy="{y:.1f}" r="5" class="new {"d" if n > 0 else "r"}"><title>{esc(lab)} 신 지도 {n:+.1f}</title></circle>')
    out.append("</svg>")
    return ('<div class="figwrap">' + "".join(out) +
            '<p class="figlegend"><span class="dot old"></span> 구 지도 &nbsp; <span class="dot new"></span> 신 지도 '
            '(2024 대선 표를 각 경계로 다시 집계한 마진, 왼쪽=민주 우위)</p></div>\n')


# ── 개요 ────────────────────────────────────────────────────────────────
def build_index():
    alld = [(st, d) for st in ORDER for d in STATES[st]["districts"]]
    flips = [(st, d) for st, d in alld if flipped(d)]
    to_r = [x for x in flips if x[1]["new_pres_margin_2024"] < 0]
    to_d = [x for x in flips if x[1]["new_pres_margin_2024"] > 0]
    nat = LAND["national_trackers"][0]
    p = [front("2026 재획정 상세 트래커", "주별 지도 변화와 영향 지역구", toc=False), asof_line()]
    p.append("""
::: {.lead}
2026년 11월 하원 선거에서 **새 선거구 지도를 쓰는 주는 9곳**이다. 이 사이트는 그 9개 주에서 지도가 어떻게 바뀌었는지, 어느 지역구가 어떤 영향을 받았는지를 지역구 단위로 정리하고, 영향 지역구의 등급·모금·현지 동향을 추적한다. 제도·배경 설명은 [본 사이트 재획정 페이지](https://us-elections-2026.github.io/redistricting.html)에 있다.
:::
""")
    p.append('<div class="kpis">')
    kp = [("새 지도 사용 주", f"{len(ORDER)}", "미주리는 구 지도 복귀"),
          ("집계 지역구", f"{len(alld)}", "당파 성향이 바뀐 구 중심"),
          ("우위 정당이 뒤집힌 구", f"{len(flips)}", f"공화 쪽 {len(to_r)} · 민주 쪽 {len(to_d)} (2024 대선 기준)"),
          ("지도 합산 순효과", "R +9", f'{esc(nat["name"].split(" — ")[0])} {esc(nat["date"][:10])} · 선거 예측 아님')]
    for a, b, c in kp:
        p.append(f'<div class="kpi"><div class="k">{a}</div><div class="v">{b}</div><div class="s">{c}</div></div>')
    p.append("</div>\n")
    p.append(f'<p class="note">순효과 출처: {link(nat["url"], nat["name"])} — "{esc(nat["net_estimate"])}". '
             '각 지도의 잠재 효과를 더한 값이며 의석 예측이 아니다.</p>\n')

    p.append("## 주별 요약 {#states}\n")
    p.append("| 주 | 그린 주체·현재 상태 | 2024 결과 | 신 지도 기대치 | 순효과(D) | 뒤집힌 구 | 소송 |\n|--------|------------------------------|--------|--------|-----:|----------|--------------------|")
    for st in ORDER:
        s = STATES[st]
        fl = [d["district"] for d in s["districts"] if flipped(d)]
        e = s.get("expected_seats_new_map") or {}
        net = s.get("net_effect_d")
        lit = s.get("litigation") or ""
        p.append(f'| [{esc(s["name"])}](states/{st}.qmd) | {cell(short(s["status_summary"], 70))} | {seats(s.get("seats_2024_result"))} | '
                 f'{seats(e)} | {f"{net:+d}" if isinstance(net, int) else cell(net)} | {", ".join(fl) or "—"} | {cell(short(lit, 50))} |')
    p.append('\n<p class="note">신 지도 기대치 = 2024 대선 표를 새 경계로 다시 집계했을 때 각 당 후보가 이긴 구 수(주별 페이지에 근거 표기). 순효과는 주별 조사에서 인용한 출처 값.</p>\n')

    p.append("## 우위 정당이 뒤집힌 지역구 {#flips}\n")
    rows = sorted([(d["district"], d["old_pres_margin_2024"], d["new_pres_margin_2024"], f"states/{st}.html#{d['district'].lower()}")
                   for st, d in flips], key=lambda r: r[2] - r[1])
    p.append(dumbbell(rows))

    p.append("## 미주리 — 새 지도를 만들었지만 본선에서는 쓰지 않는다 {#mo}\n")
    p.append(MO["status_summary"] + "\n")
    p.append('\n::: {.callout-note collapse="true" title="미주리 경과"}\n')
    for t in MO["timeline"]:
        p.append(f'- **{t["date"]}** {t["event"]} {link(t.get("source_url"))}')
    p.append(":::\n")

    p.append("## 시도했으나 무산된 주 {#failed}\n")
    p.append("| 주 | 상태 | 요약 |\n|---|---|---|")
    for x in LAND["states"]:
        if x["status_2026"] in ("차단", "부결"):
            p.append(f'| {esc(x["name"])} | {x["status_2026"]} | {cell(x["summary"])} {link(x.get("source_url"))} |')
    write("index.qmd", "\n".join(p))


def short(s, n):
    s = re.sub(r"\s+", " ", s or "")
    if len(s) <= n:
        return s
    m = re.match(r"(.*?다)\.", s)
    return m[1] + "." if m and len(m[1]) <= n + 40 else s[:n] + "…"


# ── 주별 ────────────────────────────────────────────────────────────────
def build_state(st):
    s = STATES[st]
    ST = st.upper()
    trend = set(s.get("trend_districts", []))
    p = [front(f'{s["name"]} ({ST})', "지도 변화와 영향 지역구"), asof_line()]
    p.append(f'::: {{.lead}}\n{s["status_summary"]}\n:::\n')
    e = s.get("expected_seats_new_map") or {}
    p.append('<div class="kpis">')
    for a, b, c in [
        ("의석", s.get("seats_total", "—"), ""),
        ("2024 결과", seats(s.get("seats_2024_result")), host(s.get("seats_2024_result", {}).get("source_url"))),
        ("신 지도 기대치", seats(e), "2024 대선 재집계 기준"),
        ("순효과(D)", f'{s["net_effect_d"]:+d}' if isinstance(s.get("net_effect_d"), int) else "미확인", host(s.get("net_effect_source_url"))),
    ]:
        p.append(f'<div class="kpi"><div class="k">{a}</div><div class="v">{b}</div><div class="s">{esc(c)}</div></div>')
    p.append("</div>\n")

    if e.get("basis"):
        p.append(f'<p class="note">신 지도 기대치 근거: {esc(e["basis"])} {link(e.get("source_url"))}</p>\n')
    p.append("## 지도 비교 {#maps}\n")
    p.append(f'<div class="mappair" data-st="{st}" data-base="../"><div><h4>구 지도 (2024 선거)</h4><div class="map map-old"></div></div>'
             f'<div><h4>신 지도 (2026 선거)</h4><div class="map map-new"></div></div></div>\n'
             '<script src="../assets/maps.js"></script>\n')
    p.append('<p class="figlegend">색 = 2024 대선 마진(<span class="md">파랑=민주</span>·<span class="mr">빨강=공화</span>, 진할수록 큼). '
             '회색 = 마진 미수집. 검은 테두리 = 추세 추적 대상 구. 두 지도는 함께 움직인다. 구 지도 경계: Census 2024 cartographic boundary(119대 의회 선거구).'
             + (f' 신 지도 경계: {link(GEOSRC[ST]["src"], GEOSRC[ST]["label"])}.' if ST in GEOSRC else "")
             + (f' 공식 신 지도 문서: {link(s["maps"].get("new_map_url"), s["maps"].get("plan_id") or "신 지도")}' if s.get("maps", {}).get("new_map_url") else "")
             + "</p>\n")

    p.append("## 어떻게 그렸나 {#mechanism}\n")
    p.append((s.get("mechanism") or "미확인") + "\n")

    ds = s["districts"]
    rows = [(d["district"], d.get("old_pres_margin_2024"), d.get("new_pres_margin_2024"), f"#{d['district'].lower()}") for d in ds]
    rows.sort(key=lambda r: (r[2] - r[1]) if r[1] is not None and r[2] is not None else 0)
    p.append("## 영향 지역구 {#districts}\n")
    p.append(dumbbell(rows))
    p.append("| 구 | 현역 | 현역 2026 | 구 지도 | 신 지도 | 변화 | Cook (" + COOK["dates"][-1][5:] + ") |\n|-------|-----------|----------------|------:|------:|---------|--------|")
    for d in sorted(ds, key=lambda d: int(d["district"].split("-")[1])):
        cd = d["district"]
        name = f'<span class="nw"><a href="#{cd.lower()}">{cd}</a>' + (" ★" if cd in trend else "") + "</span>"
        p.append(f'| {name} | {cell(d.get("incumbent"))} ({cell(d.get("incumbent_party"))}) | {cell(short(d.get("incumbent_2026"), 36))} | '
                 f'{mfmt(d.get("old_pres_margin_2024"))} | {mfmt(d.get("new_pres_margin_2024"))} | '
                 f'{delta(d.get("old_pres_margin_2024"), d.get("new_pres_margin_2024"))} | {badge(cook_now(cd))} |')
    p.append('\n<p class="note">마진 = 2024 대선 표를 구·신 경계로 각각 다시 집계한 해리스–트럼프 차이(선거를 다시 한 값이 아님). ★ = [지역구 추세](../trends.qmd) 추적 대상. '
             'Cook 등급은 270toWin 재게시판 자동 취득 스냅샷.</p>\n')

    p.append("## 지역구별 상세 {#detail}\n")
    for d in sorted(ds, key=lambda d: int(d["district"].split("-")[1])):
        cd = d["district"]
        nm = d.get("nominees_2026") or {}
        p.append(f'### {cd} — {esc(d.get("impact") or "")} {{#{cd.lower()}}}\n')
        p.append(f'<p class="dmeta">2024 대선 {mfmt(d.get("old_pres_margin_2024"))} → {mfmt(d.get("new_pres_margin_2024"))} '
                 f'{link(d.get("margin_source_url"), host(d.get("margin_source_url")))}'
                 + (f' · <a href="../trends.html#{cd.lower()}">추세 보기 →</a>' if cd in trend else "") + "</p>\n")
        items = [("경계 변화", d.get("geography_change")),
                 ("현역", f'{d.get("incumbent") or "—"} ({d.get("incumbent_party") or "—"}) — {d.get("incumbent_2026") or "미확인"}'),
                 ("2026 후보", f'민주 {nm.get("D") or "미확인"} · 공화 {nm.get("R") or "미확인"}'),
                 ("등급", (d.get("rating_now") or "미확인") + (" " + link(d.get("rating_source_url"), host(d.get("rating_source_url"))) if d.get("rating_source_url") else "")),
                 ("메모", d.get("notes")), ("주의", d.get("margin_note"))]
        for k, v in items:
            if v:
                p.append(f"- **{k}** {v}")
        p.append("")

    p.append("## 경과 {#timeline}\n")
    for t in sorted(s.get("timeline", []), key=lambda t: t["date"]):
        p.append(f'- **{t["date"]}** {t["event"]} {link(t.get("source_url"))}')
    p.append("\n## 소송 {#litigation}\n")
    p.append((s.get("litigation") or "없음") + "\n")
    if s.get("changes_vs_baseline"):
        p.append('::: {.callout-note collapse="true" title="6월 기준선 대비 바뀐 점"}')
        p += [f"- {c}" for c in s["changes_vs_baseline"]]
        p.append(":::\n")
    p.append('::: {.callout-warning collapse="true" title="확인하지 못한 항목"}')
    p += [f"- {u}" for u in s.get("unverified", [])] or ["- 없음"]
    p.append(":::\n")
    p.append("## 출처 {#sources}\n")
    p += [f"- {link(u, u)}" for u in s.get("sources", [])]
    write(f"states/{st}.qmd", "\n".join(p))


# ── 추세 ────────────────────────────────────────────────────────────────
TYPE_KO = {"poll": "여론조사", "rating": "등급", "money": "자금", "candidate": "후보", "map": "지도·소송", "event": "동향"}


def build_trends():
    dmeta = {d["district"]: (st, d) for st in ORDER for d in STATES[st]["districts"]}
    logs = collections.defaultdict(list)
    for r in LOG["entries"]:
        logs[r["district"]].append(r)
    p = [front("지역구 추세", "재획정 9개 주 영향 지역구의 등급·자금·현지 동향"), asof_line()]
    p.append("""::: {.lead}
재획정 9개 주에서 **당파 성향이 뒤집혔거나 경합권(신 지도 마진 ±15p 이내)으로 3p 이상 움직인 구**, **Cook 등급이 Solid가 아닌 구**, **일일 브리핑에 세 번 이상 나온 구**를 추적한다. 지역구 단위 조사는 드물어 정보가 비어 있는 구가 많다 — 빈칸은 자료가 없다는 뜻이다.
:::
""")
    # Cook 이력 매트릭스
    dates = COOK["dates"]
    p.append("## Cook 등급 이력 {#cook}\n")
    p.append('<div class="tblwrap"><table class="matrix"><thead><tr><th>구</th><th>신 지도 마진</th>'
             + "".join(f"<th>{d[5:].replace('-', '/')}</th>" for d in dates) + "<th>이동</th></tr></thead><tbody>")
    for st in ORDER:
        p.append(f'<tr class="grp"><td colspan="{len(dates) + 3}"><a href="states/{st}.html">{esc(STATES[st]["name"])}</a></td></tr>')
        for cd in STATES[st]["trend_districts"]:
            rs = [COOK["districts"].get(cd, {}).get("ratings", {}).get(d) for d in dates]
            ks = [RANK.get(rkey(r)) for r in rs if r]
            mv = "—"
            if len(ks) >= 2 and ks[-1] != ks[0]:
                mv = f'<span class="md">민주 쪽 ▲{ks[-1] - ks[0]}</span>' if ks[-1] > ks[0] else f'<span class="mr">공화 쪽 ▼{ks[0] - ks[-1]}</span>'
            nm = dmeta.get(cd, (None, {}))[1].get("new_pres_margin_2024")
            p.append(f'<tr><td><a href="#{cd.lower()}">{cd}</a></td><td>{mfmt(nm)}</td>'
                     + "".join(f"<td>{badge(r)}</td>" for r in rs) + f"<td>{mv}</td></tr>")
    p.append("</tbody></table></div>\n")
    p.append(f'<p class="note">{esc(COOK["source_label"])}. 이동 칸은 첫 스냅샷 대비 마지막 스냅샷의 단계 수.</p>\n')

    p.append("## 지역구별 추세 {#districts}\n")
    p.append("::: {.panel-tabset}\n")
    for st in ORDER:
        p.append(f'### {STATES[st]["name"]}\n')
        for cd in STATES[st]["trend_districts"]:
            p.append(district_block(cd, dmeta.get(cd), logs.get(cd, [])))
    p.append(":::\n")
    write("trends.qmd", "\n".join(p))


def district_block(cd, meta, entries):
    st, d = meta if meta else (None, {})
    out = [f'#### {cd} {{#{cd.lower()}}}\n']
    bits = []
    if d:
        bits.append(f'2024 대선 {mfmt(d.get("old_pres_margin_2024"))} → {mfmt(d.get("new_pres_margin_2024"))}')
        nm = d.get("nominees_2026") or {}
        if nm.get("D") or nm.get("R"):
            bits.append(f'민주 {esc(nm.get("D") or "미확인")} 대 공화 {esc(nm.get("R") or "미확인")}')
        bits.append(f'<a href="states/{st}.html#{cd.lower()}">지도 변화 →</a>')
    else:
        bits.append("지도 변화가 작아 주별 표에는 없는 구(경합 또는 브리핑 빈출로 추적)")
    out.append(f'<p class="dmeta">{" · ".join(bits)}</p>\n')

    # 등급
    rh = RATERS["districts"].get(cd)
    rs = [COOK["districts"].get(cd, {}).get("ratings", {}).get(x) for x in COOK["dates"]]
    line = " → ".join(f'{badge(r)}<span class="dt">{x[5:]}</span>' for r, x in zip(rs, COOK["dates"]) if r)
    out.append(f"- **Cook** {line or '—'}")
    if rh:
        last = rh[max(rh)]
        chg = []
        prev = None
        for dt in sorted(rh):
            cur = (rh[dt].get("rating_cook"), rh[dt].get("rating_sabato"), rh[dt].get("rating_inside"))
            if cur != prev:
                chg.append(dt)
            prev = cur
        out.append(f'- **3사 등급(최신 {max(rh)})** Cook {badge(last.get("rating_cook"))} · Sabato {badge(last.get("rating_sabato"))}'
                   + (f' · Inside {badge(last.get("rating_inside"))}' if last.get("rating_inside") else "")
                   + (f' <span class="dt">(조합이 바뀐 판본: {", ".join(x[5:] for x in chg[1:])})</span>' if len(chg) > 1 else ""))
    # 자금 — 본선 후보(성 일치)를 앞에, 나머지는 '기타'로
    fec = [c for c in FEC["districts"].get(cd) or [] if c["receipts"] >= 0.1]
    nm = (d or {}).get("nominees_2026") or {}
    lasts = {re.split(r"\s+", re.sub(r"\(.*?\)", "", v).strip())[-1].lower() for v in nm.values() if v}

    def fc(c):
        return (f'<span class="p{c["party"][:1].lower()}">{esc(c["name"].title())}</span> {c["receipts"]:.2f}'
                + (f' (현금 {c["cash_on_hand"]:.2f}, ~{c["coverage_end"][5:]})' if c.get("cash_on_hand") is not None and c.get("coverage_end") else ""))
    main = [c for c in fec if c["name"].split(",")[0].strip().lower() in lasts]
    rest = [c for c in fec if c not in main][: (6 - len(main)) if main else 6]
    if fec:
        txt = " · ".join(fc(c) for c in main)
        if rest:
            txt += (f' <span class="muted">· 기타 ' if main else "") + " · ".join(fc(c) for c in rest) + ("</span>" if main else "")
        out.append(f'- **FEC 누적 모금** <span class="dt">({FEC["as_of"]} 취득, $M'
                   + (", 본선 후보 먼저" if main else ", 본선 후보 미확인 — 예비선거 탈락자 포함 가능") + f")</span> {txt}")
    else:
        out.append("- **FEC 누적 모금** 0.1M 이상 후보 없음 또는 미보고")
    # 일지
    if entries:
        out.append(f'\n::: {{.callout-note collapse="{str(len(entries) > 6).lower()}" title="현지 동향 일지 — {len(entries)}건 (하원 일일 브리핑)"}}')
        for r in sorted(entries, key=lambda r: r["date"], reverse=True):
            warn = ' <span class="warn" title="원문에 미확인·2차 집계 단서">⚠</span>' if r.get("caution") else ""
            out.append(f'- <span class="dt">{r["date"][5:]}</span> <span class="ty ty-{r["type"]}">{TYPE_KO.get(r["type"], r["type"])}</span> '
                       f'{esc(r["summary"])}{warn}')
        out.append(":::\n")
    else:
        out.append("- **현지 동향 일지** 브리핑 언급 없음\n")
    return "\n".join(out) + "\n"


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text.rstrip() + "\n")
    print("wrote", rel)


if __name__ == "__main__":
    build_index()
    for st in ORDER:
        build_state(st)
    build_trends()
