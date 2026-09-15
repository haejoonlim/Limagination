#!/usr/bin/env python3
"""신규 서식종 1차 배치 — 07 문서 §4 T-07-1.

인공 바이옴 16종을 ambient.json + ecology_codex.json에 추가.
리스킨 방식: 원본 종(deepcopy) → id/name/habitat/spawn/temperature 교체 (스탯·AI·패턴 유지).
온도 내성: 소속 바이옴 band 내에서 정의 (06 §3.5 검증 통과 보장).

실행: python3 design-docs/_tools/gen_new_species.py (soulcommander/ 기준, 멱등 — 재실행 시 교체)
"""
import copy
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "unity", "Assets", "Resources", "Data")

bi = json.load(open(os.path.join(DATA, "biomes.json")))["groups"]
CLIM = {}
for g in bi:
    for b in g["biomes"]:
        CLIM["biome_archive" if b["id"] == "biome_library" else b["id"]] = b["climate"]["band"]

# (신규 id, 이름, 원본 id, 역할, diet, 바이옴 코드, 온도 내성 [min,max], 근원자원, 노트)
NEW = [
    ("mon_windseedling_01", "바람모종", "mon_rabbit_01", "prey", "herbivore", "sky", [0, 15], "바람씨앗", "기류를 타고 떠다니는 모종 — 천공 먹이층의 바닥"),
    ("mon_stormbee_01", "폭풍꿀벌", "mon_bee_01", "swarm", "herbivore", "sky", [0, 15], "바람씨앗", "바람모종 꽂가루를 모은다"),
    ("mon_windmushroom_01", "바람버섯", "mon_fungus_01", "decomposer", "none", "sky", [-5, 10], "바람씨앗", "상승기류에 떠서 낙하물을 분해하는 부유 균류"),
    ("mon_stormhawk_01", "폭풍매", "mon_hawk_01", "hunter", "carnivore", "sky", [-10, 10], "—", "폭풍 꼭대기에서 벌·모종을 사냥"),
    ("mon_citypigeon_01", "도시비둘기", "mon_rabbit_01", "prey", "omnivore", "city", [5, 25], "시장 잔반", "미궁도시 대표 소음원 — 잔반을 먹고 번식"),
    ("mon_cockroach_01", "바퀴벌레", "mon_slime_blue_01", "decomposer", "omnivore", "sewer", [10, 30], "슬러지", "r전략종의 왕 — 도시·하수도 어디든"),
    ("mon_alleyrat_01", "골목쥐", "mon_rat_01", "prey", "omnivore", "city", [5, 25], "시장 잔반", "미궁도시·하수도 공유종"),
    ("mon_sewersnake_01", "하수뱀", "mon_snake_01", "ambusher", "carnivore", "sewer", [10, 25], "—", "수면 아래 매복 — 골목쥐·바퀴벌레 포식"),
    ("mon_templedove_01", "신전비둘기", "mon_rabbit_01", "prey", "herbivore", "temple", [8, 25], "성수 이슬", "성수를 마시고 살찌는 흰 비둘기"),
    ("mon_holymoss_01", "성수이끼", "mon_fungus_01", "decomposer", "none", "temple", [5, 25], "성수 이슬", "제단을 덮는 이끼 — 성수 이슬을 흡수"),
    ("mon_gardensnake_01", "가람뱀", "mon_snake_01", "ambusher", "carnivore", "temple", [8, 28], "—", "기둥 그늘에 매복해 비둘기 사냥"),
    ("mon_deepplankton_01", "심해플랑크톤", "mon_jellyfish_01", "swarm", "omnivore", "deep_ocean", [2, 12], "열수 미네랄", "심해 먹이사슬의 출발점 — 발광 군체"),
    ("mon_inkworm_01", "글자벌레", "mon_fungus_01", "decomposer", "omnivore", "library", [10, 22], "먹광", "책 표지·접착제를 먹는 해충 — 서고 생태의 바닥"),
    ("mon_papermoth_01", "종이나방", "mon_moth_01", "prey", "herbivore", "library", [8, 22], "먹광", "글자벌레를 먹는 나방"),
    ("mon_inkrat_01", "먹지쥐", "mon_rat_01", "prey", "omnivore", "library", [10, 25], "먹광", "먹광이 밴 페이지를 뜯어 먹는 쥐"),
    ("mon_inkcrow_01", "잉크까마귀", "mon_crow_01", "hunter", "carnivore", "library", [5, 20], "—", "책장 사이를 날아 다니며 나방·쥐를 사냥"),
    # ---- 2차 배치 18종 (T-07-2 · 2026-09-15) — G1 적응종 8 + 심연·지옥·정점·정글 10 ----
    ("mon_ruinspigeon_01", "비둘기", "mon_rabbit_01", "prey", "omnivore", "ruins", [2, 32], "저장고", "폐허 저장고를 쪼는 비둘기 — 잔량을 먹고 큰 무리를 이룬다"),
    ("mon_dustbug_01", "먼지벌레", "mon_bee_01", "swarm", "herbivore", "ruins", [2, 32], "저장고", "곡물 가루를 먹는 벌레 군체 — 저장고의 1차 소비자"),
    ("mon_tombworm_01", "무덤벌레", "mon_beetle_01", "prey", "herbivore", "graveyard", [-2, 25], "제물", "제물 음식을 먹는 딱정벌레 — 무덤 생태의 먹이 바닥"),
    ("mon_duskhawk_01", "어스름매", "mon_hawk_01", "hunter", "carnivore", "graveyard", [-2, 25], "—", "황혼에 무덤가를 선회 — 무덤벌레·쥐를 사냥"),
    ("mon_rockmoss_01", "바위이끼", "mon_fungus_01", "decomposer", "none", "mountain", [-20, 20], "고산초", "바위 표면을 덮는 이끼 — 고산초를 분해해 토양을 만든다"),
    ("mon_desertrat_01", "사막쥐", "mon_rat_01", "prey", "omnivore", "desert", [18, 45], "선인장", "선인장 즙으로 수분을 보충하는 사막의 쥐"),
    ("mon_carrionbeetle_01", "썩고기갑충", "mon_beetle_01", "decomposer", "omnivore", "desert", [18, 45], "썩은 고기", "사체를 분해하는 갑충 — 사막의 청소부"),
    ("mon_flameworm_01", "화염벌레", "mon_moth_01", "prey", "herbivore", "volcano", [40, 280], "열조류", "열수 파이프에 붙어 열조류를 뜯는 내열 유충"),
    ("mon_junglemonkey_01", "원숭이", "mon_rabbit_01", "prey", "omnivore", "jungle", [18, 38], "과실", "수관을 오르며 과실을 먹는 영장류 — 잡식"),
    ("mon_parrotswarm_01", "앵무떼", "mon_bee_01", "swarm", "herbivore", "jungle", [18, 38], "과실", "과실을 갈라 먹는 앵무새 군체 — 소란 포식"),
    ("mon_rotfungus_01", "부패균", "mon_fungus_01", "decomposer", "none", "jungle", [18, 38], "낙엽", "낙엽·과실 부스러기를 분해 — 정글 순환의 마침표"),
    ("mon_voidworm_01", "심연충", "mon_moth_01", "prey", "omnivore", "abyss", [-25, 20], "보이드 이슬", "보이드 이슬을 걸러 먹는 심연의 충 — 어둠 속 먹이 바닥"),
    ("mon_voidmoss_01", "보이드이끼", "mon_fungus_01", "decomposer", "none", "abyss", [-25, 20], "보이드 이슬", "심연 바위에 붙는 이끼 — 이슬을 응축해 군체를 부양"),
    ("mon_brimstonefly_01", "유황파리", "mon_bee_01", "swarm", "mineral", "hellscape", [80, 380], "유황", "유황 결정을 갉는 파리 군체 — 불열매를 수분 (공생)"),
    ("mon_fireberry_01", "불열매덩굴", "mon_vine_01", "prey", "mineral", "hellscape", [80, 380], "유황", "유황을 흡수해 매운 열매를 맺는 덩굴 — 유황파리가 수분"),
    ("mon_stardust_01", "별가루", "mon_bee_01", "swarm", "mana", "astral", [-35, 50], "근원 합류", "별빛이 응결한 가루 군체 — 정점 생태의 먹이 바닥"),
    ("mon_astralmoss_01", "아스트랄 이끼", "mon_fungus_01", "decomposer", "none", "astral", [-35, 50], "근원 합류", "정점 신전 바닥을 덮는 성역 이끼 — 흘러든 근원을 분해"),
    ("mon_cloudmoss_01", "구름이끼", "mon_fungus_01", "producer", "none", "astral", [-35, 50], "—", "구름을 짜는 이끼 — 해충(별가루)을 가두는 생산자 가안"),
]
assert len(NEW) == 34, f"1+2차 합계 34종 필요, 현재 {len(NEW)}"

