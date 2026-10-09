# 2026 재획정 상세 트래커

2026 미국 하원 선거에서 새 선거구 지도를 쓰는 9개 주(TX·CA·FL·OH·NC·TN·LA·AL·UT)의 지도 변화와 영향 지역구 추세.
본 사이트(us-elections-2026.github.io)의 재획정 설명 페이지를 지역구 단위로 확장한 별도 사이트.

## 구조

| 경로 | 내용 | 만드는 것 |
|---|---|---|
| `data/states/<st>.json` | 주별 현황·경과·소송·지역구 신·구 마진·후보·출처·미확인 목록, `trend_districts` | 웹 조사(2026-10-10) |
| `data/landscape.json` | 전체 주 현황, 전국 순효과 집계 | 웹 조사 |
| `data/cook_history.json` | Cook 지역구 등급 스냅샷 | 본 사이트 git 이력의 `house_cook_districts.json` |
| `data/raters_history.json` | 경합구 3사 등급 판본 | 본 사이트 git 이력의 `house_races.json` |
| `data/district_log.json` | 지역구 일지(원문 인용, 전수 문자열 대조) | `_NIS` 하원 일일 브리핑 KR |
| `data/fec.json` | 후보 누적 모금 | `scripts/fetch_fec.py` (FEC API) |
| `data/geo/<st>_{old,new}.geojson` | 지도 경계(단순화) | `scripts/make_geo.py` |
| `index.qmd` · `states/*.qmd` · `trends.qmd` | 페이지 | `scripts/build.py` — **직접 수정 금지** |
| `methodology.qmd` | 출처·방법 | 손으로 씀 |

## 갱신

```sh
export FEC_API_KEY=...
python3 scripts/fetch_fec.py                       # 모금
python3.11 scripts/make_geo.py <cb_2024_us_cd119_500k.shp>   # 경계(신 지도는 data/geo_sources.json)
python3 scripts/build.py                           # 페이지 생성
quarto preview                                     # 확인 → 커밋·push하면 Actions가 gh-pages로 배포
```

원칙: 수치는 `data/`에 출처 URL과 함께 있는 값만 쓴다. 못 찾은 값은 null('미확인')로 둔다.
