#!/usr/bin/env python3
"""v8.0 문서 정합 검증 — exit 0 = 준수.

검사:
  1. Data JSON 5종 파싱 + 개수 (monsters 50 / ambient 53 / races 15 / codex 53 / biomes 20)
  2. codex ID == ambient ID
  3. biomes: 20종 · 그룹 층 범위(1~50/51~95/96~100) · habitat 전부 매핑·중복 0 · 온도(climate band ↔ 종 내성 교차, 면역 역할 제외)
  4. 필수 문서 존재
  5. living 문서에 구수치 정본 주장 잔재 (전투 55종 / 74종 / 플레이어블 13종 / 아종 30종)
  6. living 문서에 구경로 참조 (design-docs/GDD/ · docs/GDD/ — archive/ 제외)
  7. 04_영지 시뮬 블록 ↔ sim_economy.py 실측 동기화 (골드 마일스톤 5행 — 발견 1·1-3 인용 수치)

실행: python3 design-docs/_tools/check_docs.py (soulcommander/ 기준)
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "design-docs")
DATA = os.path.join(ROOT, "unity", "Assets", "Resources", "Data")
errors = []


def fail(msg):
    errors.append(msg)


# 1+2. JSON
try:
    m = json.load(open(os.path.join(DATA, "monsters.json")))["monsters"]
    a = json.load(open(os.path.join(DATA, "ambient.json")))["ambient"]
    r = json.load(open(os.path.join(DATA, "races.json")))["races"]
    e = json.load(open(os.path.join(DATA, "ecology_codex.json")))["entries"]
    for name, got, want in [("monsters", len(m), 50), ("ambient", len(a), 53),
                            ("races", len(r), 15), ("codex", len(e), 53)]:
        if got != want:
            fail(f"{name}.json 개수 {got} (기대 {want})")
    if sorted(x["id"] for x in a) != sorted(x["id"] for x in e):
        fail("ambient.json ID != ecology_codex.json ID")
    # biomes.json (06 문서 — 00 #23 가안)
    bg = json.load(open(os.path.join(DATA, "biomes.json")))["groups"]
    biomes = [x for g in bg for x in g["biomes"]]
    if len(biomes) != 20:
        fail(f"biomes.json 개수 {len(biomes)} (기대 20)")
    spans = sorted(tuple(g["floors"]) for g in bg)
    if spans != [(1, 50), (51, 95), (96, 100)]:
        fail(f"biomes.json 그룹 층 범위 비정합: {spans} (기대 1~50/51~95/96~100)")
    mhab = {h for x in m for h in x["ecology"]["habitat"]}
    ahab = {h for x in a for h in x["ecology"]["habitat"]}
    bhab = [h for x in biomes for h in x["habitat"]]
    dup = sorted({h for h in bhab if bhab.count(h) > 1})
    if dup:
        fail(f"biomes.json habitat 중복 매핑: {dup}")
    orphan = sorted((mhab | ahab) - set(bhab))
    if orphan:
        fail(f"바이옴 미매핑 habitat (monsters/ambient에 있음): {orphan}")
    # 온도 시스템 — 종 내성 ∩ 바이옴 band (06 §3.5 · 면역 역할 제외)
    exempt = {"elemental", "guardian", "undead"}
    clim = {x["id"]: x["climate"]["band"] for x in biomes}
    for sp in m + a:
        ec = sp["ecology"]
        t1, t2 = ec["temperature"]["min"], ec["temperature"]["max"]
        for x in biomes:
            if set(ec["habitat"]) & set(x["habitat"]) and ec["role"] not in exempt:
                lo, hi = clim[x["id"]]
                if t2 < lo or t1 > hi:
                    fail(f"온도 부정합: {sp['id']} 내성 {t1}~{t2} vs {x['id']} band {lo}~{hi}")
    # 먹이그물 메트릭 (08 문서 T-08 — 고아 0 · 비대칭 0 · 간선 >=100 · relationTypes 완전 태깅)
    sp = {x["id"]: x for x in m}
    sp.update({x["id"]: x for x in a})
    web_out = 0
    orph = []
    VALID_REL = {"predation", "scavenge", "ether", "parasitism", "grazing"}
    for sid, s in sp.items():
        eco = s["ecology"]
        prey_ids = [x for x in eco.get("prey") or [] if x in sp]
        pred_ids = eco.get("predators") or []
        rt = eco.get("relationTypes") or {}
        web_out += len(prey_ids)
        # 고아 판정은 자원 간선(corpse/soul/mana 등 에테르·분해 경로)도 연결로 인정 (08 §5.1)
        if not (eco.get("prey") or []) and not pred_ids and eco["role"] not in ("elemental", "mimic"):
            orph.append(sid)
        for q in prey_ids:
            if sid not in (sp[q]["ecology"].get("predators") or []):
                fail(f"그물 비대칭: {sid} → {q} (predators 역방향 누락)")
            if q not in rt:
                fail(f"relationTypes 미태그: {sid} → {q}")
            elif rt[q] not in VALID_REL:
                fail(f"relationTypes 무효값: {sid} → {q} = {rt[q]}")
        for p in pred_ids:
            if p in sp and sid not in (sp[p]["ecology"].get("prey") or []):
                fail(f"그물 비대칭: {p} 먹이에 {sid} 누락")
        stale = [k for k in rt if k not in (eco.get("prey") or [])]
        if stale:
            fail(f"relationTypes stale 키 (prey에 없음): {sid} {stale[:4]}")
    if orph:
        fail(f"그물 고아종 (elemental/mimic 제외): {orph[:10]}")
    if web_out < 100:
        fail(f"그물 간선 부족: {web_out} (기대 >=100)")
    req = ["id", "name", "tier", "stats", "spawn", "loot", "ecology"]
    bad = [x.get("id", "?") for x in m if not all(k in x for k in req)]
    if bad:
        fail(f"monsters.json 스키마 결함: {bad}")
except FileNotFoundError as ex:
    fail(f"JSON 없음: {ex.filename}")
except json.JSONDecodeError as ex:
    fail(f"JSON 파싱 실패: {ex}")

# 3. 필수 문서
required = ["AGENTS.md", "README.md", "GDD_v8.0_00_확정사항.md",
            "GDD_v8.0_01_등급_전투력.md", "GDD_v8.0_02_생태사전.md",
            "GDD_v8.0_03_개발플랜.md", "GDD_v8.0_08_먹이그물.md",
            "archive/README.md", "../CLAUDE.md",
            "../unity/README.md", "../unity/CLAUDE.md",
            "../unity/PORTING_MAP.md", "../unity/THIRD_PARTY_NOTICES.md"]
for f in required:
    if not os.path.exists(os.path.join(DOCS, f)):
        fail(f"필수 문서 없음: {f}")

# 4+5. living 문서 스캔 (archive/ 제외)
stale = [r"전투 55종", r"[^0-9]74종", r"플레이어블 13종", r"아종 30종"]
oldpaths = [r"(?<!archive/v7\.12/)GDD/", r"docs/GDD/"]
for dirpath, dirnames, filenames in os.walk(DOCS):
    if "archive" in dirpath:
        continue
    for fn in filenames:
        if not fn.endswith(".md"):
            continue
        p = os.path.join(dirpath, fn)
        for i, line in enumerate(open(p), 1):
            for pat in stale:
                if re.search(pat, line):
                    fail(f"{os.path.relpath(p, ROOT)}:{i}: 구수치 잔재 [{pat}]")
            for pat in oldpaths:
                if re.search(pat, line) and not any(
                        k in line for k in ["archive", "구 ", "이전", "폐기", "역사"]):
                    fail(f"{os.path.relpath(p, ROOT)}:{i}: 구경로 참조 [{pat}]")

# 7. 04_영지 시뮬 블록 ↔ sim_economy.py 실측 동기화
# 04 §3.11 마일스톤 표(| N층 | ... | 골드 | ... |)를 문서에서 직접 파싱해 시뮬 baseline 재실행 결과와 대조.
# 양쪽 중 하나(문서 or 시뮬)만 바뀌면 FAIL — 시뮬 튜닝 시 04 표를 갱신하면 통과. 문서↔시뮬 드리프트 방지용.
SIM = os.path.join(DOCS, "_tools", "sim_economy.py")
DOC04 = os.path.join(DOCS, "GDD_v8.0_04_영지.md")
if os.path.exists(SIM) and os.path.exists(DOC04):
    try:
        out = subprocess.run([sys.executable, SIM], capture_output=True, text=True,
                             timeout=60, check=True).stdout
        # (a) 시뮬 baseline 마일스톤 파싱 — 로그 행: "  10    4     -2,165        50      142      313"
        #     baseline은 첫 시나리오 헤더(=앞의 75개 '=' 라인) 이후 시작 — 이후 시나리오 값으로 덮어쓰지 않게
        #     첫 등록값만 유지(setdefault). baseline이 항상 첫 시나리오라는 시뮬 출력 규약에 의존.
        saw_header = False
        log = {}
        for ln in out.splitlines():
            if re.fullmatch(r"=+", ln.strip()) and ln.strip():
                saw_header = True
                continue
            m2 = re.match(r"\s*(\d+)\s+\d+\s+(-?[\d,]+)\s", ln) if saw_header else None
            if m2:
                log.setdefault(int(m2.group(1)), int(m2.group(2).replace(",", "")))
        # (b) 04 문서 표 파싱 — 행: "| 10층 | 4 | **-2,165** | 50 | 142 | ... |" (마일스톤 표, 5열+비고)
        #     발견 1-2/1-3 비교표 행(A 시작 골드 5,000 등)은 'N층 |'로 시작하지 않아 자동 제외.
        doc_rows = {}
        for i, line in enumerate(open(DOC04), 1):
            m3 = re.match(r"\|\s*(\d+)층\s*\|\s*\d+\s*\|\s*\*{0,2}(-?[\d,]+)\*{0,2}\s*\|", line)
            if m3:
                fl = int(m3.group(1))
                if fl in doc_rows:
                    fail(f"04_영지:{i}: '| {fl}층 |' 행 중복 — 마일스톤 표 규약 위반")
                doc_rows[fl] = int(m3.group(2).replace(",", ""))
        if not doc_rows:
            fail("04_영지에서 마일스톤 표(| N층 | 일차 | 골드 | ...)을 찾지 못함 — 표 형식 변경 추정")
        # 필수 층 계약 — 값은 시뮬에서 동적으로 대조하되, 이 5개 행 자체가 사라지면 FAIL.
        # (10 파산점 · 25 S3 · 50 S4 최저 · 80 ★6 참고 · 100 종료 — 시뮬 마일스톤 구조를 바꿀 때만 수정)
        for fl in [10, 25, 50, 80, 100]:
            if fl not in doc_rows:
                fail(f"04_영지 마일스톤 표에서 {fl}층 행 누락 — 표 축소는 check_docs 필수 층 계약과 불일치")
        # (c) 대조
        for fl in sorted(doc_rows):
            want = doc_rows[fl]
            got = log.get(fl)
            if got is None:
                fail(f"sim_economy.py baseline에 {fl}층 마일스톤 없음 (문서 표에는 존재) — "
                     f"시뮬 출력 층 목록과 04 표 동기화 필요")
            elif got != want:
                fail(f"04_영지 시뮬 블록 드리프트: {fl}층 골드 문서 {want:,} vs 시뮬 실측 {got:,} — "
                     f"04 §3.11 마일스톤 표 갱신 또는 sim_economy.py 되돌림 필요")
    except subprocess.TimeoutExpired:
        fail("sim_economy.py 60초 초과")
    except subprocess.CalledProcessError as ex:
        fail(f"sim_economy.py 실행 실패 (exit {ex.returncode})")

if errors:
    print(f"FAIL ({len(errors)}건):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
n_all = len(m) + len(a)
print(f"OK — v8.0 정합 (JSON {len(m)}/{len(a)}/15/{len(e)}/{len(biomes)} · biomes 1~50/51~95/96~100 · 온도 {n_all}종 정합 · 필수문서 · 구수치/구경로 0건)")