# habitat 코드 → biome 접미사 (CLIM 키 조합용)
BIO_SUFFIX = {"city": "labyrinthcity", "library": "archive", "deep_ocean": "deepsea",
              "hellscape": "hell", "astral": "summit"}
# codex group 표기 — biomes.json gid 기준
GROUP_LABEL = {"g1": "G1 — 하부 탑", "g2": "G2 — 중부 탑", "g3": "G3 — 정점"}
BIO_GID = {}
for _g in bi:
    for _b in _g["biomes"]:
        BIO_GID["biome_archive" if _b["id"] == "biome_library" else _b["id"]] = _g["id"]

# 도시·하수도 공유종 (07 §4 — 도시 생태가 하수도로 흘러든다)
DUAL = {"mon_alleyrat_01": ["city", "sewer"], "mon_cockroach_01": ["sewer", "city"]}

apath = os.path.join(DATA, "ambient.json")
amb_doc = json.load(open(apath))
base_by_id = {s["id"]: s for s in amb_doc["ambient"]}
new_ids = {n[0] for n in NEW}
amb_doc["ambient"] = [s for s in amb_doc["ambient"] if s["id"] not in new_ids]
for nid, name, base, role, diet, hab, temp, res, note in NEW:
    s = copy.deepcopy(base_by_id[base])
    s["id"], s["name"] = nid, name
    s["spawn"]["floors"] = CLIM["biome_" + BIO_SUFFIX.get(hab, hab)]
    s["spawn"]["wave"] = ["world"]
    s["ecology"]["role"] = role
    s["ecology"]["diet"] = diet
    s["ecology"]["habitat"] = DUAL.get(nid, [hab])
    s["ecology"]["temperature"] = {"min": temp[0], "max": temp[1]}
    s["ecology"]["predators"] = []
    s["ecology"]["prey"] = [res] if res != "—" else []
    s["ecology"]["note"] = note
    amb_doc["ambient"].append(s)
