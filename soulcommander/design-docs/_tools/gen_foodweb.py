#!/usr/bin/env python3
"""복합 먹이 그물 1차 실행 — 08 문서 T-08-1~4 (2026-09-15 승인본).

T-08-1  전역 자원 corpse·soul·mana — 분해자·청소부 + 언데드·정령(미정N 승인)
T-08-2  서식종 34종 간선 부여 — 근원자원 + 바이옴 내 포식 관계
T-08-3  predators/prey 비대칭 전수 쌍방 정합
T-08-4  전투몬 생물 사슬 편입 (관계만 공유 — 미정M 승인, 개체수 비연동)

멱등 — 재실행해도 같은 결과. 실행 후 gen_ecology_codex.py로 도감 재생성.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "unity", "Assets", "Resources", "Data")

mon_f = os.path.join(DATA, "monsters.json")
amb_f = os.path.join(DATA, "ambient.json")
mon = json.load(open(mon_f))["monsters"]
amb = json.load(open(amb_f))["ambient"]
all_sp = mon + amb
by_id = {s["id"]: s for s in all_sp}
name_map = {}
for s in all_sp:
    name_map.setdefault(s["name"], []).append(s)

# 바이옴 habitat → 대표 근원자원 (도감 RESOURCES의 평문명 — 기존 데이터가 쓰는 표기)
BIO_RES = {
    "grassland": "햇빛·풀", "plains": "햇빛·풀", "meadow": "햇빛·풀",
    "forest": "도토리·숲열매", "swamp": "수생식물", "river": "수생식물",
    "cave": "구아노", "mine": "구아노", "underground": "구아노", "fungus": "균류",
    "ruins": "버려진 식량 저장고", "graveyard": "제물·향유 잔여",
    "mountain": "고산초", "tundra": "고산초", "ice_cave": "고산초",
    "desert": "선인장 즙", "volcano": "열조류", "coast": "플랑크톤·해조",
    "deepsea": "열수 분출구 미네랄", "sky": "바람씨앗",
    "dungeon": "시장 잔반", "city": "시장 잔반", "castle": "시장 잔반", "tower": "시장 잔반",
    "sewer": "슬러지", "temple": "성수 이슬", "jungle": "과실·수액",
    "abyss": "보이드 이슬", "hell": "유황 분출물",
    "archive_ink": "먹광", "summit_src": "근원 합류",
    "astral": "근원 합류", "dragon_lair": "근원 합류", "lair": "근원 합류",
    "library": "먹광",  # 서고(구 대도서관) habitat
}
EXCLUDE_ROLES = {"elemental", "mimic"}  # 그물 밖 원칙 (08 §5.3)

def habitats(s):
    return set(s["ecology"].get("habitat") or [])

def res_for(s):
    for h in habitats(s):
        if h in BIO_RES:
            return BIO_RES[h]
    return None

def add_prey(s, item):
    """prey에 추가 (중복 방지). species id 또는 자원 문자열."""
    lst = s["ecology"].setdefault("prey", [])
    if item not in lst:
        lst.append(item)
        return True
    return False

def add_pred(s, pid):
    lst = s["ecology"].setdefault("predators", [])
    if pid not in lst:
        lst.append(pid)
        return True
    return False

def resolve_pair(pred, prey_name):
    """이름으로 피식자 후보 → 서식지 겹치는 개체 우선."""
    cands = name_map.get(prey_name) or []
    if not cands:
        return None
    ph = habitats(pred)
    for c in cands:
        if c["id"] != pred["id"] and habitats(c) & ph:
            return c
    return cands[0]

changed = 0

# ── T-08-1: 전역 자원 ──────────────────────────────────────────
ETHER = {  # 이름 → 섭취 자원 (08 §5.1, 미정N 승인)
    "좀비": ["corpse"], "스켈레톤": ["corpse"], "스켈레톤 워리어": ["corpse"],
    "스켈레톤 야차": ["corpse", "soul"], "오우즈": ["corpse"],
    "리치": ["soul", "mana"], "밴시": ["soul"],
    "스켈레톤 메이지": ["soul", "mana"],
    "수호령": ["mana"], "아아시마르": ["mana"], "드레드노트": ["mana"],
}
for s in all_sp:
    role = s["ecology"]["role"]
    if role in ("decomposer", "scavenger"):
        if add_prey(s, "corpse"):
            changed += 1
    if s["name"] in ETHER:
        for r in ETHER[s["name"]]:
            if add_prey(s, r):
                changed += 1

# ── T-08-2: 서식종 근원자원 + 바이옴 내 포식 관계 ───────────────
# 2-a) prey가 완전히 빈 종(생물 역할) → 소속 바이옴 근원자원 부여
for s in all_sp:
    if s["ecology"]["role"] in EXCLUDE_ROLES:
        continue
    if not (s["ecology"].get("prey") or []):
        r = res_for(s)
        if r and add_prey(s, r):
            changed += 1

# 2-b) 포식 관계 (이름 기반 — 존재하는 종만, 멱등)
CHAINS = [
    # (포식자 이름, [피식자 이름]) — 전투몬 포함, 관계만 공유(미정M)
    ("잉크까마귀", ["먹지쥐", "종이나방"]),
    ("가람뱀", ["신전비둘기"]),
    ("하수뱀", ["골목쥐", "바퀴벌레"]),
    ("폭풍매", ["바람모종", "폭풍꿀벌"]),   # 송곳매(미구현) → 폭풍매 대체
    ("어스름매", ["무덤벌레"]),
    ("유안티", ["원숭이"]),
    ("마녀 해파리", ["심해플랑크톤"]),      # 여과 섭식 (심해조개 미구현 대체)
    ("산호초", ["심해플랑크톤"]),           # 산호 여과 섭식 — 폴리프가 플랑크톤 포획
    ("맹독 전갈", ["사막쥐"]),
    ("전갈", ["사막쥐"]),
    # 도플갱어(미믹)는 그물 밖 — 매복형 니치, 관계 없음 유지 (08 §5.3)
    # T-08-4: 전투몬 생물 사슬 편입
    ("거대 곰", ["바위이끼"]),
    ("크라켄 촉수", ["거대 게"]),           # 정점 — 심해 갑각류 섭취
    ("발록", ["유황파리"]),
    ("헬 하운드", ["불열매덩굴"]),
    ("거미 여왕", ["먼지벌레"]),
]
wired, skipped = 0, []
for pred_name, preys in CHAINS:
    cands = name_map.get(pred_name)
    if not cands:
        skipped.append(pred_name)
        continue
    pred = cands[0]
    for py in preys:
        q = resolve_pair(pred, py)
        if q is None:
            skipped.append(f"{pred_name}→{py}")
            continue
        if add_prey(pred, q["id"]):
            changed += 1
        wired += 1

# 골렘류 — detritus(무기물) 섭취
for s in mon:
    if "골렘" in s["name"]:
        if add_prey(s, "detritus"):
            changed += 1
# 스톰 자이언트 — 뇌전(mana)
for s in mon:
    if s["name"] == "스톰 자이언트":
        if add_prey(s, "mana"):
            changed += 1

# ── T-08-3: 쌍방 정합 ──────────────────────────────────────────
def symmetrize():
    n = 0
    for s in all_sp:
        for pid in s["ecology"].get("predators") or []:
            p = by_id.get(pid)
            if p and add_prey(p, s["id"]):
                n += 1
    for p in all_sp:
        for x in p["ecology"].get("prey") or []:
            q = by_id.get(x)
            if q and add_pred(q, p["id"]):
                n += 1
    return n

asym_before = sum(
    1 for s in all_sp for pid in (s["ecology"].get("predators") or [])
    if pid in by_id and s["id"] not in (by_id[pid]["ecology"].get("prey") or []))
fixed = symmetrize()

# ── 저장 ───────────────────────────────────────────────────────
json.dump({"monsters": mon}, open(mon_f, "w"), ensure_ascii=False, indent=2)
json.dump({"ambient": amb}, open(amb_f, "w"), ensure_ascii=False, indent=2)

# ── 메트릭 ─────────────────────────────────────────────────────
edges = len({(p["id"], x) for p in all_sp for x in p["ecology"].get("prey") or [] if x in by_id})
asym_after = sum(
    1 for s in all_sp for pid in (s["ecology"].get("predators") or [])
    if pid in by_id and s["id"] not in (by_id[pid]["ecology"].get("prey") or []))
orphans = [s["id"] for s in all_sp
           if not (s["ecology"].get("prey") or []) and not (s["ecology"].get("predators") or [])
           and s["ecology"]["role"] not in EXCLUDE_ROLES]

print(f"변경 항목 {changed} · 포식 관계 시도 {wired} · 스킵 {len(skipped)}")
if skipped:
    print("  스킵 목록:", skipped)
print(f"비대칭: {asym_before} → {asym_after} (쌍방 보정 {fixed})")
print(f"종간 간선: 64 → {edges}")
print(f"고아종(생물): {len(orphans)} {orphans[:8]}")
