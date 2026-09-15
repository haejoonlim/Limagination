#!/usr/bin/env python3
"""v8.0 문서 정합 검증 — exit 0 = 준수.

검사:
  1. Data JSON 5종 파싱 + 개수 (monsters 54 / ambient 53 / races 15 / codex 53 / biomes 20)
  2. codex ID == ambient ID
  3. biomes: 20종 · 그룹 층 범위(1~50/51~95/96~100) · habitat 전부 매핑·중복 0 · 온도(climate band ↔ 종 내성 107종 교차, 면역 역할 제외)
  4. 필수 문서 존재
  5. living 문서에 구수치 정본 주장 잔재 (전투 55종 / 74종 / 플레이어블 13종 / 아종 30종)
  6. living 문서에 구경로 참조 (design-docs/GDD/ · docs/GDD/ — archive/ 제외)

실행: python3 design-docs/_tools/check_docs.py (soulcommander/ 기준)
"""
import json
import os
import re
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
            "GDD_v8.0_03_개발플랜.md",
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

if errors:
    print(f"FAIL ({len(errors)}건):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
n_all = len(m) + len(a)
print(f"OK — v8.0 정합 (JSON {len(m)}/{len(a)}/15/{len(e)}/{len(biomes)} · biomes 1~50/51~95/96~100 · 온도 {n_all}종 정합 · 필수문서 · 구수치/구경로 0건)")
