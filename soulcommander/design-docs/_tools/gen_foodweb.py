#!/usr/bin/env python3
"""복합 먹이 그물 1차 실행 — 08 문서 T-08-1~5 (2026-09-15 승인본).

T-08-1  전역 자원 corpse·soul·mana — 분해자·청소부 + 언데드·정령(미정N 승인)
T-08-2  서식종 34종 간선 부여 — 근원자원 + 바이옴 내 포식 관계
T-08-3  predators/prey 비대칭 전수 쌍방 정합
T-08-4  전투몬 생물 사슬 편입 (관계만 공유 — 미정M 승인, 개체수 비연동)
T-08-5  relationTypes 필드 — 모든 prey 간선에 관계 유형 태깅
        (predation 포식 / scavenge 청소·사체 / ether 에테르·영혼·마력 /
         parasitism 기생 — 예약 / grazing 근원자원 섭취)

관계 유형 판정 규칙 (rel_type_for — 08 §4):
  soul·mana 섭취          → ether    (에테르 경로, 미정N)
  corpse + 분해·청소 역할 → scavenge (① 청소 경로)
  corpse + 그 외 역할     → ether    (언데드의 사체 흡수, 08 §5.1)
  detritus (골렘)        → scavenge (사체 경로 계열 — 무기물)
  피식자가 종(id)        → predation (기본)
  그 외 자원             → grazing (② 근원자원 섭취)

relationTypes는 prey와 1:1 대응 사전({피식자id|자원명: 유형}) — check_docs가
완전 태깅·무효값·stale 키를 상시 검증. 멱등 — 재실행해도 같은 결과.
실행 후 gen_ecology_codex.py로 도감 재생성.
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
ETHER_RES = {"soul", "mana"}            # 에테르 경로 자원 (미정N)

def habitats(s):
    return set(s["ecology"].get("habitat") or [])

def res_for(s):
    for h in habitats(s):
        if h in BIO_RES:
            return BIO_RES[h]
    return None

def rel_type_for(eater, item):
    """먹는 종 + 먹힘 항목 → 관계 유형 (08 §4 판정 규칙 — docstring 참조)."""
    if item in ETHER_RES:
        return "ether"
    role = eater["ecology"]["role"]
    if item == "corpse":
        return "scavenge" if role in ("decomposer", "scavenger") else "ether"
    if item == "detritus":
        return "scavenge"
    if item in by_id:
        return "predation"
    return "grazing"

def add_prey(s, item):
    """prey에 추가 (중복 방지). species id 또는 자원 문자열."""
    lst = s["ecology"].setdefault("prey", [])
    if item not in lst:
        lst.append(item)
        return True
    return False

def tag_prey(s, item, rtype=None):
    """prey 추가 + relationTypes 태깅 (rtype=None이면 규칙으로 자동 판정)."""
    add_prey(s, item)
    want = rtype or rel_type_for(s, item)
    rt = s["ecology"].setdefault("relationTypes", {})
    if rt.get(item) != want:
        rt[item] = want
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
        if tag_prey(s, "corpse"):
            changed += 1
    if s["name"] in ETHER:
        for r in ETHER[s["name"]]:
            if tag_prey(s, r):
                changed += 1

# ── T-08-2: 서식종 근원자원 + 바이옴 내 포식 관계 ───────────────
# 2-a) prey가 완전히 빈 종(생물 역할) → 소속 바이옴 근원자원 부여
for s in all_sp:
    if s["ecology"]["role"] in EXCLUDE_ROLES:
        continue
    if not (s["ecology"].get("prey") or []):
        r = res_for(s)
        if r and tag_prey(s, r):
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
        if tag_prey(pred, q["id"]):
            changed += 1
        wired += 1

# 골렘류 — detritus(무기물) 섭취
for s in mon:
    if "골렘" in s["name"]:
        if tag_prey(s, "detritus"):
            changed += 1
# 스톰 자이언트 — 뇌전(mana)
for s in mon:
    if s["name"] == "스톰 자이언트":
        if tag_prey(s, "mana"):
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

# ── T-08-5: relationTypes 정규화 — 태그 없는 간선(원본 데이터·쌍방 보정분) 전수 재분류 ──
# add 시점 태그와 무관하게 "최종 데이터 상태"에서 규칙 재판정 — 멱등 + 규칙 일원화.
# prey에 없는 stale 태그도 정리.
n_tag = 0
for s in all_sp:
    prey_list = s["ecology"].get("prey") or []
    rt = s["ecology"].get("relationTypes")
    if rt and not prey_list:
        s["ecology"]["relationTypes"] = {}
        changed += 1
        continue
    if not prey_list:
        continue
    rt = s["ecology"].setdefault("relationTypes", {})
    for item in prey_list:
        want = rel_type_for(s, item)
        if rt.get(item) != want:
            rt[item] = want
            n_tag += 1
    for k in [k for k in rt if k not in prey_list]:
        del rt[k]
changed += n_tag

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

# T-08-5 — 관계 유형 분포 + 완전 태깅 확인
type_count = {}
for s in all_sp:
    for t in (s["ecology"].get("relationTypes") or {}).values():
        type_count[t] = type_count.get(t, 0) + 1
print("relationTypes 분포:", dict(sorted(type_count.items(), key=lambda x: -x[1])))
untagged = sum(1 for s in all_sp for x in (s["ecology"].get("prey") or [])
               if x not in (s["ecology"].get("relationTypes") or {}))
print(f"미태그 간선: {untagged}")