amb_doc["meta"] = {"v80": "ambient/non-combat 19+16+18 (T-07-1 1차 · T-07-2 2차 2026-09-15)"}
with open(apath, "w", encoding="utf-8") as f:
    json.dump(amb_doc, f, ensure_ascii=False, indent=1)

epath = os.path.join(DATA, "ecology_codex.json")
codex = json.load(open(epath))
codex["entries"] = [e for e in codex["entries"] if e["id"] not in new_ids]
for nid, name, base, role, diet, hab, temp, res, note in NEW:
    fb = CLIM["biome_" + BIO_SUFFIX.get(hab, hab)]
    bid = "biome_" + BIO_SUFFIX.get(hab, hab)
    codex["entries"].append({
        "id": nid, "name": name, "floors": fb, "habitat": DUAL.get(nid, [hab]),
        "diet": diet, "role": role,
        "note": note,
        "temp": temp,
        "spawnBlock": (fb[0] - 1) // 5 + 1,
        "group": GROUP_LABEL[BIO_GID[bid]],
    })
codex["meta"] = {"v80": "ecology codex v1.2 - ambient 19+16+18 (T-07-1·T-07-2) · floors=참조 · 온도 내성 포함",
                 "source": "ambient.json ecology + biomes.json climate"}
with open(epath, "w", encoding="utf-8") as f:
    json.dump(codex, f, ensure_ascii=False, indent=1)

print(f"OK — 34종 (1차 16 + 2차 18): ambient {len(amb_doc['ambient'])}종 · codex {len(codex['entries'])}종")
