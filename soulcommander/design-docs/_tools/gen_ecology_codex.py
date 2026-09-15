#!/usr/bin/env python3
"""생태 도감 HTML 생성기 v2 — 사전형 UI (탭 · 표제어 검색 · 초성 색인 · 상세 팝업 · 상호참조).

실행: python3 design-docs/_tools/gen_ecology_codex.py (soulcommander/ 기준)
출력: design-docs/생태도감.html (정적 1파일 · 인터넷 불필요)

UI 원칙 (07 문서 §10):
  1. 중요도 순 — 종사전(기본) → 바이옴 → 개념 → 시뮬레이터
  2. 사전식 — 표제어 검색 · 가나다 초성 색인 · 항목 클릭 시 상세 팝업
  3. 상호참조 — 먹이·천적을 클릭하면 해당 표제어로 이동
  4. 접이식 — 개념·바이옴 카드는 한 줄 요약만 기본 표시
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "unity", "Assets", "Resources", "Data")
OUT = os.path.join(ROOT, "design-docs", "생태도감.html")

bi = json.load(open(os.path.join(DATA, "biomes.json")))[ "groups"]
amb = json.load(open(os.path.join(DATA, "ambient.json")))["ambient"]
mon = json.load(open(os.path.join(DATA, "monsters.json")))["monsters"]

# T-07-5 서고 개명(가안) — 데이터는 아직 biome_library이므로 여기서 정규화 (07 §5.1)
CLIM, BNAME = {}, {}
for g in bi:
    for b in g["biomes"]:
        bid = "biome_archive" if b["id"] == "biome_library" else b["id"]
        CLIM[bid] = b["climate"]
        BNAME[bid] = b["name"]
HAB2BIO = {}
for bid, _ in [(k, k) for k in BNAME]:
    pass
for g in bi:
    for b in g["biomes"]:
        bid = "biome_archive" if b["id"] == "biome_library" else b["id"]
        for h in b["habitat"]:
            HAB2BIO[h] = bid
BIOME_NAMES = {bid: ("서고 (구 대도서관)" if bid == "biome_archive" else BNAME[bid]) for bid in BNAME}

ROLE_KO = {
    "prey": "먹이", "swarm": "군체", "hunter": "사냥꾼", "predator": "포식자",
    "ambusher": "매복자", "apex": "최상위", "scavenger": "청소부",
    "decomposer": "분해자", "corruptor": "오염자", "guardian": "수호자",
    "undead": "언데드", "mimic": "의태자", "elemental": "정령", "warrior": "전사",
    "producer": "생산자",
}
GROUP_KO = {"g1": "G1 하부", "g2": "G2 중부", "g3": "G3 정점"}
DIET_KO = {"herbivore": "초식", "carnivore": "육식", "omnivore": "잡식", "none": "비섭취",
           "mana": "마력", "blood": "흡혈", "mineral": "광물", "soul": "영혼", "brain": "뇌"}
KIND_KO = {"amb": "야생", "mon": "전투", "plan": "예정"}

# 예정 신규종 — 전부 1·2차 배치 완료 (2026-09-15, T-07-1·T-07-2) → 실데이터 ambient.json 53종으로 표시됨
PLANNED = {}

RESOURCES = {
    "biome_plains": ("햇빛·풀", "1차 생산의 원형 — 탑 생태의 시작점", 140, 1.2),
    "biome_forest": ("도토리·숲열매", "풍년 주기가 개체수 진동을 만든다", 120, 1.0),
    "biome_swamp": ("수생식물·유기물 침전", "천천히 쌓이고 천천히 썩는다", 90, 0.7),
    "biome_cave": ("균류·박쥐 분변(구아노)", "지하 생태의 유일한 에너지 입구", 80, 0.6),
    "biome_ruins": ("버려진 식량 저장고", "인간의 잔재가 생태를 부양", 70, 0.8),
    "biome_graveyard": ("제물·향유 잔여", "작고 고정적인 자원 — 개체수 한계 명확", 40, 0.4),
    "biome_mountain": ("고산초·지이끼", "성장이 느린 극한 자원", 60, 0.5),
    "biome_desert": ("선인장 즙·이슬", "희소 자원 — K가 낮아 개체수 폭락·폭등 반복", 35, 0.5),
    "biome_volcano": ("열조류(熱藻類)·광물 이온", "열수에만 사는 특화 생산자", 50, 0.6),
    "biome_coast": ("플랑크톤·해조", "조류(潮流)가 자원을 계속 새로 보낸다", 110, 1.0),
    "biome_deepsea": ("열수 분출구 미네랄", "햇빛 없는 화학합성 생태 — 섬생물지리학의 극단", 65, 0.5),
    "biome_sky": ("바람씨앗", "상승기류가 띄워 보내는 떠다니는 자원", 55, 0.7),
    "biome_labyrinthcity": ("시장 잔반", "도시가 흘려보내는 근원자원 — 풍요롭지만 불규칙", 85, 0.9),
    "biome_sewer": ("슬러지", "버려진 음식물 찌꺼기 — r전략종의 천국", 95, 1.1),
    "biome_temple": ("성수 이슬", "제단에 맺히는 마력 응결 — 소량·고품질", 45, 0.5),
    "biome_jungle": ("과실·수액", "사계절 풍부 — 다층 구조로 니치 분화 극대화", 130, 1.1),
    "biome_abyss": ("보이드 이슬", "심연에서 응결하는 알 수 없는 근원", 50, 0.4),
    "biome_hell": ("유황 분출물", "화염 생태의 에너지원 — 독성 강해 특화종만 섭취", 60, 0.6),
    "biome_archive": ("먹광(墨光)", "책의 잉크·표지가 빛내는 마력 찌꺼기", 55, 0.6),
    "biome_summit": ("근원 합류", "탑 전체 근원자원이 흘러모이는 정점", 70, 0.5),
}

NOTES = {
    "biome_plains": "야생종 19종의 요충지 — 탑 전체 사슬(통로 37개)의 중심 허브.",
    "biome_forest": "니치 분화의 모범 — 6개 역할이 공존하는 가장 풍요로운 층.",
    "biome_swamp": "물가를 타고 숲·동굴·연해와 통하는 생태 회랑.",
    "biome_cave": "박쥐 분변 하나가 전체 사슬을 떠받치는 지하 순환의 교과서.",
    "biome_ruins": "청소부(까마귀·쥐)가 왕이 된 층 — 먹이는 저장고가 대신한다.",
    "biome_graveyard": "자원이 적어 개체수가 항상 K 근처 아래 — 사냥감이 귀한 곳.",
    "biome_mountain": "사냥꾼(매)은 산맥과 초원을 오가며 두 사슬을 연결한다.",
    "biome_desert": "K가 가장 낮은 층 — 개체수 붕괴·회복을 눈으로 볼 수 있는 사슬.",
    "biome_volcano": "열에 특화된 분해자(레드 슬라임)가 자원을 다시 흘려보낸다.",
    "biome_coast": "조류가 자원을 계속 공급 — 폐쇄 바이옴과 다른 열린 사슬.",
    "biome_deepsea": "햇빛 대신 열수 분출구 — 화학합성 생태 (10% 법칙이 극한으로 작동).",
    "biome_sky": "떠다니는 씨앗을 놓고 벌·매가 경쟁 — 높이 곤충이 지배한다.",
    "biome_labyrinthcity": "잔반 = 근원자원. 골목쥐·바퀴벌레의 도시 생태가 전부 여기서 시작.",
    "biome_sewer": "r전략종의 천국 — 바퀴벌레 군체가 폭발적으로 회복되는 층.",
    "biome_temple": "수호자(가디언)는 사슬 밖 존재 — 사냥하지 않고 지킨다.",
    "biome_jungle": "다층 숲이 만든 니치 폭발 — 같은 나무에 3개의 사슬이 산다.",
    "biome_abyss": "포식자만 있는 위험한 구조 — 먹이 충(심연충) 추가가 생존의 열쇠.",
    "biome_hell": "유황파리 군체가 불열매를 수분하는 공생 구조 (가안).",
    "biome_archive": "글자벌레→종이나방→잉크까마귀 — 인공 바이옴 생태의 대표 사례.",
    "biome_summit": "영양급위의 정점 — 최상위 포식자 하나가 전층 개체 균형을 좌우한다.",
}

PREY_R = {"prey", "swarm", "producer"}
PRED_R = {"predator", "hunter", "ambusher", "apex"}
DEC_R = {"decomposer", "scavenger", "corruptor"}

# ---------- 바이옴 카드 데이터 ----------
biomes = []
for g in bi:
    for b in g["biomes"]:
        bid = "biome_archive" if b["id"] == "biome_library" else b["id"]
        H = set(b["habitat"])
        cur = []
        for s in amb:
            if H & set(s["ecology"]["habitat"]):
                cur.append({"n": s["name"], "r": s["ecology"]["role"], "p": False})
        for m in mon:
            if H & set(m["ecology"]["habitat"]):
                cur.append({"n": m["name"], "r": m["ecology"]["role"], "p": False})
        for n, r, src, t in PLANNED.get(bid, []):
            cur.append({"n": n, "r": r, "p": True, "src": src, "tier": t})
        roles = {c["r"] for c in cur}
        miss = []
        if not roles & PREY_R: miss.append("먹이")
        if not roles & PRED_R: miss.append("포식")
        if not roles & DEC_R: miss.append("분해")
        res = RESOURCES[bid]
        cl = b.get("climate", {"ambient": 15, "base": 18, "band": [0, 35]})
        biomes.append({
            "id": bid, "gid": g["id"], "gname": GROUP_KO[g["id"]],
            "tempS": f"🌡 {cl['ambient']}°C (band {cl['band'][0]}~{cl['band'][1]}°C)",
            "cl": [cl["ambient"], cl["band"][0], cl["band"][1]],
            "name": "서고 (구 대도서관)" if bid == "biome_archive" else b["name"],
            "slots": b["slots"], "mult": b["difficulty"]["mult"],
            "habitat": b["habitat"], "species": cur,
            "complete": not miss, "missing": miss,
            "resName": res[0], "resDesc": res[1], "K": res[2], "r": res[3],
            "note": NOTES[bid],
            "curN": sum(1 for c in cur if not c["p"]), "planN": sum(1 for c in cur if c["p"]),
        })

# ---------- 종사전 데이터 (사전형 엔트리) ----------
name_by_id = {s["id"]: s["name"] for s in amb}
name_by_id.update({m["id"]: m["name"] for m in mon})

def resolve(refs):
    out = []
    for x in refs or []:
        if x in name_by_id:
            out.append({"n": name_by_id[x], "id": x})
        else:
            out.append({"n": x, "id": None})
    return out

def biome_names(habs):
    seen, out = set(), []
    for h in habs:
        bid = HAB2BIO.get(h)
        if bid and bid not in seen:
            seen.add(bid); out.append(BIOME_NAMES[bid])
    return out

species = []
for s in amb:
    ec = s["ecology"]
    t = ec.get("temperature") or {}
    note = ec.get("note") or f"{ROLE_KO[ec['role']]}형 · 식성 {DIET_KO.get(ec.get('diet'), ec.get('diet','?'))}."
    species.append({"id": s["id"], "name": s["name"], "k": "amb", "tier": None,
                    "r": ec["role"], "d": ec.get("diet", "none"),
                    "bio": biome_names(ec["habitat"]), "floors": s["spawn"]["floors"],
                    "temp": [t.get("min"), t.get("max")] if t else None,
                    "stats": s.get("stats"), "el": None, "note": note,
                    "pred": resolve(ec.get("predators")), "prey": resolve(ec.get("prey")),
                    "eco": {"rep": ec.get("reproduction", 0.6), "food": ec.get("food_need", 0.4),
                            "agg": ec.get("aggression", 0.3), "soc": ec.get("sociality", 0.5)}})
for m in mon:
    ec = m["ecology"]
    t = ec.get("temperature") or {}
    note = ec.get("note") or f"{ROLE_KO[ec['role']]}형 전투 몬스터 (T{m.get('tier','?')}) · 식성 {DIET_KO.get(ec.get('diet'), ec.get('diet','?'))}."
    species.append({"id": m["id"], "name": m["name"], "k": "mon", "tier": m.get("tier"),
                    "r": ec["role"], "d": ec.get("diet", "none"),
                    "bio": biome_names(ec["habitat"]), "floors": m["spawn"]["floors"],
                    "temp": [t.get("min"), t.get("max")] if t else None,
                    "stats": m.get("stats"), "el": m.get("element"), "note": note,
                    "pred": resolve(ec.get("predators")), "prey": resolve(ec.get("prey")),
                    "eco": {"rep": ec.get("reproduction", 0.5), "food": ec.get("food_need", 0.4),
                            "agg": ec.get("aggression", 0.4), "soc": ec.get("sociality", 0.5)}})
for bid, lst in PLANNED.items():
    band = CLIM[bid]["band"]
    for n, r, src, t in lst:
        pid = "plan_" + n
        species.append({"id": pid, "name": n, "k": "plan", "tier": None, "r": r, "d": None,
                        "bio": [BIOME_NAMES[bid]], "floors": band,
                        "temp": None, "stats": None, "el": None,
                        "note": f"예정 신규종 — {src}. 2차 배치 대상 (07 §4).",
                        "pred": [], "prey": []})

# 중요도: 전투(T높은순) > 야생 > 예정 — 가나다 토글로 변경 가능
def imp(s):
    return 200 + (s["tier"] or 0) * 10 if s["k"] == "mon" else (100 if s["k"] == "amb" else 0)
species.sort(key=lambda s: (-imp(s), s["name"]))

# 생태 통로 (공유종 기반 엣지 수)
edges = 0
for i, x in enumerate(biomes):
    for y in biomes[i + 1:]:
        Hx, Hy = set(x["habitat"]), set(y["habitat"])
        if any(set(s["ecology"]["habitat"]) & Hx and set(s["ecology"]["habitat"]) & Hy for s in amb + mon):
            edges += 1

data = {"biomes": biomes, "edges": edges, "species": species,
        "nAmb": len(amb), "nMon": len(mon), "nPlan": sum(len(v) for v in PLANNED.values()),
        "nSp": len(species)}

# ---------- 개념 사전 (22개 · 접이식) ----------
CONCEPTS = [
    ("로지스틱 성장", "Logistic Growth", "dN/dt = r·N·(1−N/K)",
     "개체수가 처음엔 폭발적으로 늘다가, 환경 한계에 가까워지면 성장이 멈추는 <b>S자 곡선</b>. 자연의 개체수 증가는 거의 항상 이 모양.",
     "바이옴별 <b>개체수 상한</b> — 스폰 캡과 사냥 개체수 조절의 기본식. 하단 시뮬레이터의 초록 선이 이 곡선."),
    ("수용력", "Carrying Capacity (K)", "K = 자원 등급 × 공간 크기",
     "그 환경이 먹여 살릴 수 있는 최대 개체수. K를 넘으면 기아로 개체수가 다시 떨어진다.",
     "근원자원 풍요도 → 바이옴별 K. 사막(K 35)과 정글(K 130)의 체감 차이가 여기서 나온다."),
    ("로트카-볼테라", "Lotka-Volterra", "dN/dt = rN(1−N/K) − aNP<br>dP/dt = baNP − dP",
     "포식자와 피식자의 개체수가 서로 물고 물리며 <b>주기적 파동</b>을 만드는 모델. 토끼가 늘면 여우가 늘고, 여우가 늘면 토끼가 줄고.",
     "<b>조우율·사냥 가치의 시간 변화</b> — 시즌마다 사냥감이 많은 층/적은 층이 달라지는 이유. 시뮬레이터의 빨강·초록 파동."),
    ("영양 단계 · 10% 법칙", "Trophic Levels · 10% Rule", "먹이 10 → 포식 1",
     "에너지는 단계가 올라갈수록 약 1/10만 전달된다. 그래서 최상위 포식자는 항상 소수.",
     "스폰 테이블 비율 설계 — 먹이 10 : 포식 1. 서고 카드의 4종 사슬 배분도 이 법칙을 따름."),
    ("영양급위", "Trophic Cascade", "상위 제거 → 하위 폭발",
     "최상위 포식자가 사라지면 그 아래 단계가 연쇄적으로 폭발하거나 붕괴한다. (옐로스톤 늑대 복귀 사례)",
     "<b>보스 처치 후 2~3시즌 하위종 폭증 이벤트</b> — 사냥 보너스·생태 변동으로 연결 가능."),
    ("섬생물지리학", "Island Biogeography", "종수 ∝ 면적 · 연결도",
     "섬이 클수록, 본토와 가까울수록 더 많은 종이 산다. 작고 고립된 섬은 종수가 적다.",
     "<b>5층 블록 = 섬</b>. 근원자원 K가 곧 면적, 생태 통로(공유종)가 곧 거리 — 통로 37개로 탑 전체가 하나로 연결."),
    ("니치 분화 · 경쟁 배제", "Niche · Competitive Exclusion", "같은 자리 · 같은 먹이 → 한 종만 생존",
     "완전히 같은 역할을 하는 두 종은 공존할 수 없다. 그래서 종들은 각자 다른 자리를 만든다(니치 분화).",
     "<b>바이옴당 역할 중복 금지</b> — 신규종 habitat 단일 원칙의 근거. 같은 먹이를 노리는 종은 먹이를 나눠 먹도록 설계."),
    ("r/K 전략", "r/K Selection", "r전략: 많이 낳고 빨리 늘어<br>K전략: 적게 낳고 크게 산다",
     "벌레·쥐 같은 r전략종은 개체수 회복이 빠르고, 용·곰 같은 K전략종은 느리지만 한 마리가 강하다.",
     "swarm 계열은 사냥해도 금방 채워지고(하수도), apex는 한 번 잡으면 오래 비어 있다(정점) — 사냥 경제의 밸런스 축."),
    ("생태 천이", "Ecological Succession", "빈 땅 → 풀 → 덤불 → 숲",
     "교란(화재 등)으로 생태가 무너져도 정해진 순서로 서서히 회복된다.",
     "<b>리셋 주기 직후의 바이옴 재생 단계</b> — 갓 열린 층은 먹이종만 있고 포식자는 나중에 돌아온다 (미정J와 연결)."),
    ("핵심종 · 지표종", "Keystone · Indicator Species", "핵심종: 생태를 떠받치는 종<br>지표종: 건강도를 알리는 종",
     "핵심종 하나의 부재가 생태 전체를 바꾼다. 지표종의 개체수로 생태 건강 상태를 알 수 있다.",
     "<b>쥐 = 지표종</b> (개체수 = 층 건강 게이지) · <b>정점 보스 = 핵심종</b> — 도감에 생태 역할 표기"),
    ("침입종", "Invasive Species", "천적 없는 종의 폭발",
     "천적 없이 들어온 종은 로지스틱의 브레이크 없이 폭발한다.",
     "과거 <b>31~75층 데드존 사례</b> — 포식자 없는 밴드의 위험. check_docs 역할 검사가 방지 장치."),
    ("영양물질 순환", "Nutrient Cycling", "사체 → 분해자 → 자원",
     "죽은 것은 분해자를 거쳐 다시 근원자원이 된다. 순환이 끊기면 생태도 끊긴다.",
     "<b>처치 사체 → 분해자 부스트</b> (v7.12 검증 완료 역학 승계안) — 사냥이 바이옴 자원에 미치는 영향."),
    ("기능반응 곡선", "Holling's Functional Response", "타입 II: 포화형 / 타입 III: S형",
     "사냥감이 많아져도 포식자의 포식 속도엔 한계가 있다(포화). 타입 III은 사냥감이 적을 때 잘 안 잡다가 일정 수를 넘으면 폭발적으로 잡는다 — 피식자 멸종 방지 장치.",
     "<b>사냥 피로도·자동 사냥 효율 캡</b> — 밀도가 낮은 층에서 무한사냥 방지. AI 몬스터 포식 속도에도 동일 적용. (06 §3.5 온도와 결합 시 계절별 사냥 효율 변동)"),
    ("온도 의존성 · 열성능 곡선", "Thermal Performance Curve", "최적 온도 T_opt에서 성능 최대 — 멀어질수록 급락",
     "모든 생물은 잘 활동하는 온도가 정해져 있고, 최적점에서 벗어날수록 활동 능력이 급격히 떨어진다.",
     "<b>종별 온도 내성(min~max) 필드</b> — 이미 73종 전종에 존재. 바이옴 band 밖 종은 스폰 게이트에서 차단 (06 §3.5)."),
    ("베르그만 법칙", "Bergmann's Rule", "추울수록 몸이 커진다",
     "같은 계열이라도 추운 지역 종이 몸집이 크다 — 체적 대비 체표면적이 작아 열을 덜 잃는다.",
     "<b>산맥·심연·정점 = 거대종 위주</b> — 거대 곰·트롤·스톰 자이언트·레비아탄 배치가 이미 이 법칙을 따름. 신규종 설계 지침으로 명문화."),
    ("앨런 법칙", "Allen's Rule", "추울수록 귀·꼬리 등 돌기가 짧아진다",
     "추운 기후의 동물은 열 손실 부위(귀·다리·꼬리)가 짧다.",
     "<b>신규종 비주얼 가이드</b> — G1 한파 바이옴(산맥·동굴 상층) 종은 돌기 짧게. 도감 아이콘 일관성 규칙."),
    ("바이오루미네센스", "Bioluminescence", "빛으로 소통 · 먹이 유인",
     "햇빛 없는 심해·동굴에서 생물이 스스로 빛을 낸다 — 먹이 유인·의사소통·위장 수단.",
     "<b>심해·동굴의 시야 시스템</b> — 발광 종은 어둠 속 시야 범위 제공. 동굴 바이옴 '조명 반경 -40%' 모디퍼와 정합 (06 §3.2)."),
    ("수요공급 · 동적 가격", "Supply–Demand Pricing", "가격 = 기본가 × (목표재고/현재재고)^k",
     "재고가 많으면 내려가고 부족하면 오르는 가격 변동 — 시장의 기본 원리.",
     "<b>NPC 상점·사냥 재료 판매가 변동</b> — 과잉 사냥된 재료는 값 떨어짐 → 자연스러운 자원 분산 유도 (P3 이후 후보)."),
    ("싱크와 소스", "Sink & Source", "발행(소스) = 회수(싱크) 유지",
     "퀘스트·드롭으로 돈이 새로 생기면(소스), 강화·세금으로 돌아가는 통로(싱크)가 반드시 필요하다. 균형이 깨지면 인플레이션.",
     "<b>골드100×층·영혼석 층×30(소스) ↔ 소환티켓130석·합성·병원(싱크)</b> — 이미 존재하는 경제 설계. 사냥 재화 추가 시 재계산 필수."),
    ("체감 효용", "Diminishing Returns", "효과 = X/(X+C) 형태",
     "같은 투자를 반복해도 실제 체감 효과는 점점 줄어든다. 무한 강화 방지의 기본.",
     "<b>DEF/(DEF+200) 데미지 감소식</b> — AGENTS §4에 이미 확정. 온도 내성·Sanity 회복에도 동일식 적용 권장."),
    ("멱함수 성장", "Power Law", "Y = a·X^b",
     "필요 경험치·강화 비용이 레벨의 거듭제곱으로 늘어난다 — 초반 빠르게, 후반 느리게.",
     "<b>Lv100 곡선·영혼석 합성 비용</b> (P3-1) — b≈2~2.5 가안. 생태 개체수 회복 속도에도 적용 가능 (r전략종 b 낮음)."),
    ("마르코프 연쇄", "Markov Chain", "다음 상태 = f(현재 상태)만으로 결정",
     "날씨·환경이 현재 상태에서만 확률적으로 다음 상태로 넘어간다 — 기억 없는 자연스러운 변동.",
     "<b>시뮬레이터 계절제 시연 구현</b> — 한파·평년·폭엔 3상태 전이확률행렬(유지 0.60)이 온도를 흔들고, 열성능 φ가 r·K·d를 진폭 → 계절마다 파동 변화. 층 진입 기온 전환은 계절제 확장 후보 (06 §3.5·미정L)."),
]

CAT = {
    "로지스틱 성장":"ce","수용력":"ce","로트카-볼테라":"ce","영양 단계 · 10% 법칙":"ce",
    "영양급위":"ce","섬생물지리학":"ce","니치 분화 · 경쟁 배제":"ce","r/K 전략":"ce",
    "생태 천이":"ce","핵심종 · 지표종":"ce","침입종":"ce","영양물질 순환":"ce",
    "기능반응 곡선":"ce","온도 의존성 · 열성능 곡선":"ce","베르그만 법칙":"ce","앨런 법칙":"ce",
    "바이오루미네센스":"ce",
    "체감 효용":"cb","멱함수 성장":"cb",
    "수요공급 · 동적 가격":"cc","싱크와 소스":"cc","마르코프 연쇄":"cc",
}
CAT_KO = {"ce":"생태","cb":"밸런스","cc":"경제·시뮬"}

ONE_LINER = {
    "로지스틱 성장": "개체수는 무한히 늘지 않고 한계(K)에서 멈춘다",
    "수용력": "그 환경이 먹여 살릴 수 있는 최대 개체수",
    "로트카-볼테라": "먹이 늘면 포식자 늘고, 포식자 늘면 먹이 줄고 — 주기 파동",
    "영양 단계 · 10% 법칙": "단계가 올라갈수록 에너지는 1/10 — 최상위 포식자는 늘 소수",
    "영양급위": "상위 포식자가 사라지면 그 아래가 폭발한다",
    "섬생물지리학": "섬이 크고 본토와 가까울수록 종이 많다 — 5층 블록=섬",
    "니치 분화 · 경쟁 배제": "같은 자리·같은 먹이면 두 종은 공존 못 한다",
    "r/K 전략": "많이 낳고 빨리 늘는 종 vs 적게 낳고 크게 사는 종",
    "생태 천이": "무너진 생태는 정해진 순서로 서서히 회복된다",
    "핵심종 · 지표종": "하나 빠지면 생태 전체가 바뀌는 종 / 건강도를 알리는 종",
    "침입종": "천적 없이 들어온 종은 제멋대로 폭발한다",
    "영양물질 순환": "죽은 것은 분해자를 거쳐 다시 자원이 된다",
    "기능반응 곡선": "사냥감이 아무리 많아도 포식 속도엔 한계가 있다",
    "온도 의존성 · 열성능 곡선": "최적 온도에서만 최고 성능 — 벗어나면 급락",
    "베르그만 법칙": "추운 곳 생물은 몸집이 크다",
    "앨런 법칙": "추운 곳 생물은 귀·꼬리 같은 돌기가 짧다",
    "바이오루미네센스": "어두운 곳에서 생물이 스스로 빛을 낸다",
    "체감 효용": "같은 투자를 반복해도 체감 효과는 점점 줄어든다",
    "멱함수 성장": "요구량이 거듭제곱으로 늘어난다 — 초반 빠르게, 후반 느리게",
    "수요공급 · 동적 가격": "재고가 많으면 싸지고, 부족하면 비싸진다",
    "싱크와 소스": "돈이 나오는 통로와 들어가는 통로의 총량을 맞춘다",
    "마르코프 연쇄": "다음 날씨는 현재 상태만으로 확률적으로 결정된다",
}
PIN = {"로지스틱 성장", "로트카-볼테라"}
CONCEPT_GROUPS = [
    ("ce", "생태", "먹이사슬·개체수 — 게임이 '살아있는' 이유"),
    ("cb", "밸런스", "성장·제한 — 숫자가 폭주하지 않게 하는 법칙"),
    ("cc", "경제·시뮬", "재화·변동 — 시스템이 도는 법칙"),
]

def concept_card(n, e, f, d, m):
    cls = "concept" + (" pinned" if n in PIN else "")
    op = " open" if n in PIN else ""
    star = '<span class="star">★ </span>' if n in PIN else ""
    return (f'<details class="{cls}"{op}><summary>'
            f'<span class="conline"><span class="cat {CAT[n]}">{CAT_KO[CAT[n]]}</span><b>{star}{n}</b></span>'
            f'<span class="oneliner">{ONE_LINER[n]}</span></summary>'
            f'<div class="cbody"><span class="en">{e}</span>'
            f'<div class="formula">{f}</div><p>{d}</p><p class="map">→ 게임 매핑: {m}</p></div></details>')

parts = []
for cat, label, desc in CONCEPT_GROUPS:
    items = [c for c in CONCEPTS if CAT[c[0]] == cat]
    cards = "\n".join(concept_card(*c) for c in items)
    parts.append(f'<div class="cghead">{label} <span class="cgsub">{desc} · {len(items)}개</span></div>\n<div class="concepts">\n{cards}\n</div>')
concepts_html = "\n".join(parts)

html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>소울 커맨더 — 생태 도감</title>
<style>
  :root{--bg:#14111c;--card:#1e1930;--line:#332a4a;--tx:#e8e2f4;--dim:#9a90b8;
    --g1:#5fb877;--g2:#5f8fd8;--g3:#d8b45f;--prey:#8fce6a;--pred:#e06a6a;--dec:#b08ce0;--prod:#6ad4c4;}
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--tx);font-family:'Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif;line-height:1.6}
  .wrap{max-width:1180px;margin:0 auto;padding:0 20px 40px}
  /* ── 상단 고정 내비 (탭 = 사전의 표제어 구획) ── */
  .topbar{position:sticky;top:0;z-index:40;background:rgba(20,17,28,.94);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);margin:0 -20px;padding:10px 20px 0}
  .brand{font-size:17px;font-weight:800;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .brand small{color:var(--dim);font-weight:400;font-size:11.5px}
  .tabs{display:flex;gap:4px;margin-top:8px;flex-wrap:wrap}
  .tab{background:none;border:none;color:var(--dim);font:inherit;font-size:13.5px;font-weight:600;padding:8px 14px;border-radius:10px 10px 0 0;cursor:pointer;border-bottom:2px solid transparent}
  .tab:hover{color:var(--tx)}
  .tab.on{color:#fff;border-bottom-color:#ffd98a;background:#1a1626}
  .panel{padding-top:22px}
  .hidden{display:none}
  h2{font-size:21px;margin:8px 0 6px;padding-bottom:8px;border-bottom:2px solid var(--line)}
  h2 .sub{color:var(--dim);font-size:13px;font-weight:400;margin-left:8px}
  .lead{color:var(--dim);font-size:13.5px;margin-bottom:16px;max-width:860px}
  .lead b{color:#ffd98a}
  .stats{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 14px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:12px;color:var(--dim)}
  .stat b{font-size:18px;display:block;color:#fff}
  /* ── 종사전: 검색 · 필터 · 색인 ── */
  .dexbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
  .dexbar input[type=search]{flex:1;min-width:220px;background:#12101a;border:1px solid var(--line);border-radius:10px;color:var(--tx);font:inherit;font-size:14px;padding:9px 14px}
  .dexbar input[type=search]:focus{outline:1px solid #8fd0ff}
  .chipbtn{background:#221d33;border:1px solid var(--line);color:#cfc6ee;font:inherit;font-size:12px;border-radius:20px;padding:5px 12px;cursor:pointer}
  .chipbtn.on{background:#3a2f55;border-color:#8fd0ff;color:#fff}
  select{background:#12101a;color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:12.5px}
  .choidx{display:flex;gap:4px;flex-wrap:wrap;margin:2px 0 12px}
  .cho{background:none;border:1px solid var(--line);color:var(--dim);font-size:11.5px;border-radius:6px;padding:2px 8px;cursor:pointer}
  .cho.on{background:#332a4a;color:#fff;border-color:#8fd0ff}
  .dexgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,240px),1fr));gap:10px}
  .dcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px;cursor:pointer;position:relative;transition:border-color .12s}
  .dcard:hover{border-color:#8fd0ff}
  .dcard .dt{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
  .dcard b{font-size:15px}
  .dcard .did{font-size:10px;color:var(--dim);font-family:ui-monospace,monospace}
  .dcard .dl{color:var(--dim);font-size:12px;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .dcard .dchips{margin-top:7px;display:flex;gap:4px;flex-wrap:wrap}
  .mini{font-size:10px;border-radius:4px;padding:1px 6px}
  .mini.amb{background:#16332f;color:#6ad4c4}.mini.mon{background:#332a12;color:#ffd98a}.mini.plan{background:#2e1a33;color:#e08cd0;border:1px dashed #e08cd0}
  .mini.r-prey,.mini.r-swarm,.mini.r-producer{background:#243620;color:var(--prey)}
  .mini.r-predator,.mini.r-hunter,.mini.r-ambusher,.mini.r-apex{background:#382020;color:var(--pred)}
  .mini.r-decomposer,.mini.r-scavenger,.mini.r-corruptor{background:#2c2240;color:var(--dec)}
  .mini.r-guardian,.mini.r-undead,.mini.r-mimic,.mini.r-elemental,.mini.r-warrior{background:#262035;color:var(--dim)}
  .mini.tier{background:#332a4a;color:#b8a8e8}
  .empty{color:var(--dim);font-size:13px;padding:26px 0;text-align:center}
  /* ── 상세 팝업 (사전 항목 뷰) ── */
  .modal{position:fixed;inset:0;background:rgba(10,8,16,.72);display:flex;align-items:flex-start;justify-content:center;z-index:60;padding:5vh 14px}
  .modal.hidden{display:none}
  .mcard{width:min(660px,96vw);max-height:88vh;overflow:auto;background:var(--card);border:1px solid #4a3d6e;border-radius:16px;padding:20px 22px;position:relative}
  .mclose{position:absolute;top:10px;right:12px;background:#221d33;border:1px solid var(--line);color:var(--dim);border-radius:8px;font:inherit;font-size:12px;padding:3px 10px;cursor:pointer}
  .mhead b{font-size:22px}
  .mhead .mid{color:var(--dim);font-size:11px;font-family:ui-monospace,monospace;margin-left:8px}
  .mbadges{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px}
  .mdef{font-size:14px;margin:10px 0 2px;color:#e8e2f4}
  .kv{display:grid;grid-template-columns:92px 1fr;gap:5px 10px;font-size:13px;margin:12px 0;border-top:1px dashed var(--line);border-bottom:1px dashed var(--line);padding:12px 0}
  .kv dt{color:var(--dim)}
  .kv dd a,.xref{color:#8fd0ff;cursor:pointer;text-decoration:none;border-bottom:1px dotted #8fd0ff}
  .rel{margin:10px 0}
  .rel h4{font-size:12.5px;color:var(--dim);margin:8px 0 5px}
  .relchip{display:inline-block;font-size:12px;border-radius:16px;padding:3px 11px;margin:2px 4px 2px 0;background:#262035;border:1px solid var(--line)}
  .relchip a{color:#8fd0ff;cursor:pointer}
  .relchip.res{border-style:dashed;color:var(--dim)}
  table.stt{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
  table.stt th{color:var(--dim);font-weight:500;text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);font-size:12px}
  table.stt td{padding:5px 8px;border-bottom:1px dashed var(--line)}
  .mnote{font-size:12.5px;color:var(--dim);margin-top:12px}
  /* ── 개념 사전 (접이식) ── */
  .cghead{margin:26px 0 10px;font-size:16px;font-weight:700}
  .cghead:first-of-type{margin-top:14px}
  .cgsub{color:var(--dim);font-size:12px;font-weight:400;margin-left:8px}
  .concepts{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:10px}
  details.concept{background:var(--card);border:1px solid var(--line);border-radius:12px;font-size:13px;overflow:hidden}
  details.concept.pinned{border-color:#5a4a22;box-shadow:0 0 0 1px #5a4a22 inset}
  details.concept summary{list-style:none;cursor:pointer;padding:11px 14px;display:flex;flex-direction:column;gap:3px;position:relative}
  details.concept summary::-webkit-details-marker{display:none}
  details.concept summary::after{content:'▸ 펼치기';font-size:10.5px;color:var(--dim);position:absolute;right:14px;margin-top:-17px}
  details.concept[open] summary::after{content:'▴ 접기'}
  .conline{display:flex;align-items:center;gap:6px}
  .conline b{font-size:14.5px}
  .star{color:#ffd98a}
  .oneliner{color:var(--dim);font-size:12px;line-height:1.45}
  details.concept[open] .oneliner{color:#b8a8e8}
  .cbody{padding:0 14px 13px;font-size:13px;border-top:1px dashed var(--line);margin-top:2px;padding-top:10px}
  .cbody .en{display:block;color:var(--dim);font-size:11px;margin-bottom:6px}
  .cat{font-size:10px;border-radius:4px;padding:1px 6px}
  .cat.ce{background:#16332f;color:#6ad4c4}
  .cat.cb{background:#3a2f12;color:#ffd98a}
  .cat.cc{background:#2e1a33;color:#e08cd0}
  .formula{font-family:ui-monospace,monospace;background:#12101a;border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin:8px 0;font-size:12px;color:#ffd98a;white-space:pre-line}
  .concept p{color:#cfc6e4;margin:4px 0}
  .concept .map{color:#8fd0ff;font-size:12.5px}
  /* ── 바이옴 카드 ── */
  .ghead{margin:30px 0 12px;font-size:17px;font-weight:700}
  .ghead .bar{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px}
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,350px),1fr));gap:14px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;position:relative}
  .card.g1{border-top:3px solid var(--g1)} .card.g2{border-top:3px solid var(--g2)} .card.g3{border-top:3px solid var(--g3)}
  .chead2{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;flex-wrap:wrap;gap:2px 8px}
  .cname{font-size:17px;font-weight:700}
  .cmeta{font-size:11px;color:var(--dim)}
  .res{background:#12101a;border-radius:8px;padding:8px 10px;margin:8px 0;font-size:12.5px}
  .res b{color:#ffd98a}
  .res .d{color:var(--dim);font-size:11.5px;display:block}
  .chain{margin:8px 0}
  .crow{display:flex;align-items:flex-start;gap:6px;margin:5px 0;flex-wrap:wrap}
  .clabel{font-size:11px;color:var(--dim);min-width:44px;padding-top:3px}
  .chip{font-size:11.5px;border-radius:20px;padding:2px 9px;margin:1px 0;display:inline-block}
  .chip.prey{background:#243620;border:1px solid var(--prey);color:var(--prey)}
  .chip.swarm{background:#243620;border:1px solid var(--prey);color:var(--prey)}
  .chip.producer{background:#16332f;border:1px solid var(--prod);color:var(--prod)}
  .chip.predator,.chip.hunter,.chip.ambusher,.chip.apex{background:#382020;border:1px solid var(--pred);color:var(--pred)}
  .chip.decomposer,.chip.scavenger,.chip.corruptor{background:#2c2240;border:1px solid var(--dec);color:var(--dec)}
  .chip.other{background:#262035;border:1px solid var(--line);color:var(--dim)}
  .chip.plan{border-style:dashed;opacity:.85}
  .chip .src{color:var(--dim);font-size:10px}
  .badge{font-size:10.5px;border-radius:6px;padding:2px 8px;margin-left:6px;vertical-align:2px}
  .badge.ok{background:#1d3322;color:#7fe09a}
  .badge.miss{background:#3a2720;color:#e0a07f}
  .badge.plan{background:#332a4a;color:#b8a8e8}
  .cnote{font-size:12px;color:var(--dim);border-top:1px dashed var(--line);margin-top:10px;padding-top:8px}
  .jump{font-size:11px;background:#262035;border:1px solid var(--line);color:#b8a8e8;border-radius:6px;padding:2px 8px;cursor:pointer;margin-left:6px}
  /* ── 시뮬레이터 ── */
  .sim{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:16px}
  .simrow{display:flex;gap:22px;flex-wrap:wrap;margin-top:12px}
  canvas{background:#12101a;border-radius:10px;border:1px solid var(--line);width:100%;max-width:620px;height:auto}
  .sl{font-size:12px;color:var(--dim);display:block;margin:7px 0 2px}
  .sl b{color:var(--tx)}
  input[type=range]{width:190px;accent-color:#8fd0ff}
  .eqbox{font-size:12.5px;color:#cfc6e4;background:#12101a;border-radius:8px;padding:8px 12px;margin-top:10px}
  .legend{font-size:12px;color:var(--dim);margin-top:6px}
  .legend i{display:inline-block;width:18px;height:3px;border-radius:2px;margin:0 5px 0 12px;vertical-align:3px}
  footer{margin-top:46px;color:var(--dim);font-size:12px;border-top:1px solid var(--line);padding-top:14px}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div class="brand">📜 소울 커맨더 — 생태 도감 <small>20바이옴 × 하나의 먹이사슬 · 사전형 참조 (07 §10)</small></div>
    <div class="tabs">
      <button class="tab on" data-p="dex">🔎 종사전 <span class="mini amb" style="margin-left:2px">__NSP__종</span></button>
      <button class="tab" data-p="biome">🗺 바이옴 <span class="mini amb" style="margin-left:2px">20</span></button>
      <button class="tab" data-p="concept">📖 생태 개념 <span class="mini amb" style="margin-left:2px">22</span></button>
      <button class="tab" data-p="sim">📈 시뮬레이터</button>
      <button class="tab" data-p="web">🕸 먹이사슬</button>
    </div>
  </div>

  <!-- ① 종사전 — 가장 중요한 내용이 기본 화면 -->
  <section id="panel-dex" class="panel">
    <div class="stats">
      <div class="stat"><b>__NAMB__</b>야생종</div>
      <div class="stat"><b>__NMON__</b>전투종</div>
      <div class="stat"><b>+__NPLAN__</b>예정 신규종</div>
      <div class="stat"><b>__NEDGE__</b>생태 통로</div>
      <div class="stat"><b>__NOK__/20</b>사슬 완결</div>
    </div>
    <p class="lead">표제어를 <b>검색</b>하거나 <b>초성 색인</b>으로 찾아보세요. 항목을 누르면 뜻풀이(정의)·서식·먹이사슬 관계가 나오고, <b>먹이·천적은 클릭</b>하면 그 종의 항목으로 이동합니다. 기본 정렬은 중요도(전투 티어 → 야생 → 예정)순.</p>
    <div class="dexbar">
      <input type="search" id="q" placeholder="표제어 검색 — 예: 쥐, 슬라임, 레비아탄…" autocomplete="off">
      <button class="chipbtn on" data-k="all">전체</button>
      <button class="chipbtn" data-k="mon">전투 __NMON__</button>
      <button class="chipbtn" data-k="amb">야생 __NAMB__</button>
      <button class="chipbtn" data-k="plan">예정 __NPLAN__</button>
      <select id="srt"><option value="imp">중요도순</option><option value="ga">가나다순</option></select>
    </div>
    <div class="choidx" id="choidx"></div>
    <div class="dexgrid" id="dexgrid"></div>
    <div class="empty hidden" id="dexempty">검색 결과가 없습니다 — 다른 표제어로 찾아보세요.</div>
  </section>

  <!-- ② 바이옴 -->
  <section id="panel-biome" class="panel hidden">
    <h2>바이옴 생태 카드 <span class="sub">근원자원 → 먹이사슬 3계층 · 실선=현행종 / 점선=예정종</span></h2>
    <p class="lead">각 카드는 한 바이옴의 "생태 머리말"이다. 근원자원(맨 아래층)이 수용력 K를 정하고, K가 개체수를 정하고, 개체수가 사슬 전체를 정한다.</p>
    <div id="cards"></div>
  </section>

  <!-- ③ 개념 -->
  <section id="panel-concept" class="panel hidden">
    <h2>생태학 개념 사전 <span class="sub">22개 · 카드를 눌러 펼치기 — ★ 2개는 핵심이니 먼저 보세요</span></h2>
    <p class="lead">모두 다 읽을 필요 없습니다. <b>★ 로지스틱 성장</b>(개체수가 K에서 멈추는 S자 곡선)과 <b>★ 로트카-볼테라</b>(먹이·포식자의 주기 파동)만 이해하면 생태 설계의 8할입니다. 나머지는 필요할 때 펼쳐 보세요.</p>
    __CONCEPTS__
  </section>

  <!-- ④ 시뮬레이터 -->
  <section id="panel-sim" class="panel hidden">
    <h2>로지스틱 · 로트카-볼테라 시뮬레이터 <span class="sub">바이옴 프리셋을 고르고 슬라이더를 움직여보세요</span></h2>
    <div class="sim">
      <select id="biomeSel"></select>
      <label style="font-size:12px;color:var(--dim);margin-left:14px"><input type="checkbox" id="noPred" style="accent-color:#8fd0ff"> 포식자 없음 (순수 로지스틱만 보기)</label>
      <label style="font-size:12px;color:var(--dim);margin-left:14px"><input type="checkbox" id="season" style="accent-color:#8fd0ff" checked> ❄ 마르코프 기온 변동 (계절제) — 한파·평년·폭염 확률 전환</label>
      <button id="reroll" style="font-size:12px;margin-left:14px;background:#221d33;color:#cfc6ee;border:1px solid var(--line);border-radius:8px;padding:3px 10px;cursor:pointer">🎲 시즌 다시 굴리기</button>
      <div class="simrow">
        <div><canvas id="cv" width="620" height="300"></canvas>
          <div class="legend"><i style="background:var(--prey)"></i>피식자 N (먹이층)<i style="background:var(--pred)"></i>포식자 P<i style="background:#ffd98a;opacity:.7"></i>수용력 K<i style="background:#6fa8ff;opacity:.5"></i>한파<i style="background:#9a90b8;opacity:.5"></i>평년<i style="background:#ff9a5a;opacity:.5"></i>폭엔</div>
          <div class="eqbox" id="eq"></div>
        </div>
        <div>
          <span class="sl">성장률 r = <b id="vr"></b></span><input type="range" id="r" min="0.1" max="1.6" step="0.05">
          <span class="sl">수용력 K = <b id="vK"></b></span><input type="range" id="K" min="20" max="160" step="5">
          <span class="sl">포식 강도 a = <b id="va"></b></span><input type="range" id="a" min="0.005" max="0.06" step="0.005">
          <span class="sl">에너지 전환 b = <b id="vb"></b></span><input type="range" id="b" min="0.1" max="1.2" step="0.05">
          <span class="sl">포식자 사망률 d = <b id="vd"></b></span><input type="range" id="d" min="0.1" max="0.9" step="0.05">
          <span class="sl">초기 먹이 N₀ = <b id="vN"></b></span><input type="range" id="N0" min="5" max="150" step="5">
          <span class="sl">초기 포식자 P₀ = <b id="vP"></b></span><input type="range" id="P0" min="1" max="40" step="1">
        </div>
      </div>
    </div>
    <div style="margin-top:26px;border-top:1px dashed var(--line);padding-top:18px">
      <h2 style="margin-top:0">🔬 실데이터 시즌 시뮬레이터 <span class="sub">35종 야생 + 전투 포식자 — 개체수 파동을 계절 단위로</span></h2>
      <p class="lead">바이옴에 실제 서식하는 종 전원을 <b>로지스틱 + 로트카-볼테라</b>로 굽니다. r = 번식률(reproduction) · d = food_need 기반 · 포식강도 = aggression — <b>파라미터 전부 ambient.json의 ecology 필드에서 나옵니다</b>. 수용력 K는 10% 법칙으로 계층 배분(하위층 · 최상위 포식자 희소), 계절마다 각 종의 <b>자체 온도 밴드</b>로 φ가 달라집니다. 0.05 아래로 떨어지면 국소절멸, 시즌 경계에서 25% 확률로 이주 재유입.</p>
      <div class="sim">
        <select id="simBio"></select>
        <span style="font-size:12px;color:var(--dim)">시즌 수</span>
        <select id="simSeasons" style="background:#221d33;color:#cfc6ee;border:1px solid var(--line);border-radius:8px;padding:3px 8px"><option>6</option><option selected>8</option><option>12</option></select>
        <button class="chipbtn" id="simRun">🎲 시즌 다시 굴리기</button>
        <span style="font-size:12px;color:var(--dim)" id="simInfo"></span>
      </div>
      <div class="simrow">
        <div><canvas id="simcv" width="620" height="300"></canvas>
          <div class="legend"><i style="background:#8fce6a"></i>하위층(먹이·분해)<i style="background:#e06a6a"></i>중위층(포식)<i style="background:#ff5252"></i>최상위<i style="background:#ffd98a;opacity:.7"></i>한파<i style="background:#9a90b8;opacity:.5"></i>평년<i style="background:#ff9a5a;opacity:.5"></i>폭엔</div>
        </div>
        <div style="font-size:12px;overflow:auto;max-height:320px"><table id="simTable" style="width:100%;border-collapse:collapse"></table></div>
      </div>
    </div>
  </section>

  <!-- ⑤ 먹이사슬 그래프 -->
  <section id="panel-web" class="panel hidden">
    <h2>먹이사슬 그래프 <span class="sub">누가 누구를 먹는지 — 종 단위 연결 · 노드를 누르면 사전 항목으로</span></h2>
    <p class="lead">노드 색 = 역할 (초록 먹이 · 빨강 포식 · 보라 분해 · 금 테두리 전투종 · 회색 다이아 근원자원). <b>실선</b> = 데이터에 명시된 관계(predators/prey), <b>점선</b> = 같은 바이옴 안의 역할 기반 추정 관계. 노드를 <b>클릭</b>하면 그 종의 사전 항목이 열립니다.</p>
    <div class="dexbar">
      <select id="webBio"><option value="all">전체 바이옴</option></select>
      <button class="chipbtn on" id="webDeriv">추정 간선 표시</button>
      <span style="font-size:12px;color:var(--dim)" id="webInfo"></span>
    </div>
    <canvas id="webcv" width="1100" height="660"></canvas>
  </section>

  <!-- 상세 팝업 -->
  <div id="modal" class="modal hidden"><div class="mcard" id="mcard"></div></div>

  <footer>생성: design-docs/_tools/gen_ecology_codex.py · 데이터 정본: biomes.json · ambient.json · monsters.json · 설계: GDD_v8.0_07_통합생태계 (가안) · 수치는 전부 가안 — 플탐에서 확정</footer>
</div>

<script>
const DATA = __DATA__;
const ROKO = __ROKO__;
const KIND_KO = {amb:"야생", mon:"전투", plan:"예정"};
const DIET_KO = {herbivore:"초식", carnivore:"육식", omnivore:"잡식", none:"비섭취", mana:"마력", blood:"흡혈", mineral:"광물", soul:"영혼", brain:"뇌"};
const $ = id=>document.getElementById(id);

/* ── 먹이사슬 그래프 (force-directed, canvas) ── */
const WEB = (()=>{
  const sp=DATA.species.filter(s=>s.k!=='plan');
  const byId={}; sp.forEach(s=>byId[s.id]=s);
  const byName={}; sp.forEach(s=>byName[s.name]=s);
  const nodes=sp.map((s,i)=>({id:s.id,n:s.name,k:s.k,r:s.r,el:null,x:Math.cos(i/sp.length*6.28)*300+550,y:Math.sin(i/sp.length*6.28)*280+330,vx:0,vy:0}));
  const nById={}; nodes.forEach(n=>nById[n.id]=n);
  const edges=[];
  for(const s of sp){
    for(const p of (s.prey||[])){
      if(p.id&&byId[p.id]) edges.push({a:s.id,b:p.id,w:2.2,dashed:false});
      else if(!p.id){ /* diet-as-resource string → biome resource node */
        const rid='res:'+p.n;
        if(!nById[rid]){nById[rid]={id:rid,n:p.n,k:'res',r:'res',x:550+(Math.random()-0.5)*700,y:330+(Math.random()-0.5)*560,vx:0,vy:0};nodes.push(nById[rid]);}
        edges.push({a:s.id,b:rid,w:1.6,dashed:false});
      }
    }
  }
  /* 추정 간선 — 같은 바이옴 안에서 포식 역할 → 먹이 역할 (실데이터 관계가 없을 때만) */
  const PREY=new Set(['prey','swarm','producer']),PRED=new Set(['predator','hunter','ambusher','apex']);
  const bioNodes={};
  for(const b of DATA.biomes){
    const members=nodes.filter(n=>n.k!=='res'&&byId[n.id]&&(byId[n.id].bio||[]).includes(b.name));
    bioNodes[b.id]=members;
  }
  const estPairs=new Set();
  for(const bid in bioNodes){
    const ms=bioNodes[bid];
    for(const p of ms){ if(!PRED.has(p.r))continue;
      for(const q of ms){ if(!PREY.has(q.r)||p.id===q.id)continue;
        if(edges.some(e=>(e.a===p.id&&e.b===q.id)||(e.a===q.id&&e.b===p.id)))continue;
        const key=p.id+'>'+q.id;
        if(!estPairs.has(key)){estPairs.add(key);edges.push({a:p.id,b:q.id,w:1,dashed:true});}
      } } }
  return {nodes,edges};
})();

/* ── 먹이사슬 그래프 렌더링 ── */
const ROLECOL={prey:'#8fce6a',swarm:'#8fce6a',producer:'#6ad4c4',predator:'#e06a6a',hunter:'#e06a6a',ambusher:'#e06a6a',apex:'#ff5252',decomposer:'#b08ce0',scavenger:'#b08ce0',corruptor:'#b08ce0',guardian:'#9a90b8',undead:'#9a90b8',mimic:'#9a90b8',elemental:'#9a90b8',warrior:'#9a90b8',res:'#ffd98a'};
let webSim=null,webDrag=null,webHover=null,webCur=WEB.nodes;
const webNodeById={};WEB.nodes.forEach(n=>webNodeById[n.id]=n);
function webBBox(){
  const bio=$('webBio').value;
  let ns=WEB.nodes;
  if(bio!=='all'){
    const b=DATA.biomes.find(x=>x.id===bio);
    const names=new Set(b?b.species.map(s=>s.n):[]);
    const keep=new Set();
    for(const n of WEB.nodes){ if(names.has(n.n)) keep.add(n.id); }
    /* 확장 — 종은 늘리지 않는다(연결 그래프라 전체가 유입되는 문제). 유지 종이 직접 먹는 근원자원만 추가 */
    for(const e of WEB.edges){ if(e.dashed)continue;
      if(keep.has(e.a)){const o=webNodeById[e.b]; if(o&&o.k==='res')keep.add(e.b);}
      if(keep.has(e.b)){const o=webNodeById[e.a]; if(o&&o.k==='res')keep.add(e.a);} }
    ns=WEB.nodes.filter(n=>keep.has(n.id));
  }
  return ns;
}
function webStep(ns){
  const ids=new Set(ns.map(n=>n.id));
  const es=WEB.edges.filter(e=>ids.has(e.a)&&ids.has(e.b));
  for(const n of ns){ n.fx=0;n.fy=0; }
  /* 반발 */
  for(let i=0;i<ns.length;i++)for(let j=i+1;j<ns.length;j++){
    const a=ns[i],b=ns[j];
    let dx=b.x-a.x,dy=b.y-a.y; let d2=dx*dx+dy*dy; if(d2<1)d2=1,dx=1,dy=0;
    const d=Math.sqrt(d2);let f=1800/d2; if(f>4)f=4;
    a.fx-=dx/d*f;a.fy-=dy/d*f;b.fx+=dx/d*f;b.fy+=dy/d*f;
  }
  /* 스프링 */
  for(const e of es){
    const a=WEB.nodes.find(x=>x.id===e.a),b=WEB.nodes.find(x=>x.id===e.b);
    if(!a||!b)continue;
    let dx=b.x-a.x,dy=b.y-a.y;const d=Math.max(1,Math.hypot(dx,dy));
    const want=e.dashed?160:130,f=(d-want)*0.012*(e.dashed?0.5:1);
    dx/=d;dy/=d;
    a.fx+=dx*d*f*0.5;a.fy+=dy*d*f*0.5;b.fx-=dx*d*f*0.5;b.fy-=dy*d*f*0.5;
  }
  /* 중심 인력 + 적분 */
  for(const n of ns){
    n.fx+=(550-n.x)*0.045;n.fy+=(330-n.y)*0.045;
    if(webDrag&&webDrag.id===n.id){n.x=webDrag.x;n.y=webDrag.y;n.vx=n.vy=0;continue;}
    n.vx=(n.vx+n.fx*0.35)*0.7;n.vy=(n.vy+n.fy*0.35)*0.7;
    if(n.vx>8)n.vx=8;else if(n.vx<-8)n.vx=-8;if(n.vy>8)n.vy=8;else if(n.vy<-8)n.vy=-8;
    n.x=Math.max(30,Math.min(1070,n.x+n.vx));n.y=Math.max(26,Math.min(634,n.y+n.vy));
  }
  return es;
}
function webDraw(es,showLabels){
  const cv=$('webcv'),g=cv.getContext('2d');
  g.clearRect(0,0,cv.width,cv.height);
  /* 간선 — 추정 간선 숨김 옵션 */
  for(const e of es){
    if(e._hide)continue;
    const a=WEB.nodes.find(x=>x.id===e.a),b=WEB.nodes.find(x=>x.id===e.b);
    if(!a||!b)continue;
    g.strokeStyle=e.dashed?'rgba(154,144,184,0.35)':'rgba(143,208,255,0.55)';
    g.lineWidth=e.w; g.setLineDash(e.dashed?[4,5]:[]);
    g.beginPath();g.moveTo(a.x,a.y);g.lineTo(b.x,b.y);g.stroke();
  }
  g.setLineDash([]);
  /* 노드 */
  g.font='11px sans-serif'; g.textAlign='center';
  const inView=new Set();es.forEach(e=>{inView.add(e.a);inView.add(e.b);});
  for(const n of WEB.nodes){
    if(n.k!=='res'&&!inView.has(n.id))continue;
    const col=ROLECOL[n.r]||'#9a90b8';
    const rad=n.k==='res'?5:(n.k==='mon'?9:7);
    if(n.k==='res'){ /* 다이아 — 근원자원 */
      g.save();g.translate(n.x,n.y);g.rotate(Math.PI/4);
      g.fillStyle=col;g.globalAlpha=.9;g.fillRect(-rad,-rad,rad*2,rad*2);g.restore();
    }else{
      g.beginPath();g.arc(n.x,n.y,rad,0,6.28);
      g.fillStyle=col;g.fill();
      if(n.k==='mon'){g.strokeStyle='#ffd98a';g.lineWidth=2;g.stroke();}
    }
    if(webHover===n.id||showLabels){
      g.fillStyle=n.k==='res'?'#ffd98a':'#e8e2f4';
      g.fillText(n.n,n.x,n.y-rad-5);
    }
  }
  g.textAlign='start';
}
function webRun(){
  if($('panel-web').classList.contains('hidden')){webSim=null;return;}
  const ns=webBBox(); webCur=ns;
  const es=webStep(ns); webDraw(es.filter(e=>!e._hide), ns.length<=60);
  $('webInfo').textContent=`노드 ${ns.filter(n=>n.k!=='res').length}종 · 간선 ${es.filter(e=>!e._hide).length}개`;
  webSim=requestAnimationFrame(webRun);
}
function webStart(){ if(!webSim)webSim=requestAnimationFrame(webRun); }
const webSel=$('webBio');
for(const b of DATA.biomes){const o=document.createElement('option');o.value=b.id;o.textContent=b.name;webSel.appendChild(o);}
/* 기본 뷰 — 전체는 헤어볼이라 가장 풍부한 초원부터 */
webSel.value='biome_plains';
webSel.addEventListener('change',()=>{webStart();});
$('webDeriv').addEventListener('click',e=>{
  e.target.classList.toggle('on');
  const show=e.target.classList.contains('on');
  WEB.edges.forEach(x=>x._d=x.dashed);
  if(!show){WEB.edges.forEach(x=>{if(x.dashed)x._hide=true;});}
  else WEB.edges.forEach(x=>{x._hide=false;});
  webStart();
});
$('webcv').addEventListener('mousemove',e=>{
  const r=e.target.getBoundingClientRect(),sc=e.target.width/r.width;
  const mx=(e.clientX-r.left)*sc,my=(e.clientY-r.top)*sc;
  let hit=null;
  for(const n of webCur){ if(Math.hypot(n.x-mx,n.y-my)<12){hit=n.id;break;} }
  webHover=hit; e.target.style.cursor=hit?'pointer':'default';
});
$('webcv').addEventListener('mousedown',e=>{
  const r=e.target.getBoundingClientRect(),sc=e.target.width/r.width;
  const mx=(e.clientX-r.left)*sc,my=(e.clientY-r.top)*sc;
  for(const n of webCur){ if(Math.hypot(n.x-mx,n.y-my)<12){webDrag={...n};webDrag.node=n;break;} }
});
$('webcv').addEventListener('mousemove',e=>{
  if(!webDrag)return;
  const r=e.target.getBoundingClientRect(),sc=e.target.width/r.width;
  webDrag.x=(e.clientX-r.left)*sc;webDrag.y=(e.clientY-r.top)*sc;
});
window.addEventListener('mouseup',()=>{ if(webDrag&&webDrag._upOnce){/*noop*/} webDrag=null; });
$('webcv').addEventListener('click',e=>{
  if(webDragJustMoved)return;
  const r=e.target.getBoundingClientRect(),sc=e.target.width/r.width;
  const mx=(e.clientX-r.left)*sc,my=(e.clientY-r.top)*sc;
  for(const n of webCur){
    if(Math.hypot(n.x-mx,n.y-my)<12){
      if(n.k==='res')return;
      openSp(n.id);break;
    } }
});
let webDragJustMoved=false;
$('webcv').addEventListener('mousedown',()=>{webDragJustMoved=false;});
$('webcv').addEventListener('mousemove',e=>{if(webDrag)webDragJustMoved=true;});

/* ── 탭 전환 ── */
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));
  document.querySelectorAll('.panel').forEach(p=>p.classList.add('hidden'));
  const p=$('panel-'+t.dataset.p); p.classList.remove('hidden');
  if(t.dataset.p==='sim'){draw();try{SIM.render();}catch(e){}}
  if(t.dataset.p==='web') webStart();
  window.scrollTo({top:0});
}));

/* ── 초성 (가나다 색인) ── */
function chosung(ch){const c=ch.charCodeAt(0);
  if(c>=0xAC00&&c<=0xD7A3)return "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"[Math.floor((c-0xAC00)/588)];
  const u=ch.toUpperCase()[0]; return /[A-Z]/.test(u)?u:null;}

/* ── 종사전 ── */
const S=DATA.species;
const fState={q:'',k:'all',cho:null,srt:'imp'};
function imp(s){return s.k==='mon'?200+(s.tier||0)*10:(s.k==='amb'?100:0);}
function gaCmp(a,b){return a.name.localeCompare(b.name,'ko');}
function filtered(){
  let L=S.filter(s=>{
    if(fState.k!=='all'&&s.k!==fState.k)return false;
    if(fState.cho&&chosung(s.name)!==fState.cho)return false;
    if(fState.q){const q=fState.q.toLowerCase();
      if(!(s.name.toLowerCase().includes(q)||s.id.toLowerCase().includes(q)||(s.note||'').toLowerCase().includes(q)))return false;}
    return true;});
  L=[...L].sort(fState.srt==='ga'?gaCmp:(a,b)=>imp(b)-imp(a)||gaCmp(a,b));
  return L;
}
function roleCls(r){return ['prey','swarm','producer','predator','hunter','ambusher','apex','decomposer','scavenger','corruptor','guardian','undead','mimic','elemental','warrior'].includes(r)?'r-'+r:'';}
function renderDex(){
  const L=filtered(),g=$('dexgrid');
  g.innerHTML=L.map(s=>`<div class="dcard" data-id="${s.id}">
    <div class="dt"><b>${s.name}</b><span class="did">${s.id}</span></div>
    <div class="dchips">
      <span class="mini ${s.k}">${KIND_KO[s.k]}</span>
      <span class="mini ${roleCls(s.r)}">${ROKO[s.r]||s.r}</span>
      ${s.tier?`<span class="mini tier">T${s.tier}</span>`:''}
      ${s.bio[0]?`<span class="mini" style="background:#262035;color:var(--dim)">${s.bio.join('·')}</span>`:''}
    </div>
    <p class="dl">${s.note||''}</p></div>`).join('');
  $('dexempty').classList.toggle('hidden',L.length>0);
}
/* 초성 색인 — 현재 필터 결과에 존재하는 초성만 */
function renderCho(){
  const base=S.filter(s=>fState.k==='all'||s.k===fState.k);
  const set=[...new Set(base.map(s=>chosung(s.name)).filter(Boolean))]
    .sort((a,b)=>"ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ".indexOf(a)-"ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ".indexOf(b));
  $('choidx').innerHTML=`<button class="cho ${!fState.cho?'on':''}" data-c="">전체</button>`+
    set.map(c=>`<button class="cho ${fState.cho===c?'on':''}" data-c="${c}">${c}</button>`).join('');
}
$('q').addEventListener('input',e=>{fState.q=e.target.value.trim();renderDex();});
document.querySelectorAll('.chipbtn[data-k]').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.chipbtn[data-k]').forEach(x=>x.classList.toggle('on',x===b));
  fState.k=b.dataset.k; fState.cho=null; renderCho(); renderDex();}));
$('choidx').addEventListener('click',e=>{if(!e.target.classList.contains('cho'))return;
  fState.cho=e.target.dataset.c||null;renderCho();renderDex();});
$('srt').addEventListener('change',e=>{fState.srt=e.target.value;renderDex();});
$('dexgrid').addEventListener('click',e=>{const c=e.target.closest('.dcard');if(c)openSp(c.dataset.id);});

/* ── 상세 팝업 (사전 항목) ── */
function relChips(list,lab){
  if(!list||!list.length)return '';
  const chips=list.map(x=>x.id
    ?`<span class="relchip"><a data-sp="${x.id}">${x.n}</a> ›</span>`
    :`<span class="relchip res">${x.n} · 자원</span>`).join('');
  return `<div class="rel"><h4>${lab}</h4>${chips}</div>`;
}
function openSp(id){
  const s=S.find(x=>x.id===id); if(!s)return;
  const t=s.temp, band=t?`${t[0]}~${t[1]}°C`:(s.k==='plan'?'미정 (소속 바이옴 band 예정)':'—');
  const st=s.stats?`<table class="stt"><tr><th>HP</th><th>ATK</th><th>DEF</th><th>방어속도</th><th>마방</th></tr>
    <tr><td>${s.stats.hp??'—'}</td><td>${s.stats.atk??'—'}</td><td>${s.stats.def??'—'}</td><td>${s.stats.aspd??'—'}</td><td>${s.stats.mdef??'—'}</td></tr></table>`:'';
  $('mcard').innerHTML=`
    <button class="mclose" onclick="closeSp()">닫기 ✕</button>
    <div class="mhead"><b>${s.name}</b><span class="mid">${s.id}</span></div>
    <div class="mbadges">
      <span class="mini ${s.k}">${KIND_KO[s.k]}</span>
      <span class="mini ${roleCls(s.r)}">${ROKO[s.r]||s.r}</span>
      ${s.tier?`<span class="mini tier">티어 T${s.tier}</span>`:''}
      ${s.el?`<span class="mini" style="background:#262035;color:#ffd98a">${s.el}</span>`:''}
    </div>
    <p class="mdef">${s.note||''}</p>
    <dl class="kv">
      <dt>식성</dt><dd>${s.d?DIET_KO[s.d]||s.d:'미정'}</dd>
      <dt>서식 바이옴</dt><dd>${s.bio.join(' · ')||'—'}</dd>
      <dt>출현층 (참조)</dt><dd>${s.floors?`${s.floors[0]}~${s.floors[1]}층`:'—'}</dd>
      <dt>온도 내성</dt><dd>${band}</dd>
    </dl>
    ${relChips(s.prey,'🍂 먹이 (이 종이 먹는 것)')}
    ${relChips(s.pred,'🎯 천적 (이 종을 먹는 것)')}
    ${st}
    <p class="mnote">※ 출현층은 바이옴 배정 전 참조값 — 실제 스폰은 habitat × 온도 게이트 (06 §3.5)로 결정.</p>`;
  $('modal').classList.remove('hidden');
}
window.openSp=openSp;
window.closeSp=()=>{$('modal').classList.add('hidden');};
$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closeSp();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeSp();});
document.addEventListener('click',e=>{
  const a=e.target.closest('[data-sp]'); if(a){openSp(a.dataset.sp); $('mcard').scrollTop=0;}
});

/* ── 바이옴 카드 ── */
const cardsEl=$('cards');
const GROUPS=[["g1","G1 하부 탑 (1~50층)","var(--g1)"],["g2","G2 중부 탑 (51~95층)","var(--g2)"],["g3","G3 정점 (96~100층)","var(--g3)"]];
for (const [gid,label,color] of GROUPS){
  const list=DATA.biomes.filter(b=>b.gid===gid);
  const h=document.createElement('div');
  h.className='ghead'; h.innerHTML=`<span class="bar" style="background:${color}"></span>${label}`;
  cardsEl.appendChild(h);
  const grid=document.createElement('div'); grid.className='cards';
  for (const b of list){
    const groups={"먹이층":["prey","swarm","producer"],"포식층":["predator","hunter","ambusher","apex"],"분해층":["decomposer","scavenger","corruptor"]};
    let rows='';
    for (const [lab,roles] of Object.entries(groups)){
      const mine=b.species.filter(s=>roles.includes(s.r));
      if(!mine.length)continue;
      rows+=`<div class="crow"><span class="clabel">${lab}</span><span>`+mine.map(s=>{
        const t=ROKO[s.r]||s.r;
        const cn=['predator','hunter','ambusher','apex'].includes(s.r)?'pred':(['decomposer','scavenger','corruptor'].includes(s.r)?'dec':s.r);
        return `<span class="chip ${cn==='pred'?'predator':(cn==='dec'?'decomposer':cn)} ${s.p?'plan':''}" title="${t}">${s.n} <span style="opacity:.7">· ${t}</span>${s.p?` <span class="src">${s.src||''}</span>`:''}</span>`;
      }).join('')+`</span></div>`;
    }
    const others=b.species.filter(s=>!["prey","swarm","producer","predator","hunter","ambusher","apex","decomposer","scavenger","corruptor"].includes(s.r));
    if(others.length)rows+=`<div class="crow"><span class="clabel">특수</span><span>`+others.map(s=>`<span class="chip other">${s.n} · ${ROKO[s.r]||s.r}</span>`).join('')+`</span></div>`;
    const badge=b.complete?'<span class="badge ok">사슬 완결 ✅</span>':`<span class="badge miss">결핍: ${b.missing.join('·')}</span>`;
    grid.insertAdjacentHTML('beforeend',`
      <div class="card ${b.gid}">
        <div class="chead2"><span class="cname">${b.name}</span><span class="cmeta">${b.gname} · 블록 ${b.slots[0]} · 계수 ×${b.mult.toFixed(2)}</span></div>
        <div>${badge}<span class="badge plan">현행 ${b.curN}종 + 예정 ${b.planN}종</span></div>
        <div class="res"><b>⟡ 근원자원 — ${b.resName}</b><span class="d">${b.resDesc} · K≈${b.K} · r≈${b.r}</span></div>
        <div style="font-size:11.5px;color:var(--dim);margin:-2px 0 6px">${b.tempS} · 서식 가능 밴드 밖 종은 스폰 차단 (06 §3.5)</div>
        <div class="chain">${rows}</div>
        <div class="cnote">🌱 ${b.note} <button class="jump" data-b="${b.id}">시뮬레이터 ▶</button></div>
      </div>`);
  }
  cardsEl.appendChild(grid);
}

/* ── 시뮬레이터 ── */
const sel=$('biomeSel');
for (const b of DATA.biomes){const o=document.createElement('option');o.value=b.id;o.textContent=`${b.name} (K=${b.K}, r=${b.r})`;sel.appendChild(o);}
const ctrl={r:$('r'),K:$('K'),a:$('a'),b:$('b'),d:$('d'),N0:$('N0'),P0:$('P0')};
function preset(){const b=DATA.biomes.find(x=>x.id===sel.value);
  ctrl.r.value=b.r; ctrl.K.value=b.K; ctrl.a.value=0.02; ctrl.b.value=0.5; ctrl.d.value=0.35;
  ctrl.N0.value=Math.round(b.K*0.4); ctrl.P0.value=Math.max(1,Math.round(b.K*0.06)); sync(); draw();}
function sync(){$('vr').textContent=(+ctrl.r.value).toFixed(2);$('vK').textContent=ctrl.K.value;
  $('va').textContent=(+ctrl.a.value).toFixed(3);$('vb').textContent=(+ctrl.b.value).toFixed(2);
  $('vd').textContent=(+ctrl.d.value).toFixed(2);$('vN').textContent=ctrl.N0.value;$('vP').textContent=ctrl.P0.value;}
/* ── 마르코프 기온 상태 — 한파/평년/폭엔 3상태 전이 (06 §3.5 · 07 §8) ── */
const MK={names:['한파','평년','폭엔'],cols:['#6fa8ff','#9a90b8','#ff9a5a'],
  P:[[0.60,0.35,0.05],[0.15,0.70,0.15],[0.05,0.35,0.60]],OFF:0.4};
let seed=1;
function rand(){seed=(seed*1103515245+12345)&0x7fffffff;return seed/0x7fffffff;}
function simulate(){const r0=+ctrl.r.value,K0=+ctrl.K.value,a=+ctrl.a.value,b=+ctrl.b.value,d0=+ctrl.d.value;
  const noPred=$('noPred').checked,useSeason=$('season').checked;
  const bio=DATA.biomes.find(x=>x.id===sel.value);
  const [T0,Tlo,Thi]=bio.cl,bw=Thi-Tlo,Topt=(Tlo+Thi)/2;
  let N=+ctrl.N0.value,P=noPred?0:+ctrl.P0.value,st=1;
  const dt=0.02,steps=6000,SEASON=600,ts=[],Ns=[],Ps=[],Ss=[],Ks=[];
  for(let i=0;i<steps;i++){
    if(useSeason&&i%SEASON===0){const p=MK.P[st],u=rand();st=u<p[0]?0:(u<p[0]+p[1]?1:2);}
    const off=useSeason?(st===0?-MK.OFF*bw:(st===2?MK.OFF*bw:0)):0;
    const T=T0+off;
    const phi=useSeason?Math.exp(-Math.pow((T-Topt)/(bw/3),2)):1;
    const r=r0*phi,K=K0*(0.3+0.7*phi),d=d0*(1+0.3*(1-phi));
    const dN=r*N*(1-N/K)-a*N*P;const dP=noPred?0:(b*a*N*P-d*P);
    N=Math.max(0.01,N+dN*dt);P=Math.max(0,P+dP*dt);
    if(i%10===0){ts.push(i*dt);Ns.push(N);Ps.push(P);Ss.push(useSeason?st:-1);Ks.push(K);}}
  return {ts,Ns,Ps,Ss,Ks,K:K0};}
function draw(){sync();const {ts,Ns,Ps,Ss,Ks,K}=simulate();const cv=$('cv'),g=cv.getContext('2d');
  g.clearRect(0,0,cv.width,cv.height);const pad=34,W=cv.width-pad-10,H=cv.height-24;
  const maxY=Math.max(K,...Ns,...Ps)*1.1;
  const X=t=>pad+t/ts[ts.length-1]*W,Y=v=>cv.height-12-v/maxY*H;
  g.font='11px sans-serif';
  if(Ss[0]!==-1){let s0=0;
    for(let i=1;i<=Ss.length;i++){
      if(i===Ss.length||Ss[i]!==Ss[s0]){
        const x0=X(ts[s0]),x1=X(ts[Math.min(i,ts.length-1)])||pad+W;
        g.fillStyle=MK.cols[Ss[s0]];g.globalAlpha=.13;g.fillRect(x0,0,x1-x0,cv.height-12);g.globalAlpha=1;
        g.fillStyle=MK.cols[Ss[s0]];g.fillText(MK.names[Ss[s0]],x0+4,12);
        s0=i;}}}
  g.strokeStyle='#ffd98a';g.lineWidth=1;g.globalAlpha=.45;g.beginPath();ts.forEach((t,i)=>{const x=X(t),y=Y(Ks[i]);i?g.lineTo(x,y):g.moveTo(x,y);});g.stroke();g.globalAlpha=1;g.lineWidth=2;
  g.strokeStyle='#ffd98a';g.setLineDash([5,5]);g.globalAlpha=.55;g.beginPath();g.moveTo(pad,Y(K));g.lineTo(pad+W,Y(K));g.stroke();g.setLineDash([]);g.globalAlpha=1;
  g.strokeStyle='#8fce6a';g.beginPath();ts.forEach((t,i)=>{const x=X(t),y=Y(Ns[i]);i?g.lineTo(x,y):g.moveTo(x,y);});g.stroke();
  g.strokeStyle='#e06a6a';g.beginPath();ts.forEach((t,i)=>{const x=X(t),y=Y(Ps[i]);i?g.lineTo(x,y):g.moveTo(x,y);});g.stroke();
  g.fillStyle='#9a90b8';g.fillText('개체수',pad-26,14);g.fillText('시간 →',pad+W-30,cv.height-2);
  g.fillStyle='#ffd98a';g.globalAlpha=.8;g.fillText('K='+K,pad+4,Y(K)-5);g.globalAlpha=1;
  const bio=DATA.biomes.find(x=>x.id===sel.value),a=+ctrl.a.value,bb=+ctrl.b.value,d=+ctrl.d.value;
  const Nstar=d/(bb*a),Pstar=(+ctrl.r.value/a)*(1-Math.min(1,Nstar/K));
  const seasonNote=$('season').checked
    ?` <b style="color:#8fd0ff">│ 마르코프 계절:</b> 전이확률 P(평년→한파)=0.35·P(평년→폭엔)=0.15·유지 0.60 — 계절 온도가 열성능 φ를 통해 <b>r·K·d를 진폭</b>시켜 파동이 계절마다 달라진다`
    :'';
  $('eq').innerHTML=$('noPred').checked
    ?`순수 로지스틱: 개체수는 <b>K=${K}</b>로 수렴 (S자 곡선) — 실제 N≈${Ns[Ns.length-1].toFixed(0)}${seasonNote}`
    :`평형점: 먹이 N* = d/(b·a) = ${Nstar.toFixed(1)} · 포식자 P* = (r/a)(1−N*/K) = ${Math.max(0,Pstar).toFixed(1)} — 두 파동이 이 주위를 도는 구조 (전환 효율 b·a·N* > d면 포식자 생존)${seasonNote}`;}
sel.addEventListener('change',preset);$('noPred').addEventListener('change',draw);$('season').addEventListener('change',draw);
$('reroll').addEventListener('click',()=>{seed=(Date.now()%2147483647)||1;draw();});
for(const id in ctrl)ctrl[id].addEventListener('input',draw);

/* ── 실데이터 시즌 시뮬레이터 — ambient.json ecology 필드 기반 (07 §8 로지스틱·LV·마르코프) ── */
const SIM=(()=>{
  /* 1) 종별 파라미터 도출 — 전부 실측 필드에서 */
  const sp=DATA.species.filter(s=>s.eco&&s.temp);
  const TIER_PRED=new Set(['predator','hunter','ambusher','apex']);
  for(const s of sp){
    s.tl=s.temp[0]+(s.temp[1]-s.temp[0])*0.5;  /* 최적온도 = 밴드 중심 */
    s.tw=Math.max(2,(s.temp[1]-s.temp[0])/2);  /* 밴드 반경 */
    s.pred_=TIER_PRED.has(s.r);
  }
  const byId={};sp.forEach(s=>byId[s.id]=s);
  /* 2) 바이옴별 출연 종 + K 배분(10% 법칙 — 하위층 위주, 최상위 포식자는 전체의 약 10%를 나눠 가짐) */
  const bioSp={};
  for(const b of DATA.biomes){
    const ms=sp.filter(s=>s.bio.includes(b.name));
    const low=ms.filter(s=>!s.pred_),hi=ms.filter(s=>s.pred_);
    for(const s of low) s.Kb=Math.max(5,Math.round(b.K*0.55/Math.max(1,low.length)));
    for(const s of hi)  s.Kb=Math.max(2,Math.round(b.K*0.10/Math.max(1,hi.length))); /* 최상위 포식자는 희소 — 단 최소 2 */
    bioSp[b.id]=ms.map(s=>s.id);
  }
  /* 3) 시즌 굴리기 — 마르코프 이상기후 + 종별 φ + LV 교차항 */
  function run(bid,nSeasons,reroll){
    if(reroll)seed=(Date.now()%2147483647)||1;
    const bio=DATA.biomes.find(x=>x.id===bid);
    const ids=bioSp[bid]||[];
    const st=ids.map(id=>({s:byId[id],N:byId[id].Kb*0.6,ext:false}));
    const [T0,Tlo,Thi]=bio.cl,bw=Thi-Tlo,Topt=(Tlo+Thi)/2;
    let season=1,anom=1; /* 1=평년 */
    const hist=[{se:1,nm:'평년',cols:'#9a90b8',pop:st.map(o=>({id:o.s.id,n:o.N}))}];
    const dt=0.05,STEPS=400;
    for(let se=0;se<nSeasons;se++){
      /* 마르코프 이상기후 전이 */
      const p=MK.P[anom],u=rand();anom=u<p[0]?0:(u<p[0]+p[1]?1:2);
      const off=anom===0?-MK.OFF*bw:(anom===2?MK.OFF*bw:0),T=T0+off;
      for(const o of st){
        if(o.ext)continue;
        const phi=Math.exp(-Math.pow((T-o.s.tl)/o.s.tw,2));
        const r=Math.max(0.05,o.s.eco.rep*phi);
        const K=Math.max(2,o.s.Kb*(0.25+0.75*phi));
        const d=Math.min(0.9,0.05+o.s.eco.food*0.8*(1+0.4*(1-phi)));
        o.r=r;o.K=K;o.d=d;
      }
      for(let i=0;i<STEPS;i++){
        for(const o of st){
          if(o.ext)continue;
          let loss=0;
          for(const q of st){
            if(q.ext||q===o)continue;
            const eats=o.s.prey.some(pp=>pp.id===q.s.id);
            if(eats){
              const aff=0.004+0.012*(o.s.eco.agg||0.3);
              loss+=aff*q.N/(20+q.N); /* Holling II 스케일 */
            }
          }
          const dN=o.r*o.N*(1-o.N/o.K)-loss*o.N-o.d*o.N*0.2;
          o.N=Math.max(0,o.N+dN*dt);
        }
      }
      /* 국소절멸 · 이주 재유입 */
      for(const o of st){
        if(o.N<0.05){o.ext=true;o.N=0;}
        else if(o.ext===true&&se>0){/* no revive mid-season */}
        if(!o.ext&&o.N>o.K*1.02)o.N=o.K*1.02;
      }
      if(se<nSeasons-1){
        for(const o of st){
          if(o.ext&&rand()<0.25){o.ext=false;o.N=byId[o.s.id].Kb*0.05+0.05;} /* 이주 재유입 */
        }
      }
      hist.push({se:se+2,nm:MK.names[anom],cols:MK.cols[anom],pop:st.map(o=>({id:o.s.id,n:o.N}))});
    }
    return {hist,ids,T0};
  }
  /* 4) 렌더링 — 캔버스(층별 총량) + 표(종별 시즌 개체수) */
  const sel2=$('simBio');
  for(const b of DATA.biomes){const o=document.createElement('option');o.value=b.id;o.textContent=`${b.name} (${(bioSp[b.id]||[]).length}종)`;sel2.appendChild(o);}
  const TCOL={amb:'#8fce6a',dec:'#b08ce0'};
  let last=null;
  function render(){
    const nS=+$('simSeasons').value;
    last=run(sel2.value,nS,true);
    const cv=$('simcv'),g=cv.getContext('2d');
    g.clearRect(0,0,cv.width,cv.height);
    const hist=last.hist,pad=34,W=cv.width-pad-10;
    const maxY=Math.max(...hist.map(h=>Math.max(1,...h.pop.map(p=>p.n))))*1.1;
    const X=se=>pad+(se-0.5)/(hist.length-1)*W,Y=v=>cv.height-12-v/maxY*(cv.height-24);
    /* 계절 배경 */
    g.font='11px sans-serif';
    for(let i=0;i<hist.length;i++){
      const x0=pad+(Math.max(0,i-0.5))/(hist.length-1)*W,x1=pad+(Math.min(hist.length-1,i+0.5))/(hist.length-1)*W;
      g.fillStyle=hist[i].cols;g.globalAlpha=.12;g.fillRect(x0,0,x1-x0,cv.height-12);g.globalAlpha=1;
      g.fillStyle=hist[i].cols;g.fillText(hist[i].nm,x0+4,12);
    }
    /* 층별 총량 곡선 — 하위(먹이·분해·생산) / 중위·최상위(포식 역할 전체) */
    const layer=()=>{
      const L=[[],[],[]];
      for(const h of hist){let a=0,b2=0,c=0;
        for(const p of h.pop){const s=byId[p.id];
          if(s.pred_){if(s.k==='mon'&&(s.tier||0)>=4)c+=p.n;else b2+=p.n;}
          else a+=p.n;}
        L[0].push(a);L[1].push(b2);L[2].push(c);}
      return L;};
    const L=layer();
    const COLS=['#8fce6a','#e06a6a','#ff5252'];
    L.forEach((arr,li)=>{g.strokeStyle=COLS[li];g.lineWidth=li===0?2.4:2;g.beginPath();
      arr.forEach((v,i)=>{const x=X(i+1),y=Y(v);i?g.lineTo(x,y):g.moveTo(x,y);});g.stroke();});
    g.fillStyle='#9a90b8';g.fillText('개체수',pad-26,14);g.fillText('시즌 →',pad+W-34,cv.height-2);
    /* 표 */
    const rows=last.ids.map(id=>{
      const s=byId[id];
      const cells=hist.map(h=>{const p=h.pop.find(x=>x.id===id);const v=p?p.n:0;
        const col=v<0.05?'#5a5470':(v>s.Kb*0.8?'#ffd98a':'#cfc6ee');
        return `<td style="text-align:right;color:${col};padding:2px 6px">${v<0.05?'✝':v.toFixed(1)}</td>`;}).join('');
      const clr=s.k==='mon'?'#ffd98a':(TCOL[s.r]||'#cfc6ee');
      return `<tr><td style="color:${clr};padding:2px 6px;white-space:nowrap">${s.name}</td><td style="color:#5a5470;padding:2px 4px">K${s.Kb}</td>${cells}</tr>`;
    }).join('');
    const head=hist.map((h,i)=>`<th style="color:${h.cols};text-align:right;padding:2px 6px">S${i+1} ${h.nm}</th>`).join('');
    $('simTable').innerHTML=`<tr><th style="text-align:left;color:var(--dim)">종</th><th></th>${head}</tr>${rows}`;
    const ext=last.ids.filter(id=>hist[hist.length-1].pop.find(p=>p.id===id).n<0.05).length;
    $('simInfo').textContent=`${last.ids.length}종 · 최종 생존 ${last.ids.length-ext} · 절멸 ${ext}`;
  }
  sel2.addEventListener('change',render);
  $('simRun').addEventListener('click',render);
  $('simSeasons').addEventListener('change',render);
  return {render};
})();
document.addEventListener('click',e=>{
  if(e.target.classList.contains('jump')){
    sel.value=e.target.dataset.b;
    document.querySelector('[data-p="sim"]').click();
    preset();}});
renderCho();renderDex();preset();
</script>
</body>
</html>"""

ROKO_JSON = json.dumps(ROLE_KO, ensure_ascii=False)
ok = sum(1 for b in biomes if b["complete"])
html = (html.replace("__CONCEPTS__", concepts_html)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__ROKO__", ROKO_JSON)
            .replace("__NAMB__", str(len(amb)))
            .replace("__NMON__", str(len(mon)))
            .replace("__NPLAN__", str(data["nPlan"]))
            .replace("__NSP__", str(data["nSp"]))
            .replace("__NEDGE__", str(edges))
            .replace("__NOK__", str(ok)))
open(OUT, "w", encoding="utf-8").write(html)
print(f"OK — {OUT} ({len(biomes)}바이옴 · 사슬완결 {ok}/20 · 통로 {edges} · 종사전 {data['nSp']}종 = 야생 {len(amb)} + 전투 {len(mon)} + 예정 {data['nPlan']})")
