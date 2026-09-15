#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sim_economy.py — 소울커맨더 영지 재화 흐름 시뮬레이터 (가안 검증용)
GDD_v8.0_04_영지.md §3 상수 기준 · 미정G 튜닝 시 재실행 목적

시나리오:
- baseline: 평시 — 계절·사건·민심 보정 없음 (§3.11 수지표와 동일 조건)
- stress  : 최악 중첩 —
    · 겨울 전 기간 지속 (식량 수확 ×0.70 — §3.13. 계절 1바퀴 = 섬 365일이라 런 50섬일 전체가
      한 계절 안에 들어감 → "겨울에 시작한 런" = 전 구간 겨울이 현실적으로 가능한 최악)
    · 흉작 10섬일 주기 3일간 (식량 ×0.70 — §3.12 사건)
    · 도적 12섬일 주기 (금고 -10% + 채집팀 1팀 2일 차출 = 수확 -1팀분 — §3.12)
    · 민심 25 (파업 임계 20 직전 — 생산 보정 (25-50)/50×20% = -10% — §3.5)
    최악 순간 생산 배율 = 0.70×0.70×0.90×(팀-1)/팀

가정 (전부 가안 — 문서에 명시된 값 우선, 미정의 값은 §3.11 수지표와 정합되게 보간):
- 런 페이스: 층/일 구간별 (F1-10: 3.0, F11-25: 2.5, F26-80: 2.0, F81-100: 1.5)
- 인구: 수지표 행 정합 보간 (F1:30 → F5:60 → F17:150 → F40:400 → F55:1300)
- 채집팀: 해금층 1/15/35/45/60 (§3.11 가정) · 팀당 150 × (1+층/50) · L6 +15% / L7 +30%
- 농사: 필지 = 인구÷20 × 15식량 · 식당 ×1.2 (10층+)
- 건설비 (미정 → 누적 골드 10~20%선 가안): 전술소 1,000(확정) · F10 3종 각 1,000 ·
  F20 2종 각 3,000 · F30 2종 각 5,000 · 주택 동당 800 + 업글 1,000×Lv
- 업글비 (미정 → 기하급수 가안): L→L+1 = 3,000×2^(L-1) (L1→2 = 3,000 — 10층 밀집 메모와 정합)
- 정책: 우선순위 시설 [소환제단·식당·훈련장] L7 우선, 잉여금으로 순차 업글 · 골드 버퍼 20% 유지
- 소환: 마석 버퍼 10,000 초과분 전량 소환 (티켓 130) · 초회 10 무료 (무료분도 추출 대상) · 배치 36명 제외 전량 추출
- 주민 세금: 플랫 +1G/명·클리어 (2026-09-15 재설계 — 층 배율 폐지분) · 루프에 실제 반영
- 승급: 결정·골드 즉시 집행 (★5 파티 5인 → F50 캘리브레이션 목표 · ★6 완성 시점은 설계 목표 아님 — 100층까지 가능하면 충분, 2026-09-15 사용자 결정 — 관측 지표로만 출력)
- 아사 룰 (§3.14): 식량 0 지속 3층부터 인구 -2%/층 — 세금·소비·농지에 반영
- 미적용 (의도적 제외): 합성비 할인 -5×(Lv-1)%·추출환원 +10×(Lv-1)% (§3.10) — §3.1-2 캘리브레이션 기준 유지 (시설 보너스는 상향 여유분) · 식민섬 보너스 (§3.8-2 미결) · 재료 매각 · 칙령(채집장려 완화 미적용 — 순수 최악) · 전당의 은혜 (100층 이벤트 — N 미정I)
"""
from math import floor as fl

# ---------- 상수 (04 §3) ----------
TICKET = 130                    # 소환 티켓 마석
P_GRADE = [0.7004, 0.20, 0.07, 0.02884, 0.0005, 0.0001]   # ★1~★6 (미정B)
CRYSTAL = [1, 3, 10, 30, 100, 300]                        # 등급별 영혼 결정
E_CRYSTAL = sum(p*c for p, c in zip(P_GRADE, CRYSTAL))    # 소환 1회 기대 결정
STAFF = 36                      # 배치 수요 상한 (§3.2)
FREE_SUMMONS = 10               # 무료 소환 (00 #17)
PROMO = {                       # 승급 비용 (결정, 골드) — §3.1-2
    (1, 2): (25, 50), (2, 3): (100, 200), (3, 4): (375, 750),
    (4, 5): (1200, 2400), (5, 6): (3000, 5000),
}
PROMO_TOTAL_5 = sum(PROMO[(s, s+1)][0] for s in range(1, 5))   # ★1→★5
PROMO_TOTAL_6 = PROMO_TOTAL_5 + PROMO[(5, 6)][0]               # ★1→★6
GOLD_TOTAL_5 = sum(PROMO[(s, s+1)][1] for s in range(1, 5))
GOLD_TOTAL_6 = GOLD_TOTAL_5 + PROMO[(5, 6)][1]

FACILITIES = 10                 # 유지비 대상 시설 수 (주택·전당 제외)
MAINT_PER_LV = 10               # G/Lv/섬 하루 (§3.12)
EXPANSION = {10: 3000, 25: 10000, 50: 30000}   # S2/S3/S4 (§3.8)
BUILD = {4: 1000, 10: 3000, 20: 6000, 30: 10000}  # 시점: 총액 (가안)
UP_COST = lambda l: 3000 * 2 ** (l - 1)        # L→L+1 (가안)
PRIORITY = ["소환제단", "식당", "훈련장"]       # L7 우선 정책
GOLD_BUFFER = 0.20

MILESTONES = (10, 17, 25, 50, 55, 60, 80, 95, 100)

# ---------- 시나리오 (§3.5·§3.12·§3.13·§3.14 가안) ----------
SCENARIOS = {
    "baseline": dict(winter=False, famine_every=0, bandit_every=0, morale=50),
    "stress":   dict(winter=True,  famine_every=10, bandit_every=12, morale=25),
    # 10층 파산점 해결안 3종 (§3.11 발견 1 — 2026-09-15 비교 검증)
    "fixA":     dict(winter=False, famine_every=0, bandit_every=0, morale=50, start_gold=5000),     # A안: 시작 골드 5,000
    "fixB":     dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=12),        # B안: S2 확장 12층 지연
    "fixB13":   dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=13),        # B안 변형: S2 확장 13층 지연
    "fixC":     dict(winter=False, famine_every=0, bandit_every=0, morale=50, build_discount=0.5), # C안: 10층 건설비 3종만 50% 감면
    # 완화 장치 검증 (스트레스 동일 조건 + 완화 1개씩 — 2026-09-15)
    "mitig_decree": dict(winter=True, famine_every=10, bandit_every=12, morale=25, decree_harvest=True),   # 채집장려 칙령
    "mitig_stock":  dict(winter=True, famine_every=10, bandit_every=12, morale=25, stockpile=True, stockpile_target=500),  # 재고 운영 (저속 클리어)
    "mitig_both":   dict(winter=True, famine_every=10, bandit_every=12, morale=25, decree_harvest=True, stockpile=True, stockpile_target=500),  # 둘 다
    # 클러스터 재설계안 (전부 D-251 B안 s2_floor=12 기반 — 2026-09-15)
    "cluster_S1": dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=12, s3_floor=28),              # S3 확장 28층 지연
    "cluster_S2": dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=12, split_expansion=True),     # 확장비 분할 50%+3층후 50%
    "cluster_S3": dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=12, start_gold=2000),          # 시작 골드 2,000 (소액 보완)
    "cluster_S4": dict(winter=False, famine_every=0, bandit_every=0, morale=50, s2_floor=12, split_expansion=True, start_gold=2000),  # 분할+소액 조합
}

def pop_at(f):
    """수지표 행 정합 보간"""
    if f <= 1: return 30
    if f <= 5: return fl(30 + (60 - 30) * (f - 1) / 4)
    if f <= 17: return fl(60 + (150 - 60) * (f - 5) / 12)
    if f <= 40: return fl(150 + (400 - 150) * (f - 17) / 23)
    if f <= 55: return fl(400 + (1300 - 400) * (f - 40) / 15)
    return 1300

def teams_at(f):
    if f < 15: return 1
    if f < 35: return 2
    if f < 45: return 3
    if f < 60: return 4
    return 5

def pace_at(f):
    if f <= 10: return 3.0
    if f <= 25: return 2.5
    if f <= 80: return 2.0
    return 1.5

# ---------- 시뮬 본체 ----------
def run_sim(name, scn):
    gold, mana, crystal, food = scn.get("start_gold", 200.0), 0.0, 0.0, scn.get("start_food", 100.0)
    lv = {n: 1 for n in ["소환제단", "병원", "전술소", "훈련장", "식당", "숙소",
                         "연구소", "연금술소", "합성소", "추출소"]}
    lv["소환제단"] = 0   # 제단은 채집팀 +1/Lv — 초기 1팀은 기본 제공으로 모델링
    build_done, expansions_done = set(), set()
    pending_split = {}   # 확장비 분할 (split_expansion) — 잔여 50% 지급 예정表 {층: 금액}
    summons_total, summons_free_left = 0, FREE_SUMMONS
    staffed = 0
    crystal_earned = crystal_spent = 0
    promoted = {}
    party5_done_floor = party6_done_floor = None
    maint_total = 0.0
    cur_floor, day = 0, 0
    log = {}
    pop_loss, starve_run, starve_floors = 1.0, 0, 0
    food_zero_floor = gold_neg_floor = None
    food_min, food_min_f = food, 0
    gold_min, gold_min_f = gold, 0
    famine_days = bandit_hits = seized_days = 0
    worst_mult, worst_mult_f = 1.0, 0
    gold_spent_mitigation = 0.0   # 도적 금고 피해 합계

    def food_income(f, pop, t, seized):
        eff_t = max(t - (1 if seized else 0), 0)
        gather = eff_t * 150 * (1 + f / 50) * (1 + (0.15 if lv["소환제단"] >= 6 else 0) + (0.15 if lv["소환제단"] >= 7 else 0))
        farm = (pop // 20) * 15
        rest = 1.2 if f >= 10 else 1.0
        return (gather + farm) * rest

    while cur_floor < 100:
        day += 1
        pace = pace_at(max(cur_floor, 1))
        clears = min(int(pace + (0.5 if (day % 2) else 0)), 100 - cur_floor) or 1
        # --- 사건·계절 판정 (섬 하루 단위) ---
        winter = scn["winter"]
        famine = scn["famine_every"] > 0 and (day % scn["famine_every"]) in (0, 1, 2)
        bandit = scn["bandit_every"] > 0 and (day % scn["bandit_every"]) == 0
        seized = scn["bandit_every"] > 0 and (day % scn["bandit_every"]) in (0, 1)
        if scn.get("decree_harvest", False) and not scn.get("_decree_applied"):
            scn["morale"] = max(scn["morale"] - 5, 20)   # 채집장려 민심 비용 -5 (1회) — §3.7
            scn["_decree_applied"] = True
        morale_mult = 1 + (scn["morale"] - 50) / 50 * 0.20        # §3.5 수치화식
        decree_mult = 1.20 if scn.get("decree_harvest", False) else 1.0   # 채집·농사 +20% — §3.7
        season_mult = 0.70 if winter else 1.0                      # §3.13 겨울
        famine_mult = 0.70 if famine else 1.0                      # §3.12 흉작
        famine_days += 3 if famine else 0
        if bandit:
            bandit_hits += 1
            damage = gold * 0.10
            gold -= damage; gold_spent_mitigation += damage        # §3.12 도적 금고 -10%
        seized_days += 2 if seized else 0
        for _ in range(clears):
            cur_floor += 1
            f = cur_floor
            pop = pop_at(f) * pop_loss
            # 수입
            gold += 100 * f
            gold += pop          # 주민 세금 +1G/명·클리어 (플랫 — 2026-09-15 재설계 · 루프 반영)
            mana += 30 * f + (75 * f * f if f % 10 == 0 and f >= 10 else 0)
            # 확장 (해금 층수·분할 지급 시나리오별 — B안 지연·클러스터 완화 검증용)
            s2f = scn.get("s2_floor", 10)
            s3f = scn.get("s3_floor", 25)
            s4f = scn.get("s4_floor", 50)
            split = 0.5 if scn.get("split_expansion", False) else 1.0   # 해금 시 50% + 3층 후 잔여
            for ef, ec in ((s2f, 3000), (s3f, 10000), (s4f, 30000)):
                if f == ef and ef not in expansions_done:
                    expansions_done.add(ef); gold -= ec * split
                    if split < 1.0:
                        pending_split[ef + 3] = pending_split.get(ef + 3, 0) + ec * (1 - split)
            if f in pending_split:
                gold -= pending_split.pop(f)
            # 건설 (C안 감면 검증용 — 10층 3종에만 적용 · 전술소 1,000G는 확정 수치라 제외)
            if f in BUILD and f not in build_done:
                build_done.add(f)
                disc = scn.get("build_discount", 1.0) if f == 10 else 1.0
                gold -= BUILD[f] * disc
            for n in ["훈련장", "식당", "숙소"]:
                if f == 10 and n not in build_done: build_done.add(n)  # 비용은 BUILD[10]에 포함
            # 소환 + 추출 (무료 10회 포함 — 무료분도 추출 대상)
            while summons_total < 30000:
                if summons_free_left > 0:
                    summons_free_left -= 1
                elif (mana - (10000 if f > 10 else 0)) >= TICKET:
                    mana -= TICKET
                else:
                    break
                summons_total += 1
                if staffed < STAFF: staffed += 1
                else:
                    got = E_CRYSTAL * 1.1   # 레벨 보정 ×1.1 (§3.1-2 캘리브레이션 기준)
                    crystal += got; crystal_earned += got
            # 승급 집행 (합성소 30층+)
            if f >= 30:
                # ★5 파티
                p5 = promoted.get(5, 0)
                while p5 < 5 and crystal >= PROMO_TOTAL_5 and gold >= GOLD_TOTAL_5:
                    crystal -= PROMO_TOTAL_5; crystal_spent += PROMO_TOTAL_5
                    gold -= GOLD_TOTAL_5; promoted[5] = p5 = p5 + 1
                    if p5 == 5 and party5_done_floor is None: party5_done_floor = f
                p6 = promoted.get(6, 0)
                while p6 < 5 and crystal >= PROMO_TOTAL_6 and gold >= GOLD_TOTAL_6:
                    crystal -= PROMO_TOTAL_6; crystal_spent += PROMO_TOTAL_6
                    gold -= GOLD_TOTAL_6; promoted[6] = p6 = p6 + 1
                    if p6 == 5 and party6_done_floor is None: party6_done_floor = f
            # 업글 정책 (버퍼 20% 유지)
            order = sorted(lv, key=lambda n: (n not in PRIORITY, UP_COST(lv[n])))
            for n in order:
                if lv[n] >= 7: continue
                c = UP_COST(lv[n])
                if gold - c >= GOLD_BUFFER * (100 * 50):  # 버퍼 = 누적 기대 수입 20%
                    gold -= c; lv[n] += 1
            # 식량 정산 (사건·계절·민심 배율 적용)
            pop = pop_at(f) * pop_loss
            t = teams_at(f)
            prod = food_income(f, pop, t, seized) * season_mult * famine_mult * morale_mult * decree_mult
            if famine or seized:
                m = season_mult * famine_mult * morale_mult * (max(t - 1, 0) / t if seized else 1.0)
                if m < worst_mult: worst_mult, worst_mult_f = m, f
            cons = pop * pace_at(f)
            push = scn.get("harvest_push", 1.0)
            if scn.get("stockpile", False) and food < scn.get("stockpile_target", 500):
                cons *= 0.5   # 재고 운영: 재고 목표 미만이면 클리어 속도 절반 (재고 비축 우선)
            food += prod * push - cons
            if food < 0:
                starve_run += 1; starve_floors += 1
                if starve_run >= 3: pop_loss *= 0.98   # §3.14 아사 — 3층 지속 시 -2%/층
                if food_zero_floor is None: food_zero_floor = f
                food = 0
            else:
                starve_run = 0
            if food < food_min: food_min, food_min_f = food, f
            if gold < gold_min: gold_min, gold_min_f = gold, f
            if gold < 0 and gold_neg_floor is None: gold_neg_floor = f
            maint_total += MAINT_PER_LV * sum(lv.values())
            if f in MILESTONES:
                log[f] = (day, int(gold), int(mana), int(crystal), int(food))

    return dict(name=name, day=day, log=log, gold=gold, mana=mana, crystal=crystal,
                food=food, summons=summons_total, crystal_earned=crystal_earned,
                crystal_spent=crystal_spent, maint=maint_total,
                p5=party5_done_floor, p6=party6_done_floor, staffed=staffed, lv=lv,
                pop_loss=pop_loss, starve_floors=starve_floors,
                food_zero_floor=food_zero_floor, gold_neg_floor=gold_neg_floor,
                food_min=food_min, food_min_f=food_min_f,
                gold_min=gold_min, gold_min_f=gold_min_f,
                famine_days=famine_days, bandit_hits=bandit_hits,
                seized_days=seized_days, worst_mult=worst_mult, worst_mult_f=worst_mult_f,
                bandit_damage=gold_spent_mitigation)

# ---------- 출력 ----------
results = [run_sim(n, s) for n, s in SCENARIOS.items()]
for r in results:
    print("=" * 76)
    scn = SCENARIOS[r["name"]]
    tag = []
    if scn["winter"]: tag.append("전 기간 겨울 ×0.70")
    if scn["famine_every"]: tag.append(f"흉작 {scn['famine_every']}일 주기 ×0.70")
    if scn["bandit_every"]: tag.append(f"도적 {scn['bandit_every']}일 주기 (금고-10%+1팀 차출)")
    if scn["morale"] < 50: tag.append(f"민심 {scn['morale']} (×{1 + (scn['morale']-50)/50*0.20:.2f})")
    print(f"[{r['name']}] 런 {r['day']}일" + (" — " + " · ".join(tag) if tag else " — 평시"))
    print("=" * 76)
    print(f"{'층':>4} {'일':>4} {'골드':>10} {'마석':>9} {'결정':>8} {'식량':>8}")
    for f, (d, g, m, c, fd) in sorted(r["log"].items()):
        print(f"{f:>4} {d:>4} {g:>10,} {m:>9,} {c:>8,} {fd:>8,}")
    print("-" * 76)
    print(f"유지비 총액            : {int(r['maint']):>12,} G")
    print(f"소환 총횟수            : {r['summons']:>12,} 회")
    print(f"결정 획득/지출         : {int(r['crystal_earned']):,} / {int(r['crystal_spent']):,}")
    print(f"★5 파티 완성          : {r['p5']}층 (목표 50) · ★6 파티: {r['p6']}층 (참고값 — 설계 목표 아님)")
    print(f"식량 최저 재고         : {int(r['food_min']):,} ({r['food_min_f']}층) · 아사 층수: {r['starve_floors']}"
          + (f" · 최초 식량 0: {r['food_zero_floor']}층" if r["food_zero_floor"] else ""))
    print(f"골드 최저              : {int(r['gold_min']):,} G ({r['gold_min_f']}층)"
          + (f" · 최초 골드 <0: {r['gold_neg_floor']}층" if r["gold_neg_floor"] else " · 파산 없음"))
    if r["starve_floors"] > 0 or r["name"] == "stress":
        print(f"흉작/도적/차출         : {r['famine_days']}일 / {r['bandit_hits']}회 / {r['seized_days']}일 · 도적 피해 합계 {int(r['bandit_damage']):,}G")
        print(f"최악 생산 배율         : ×{r['worst_mult']:.2f} ({r['worst_mult_f']}층 시점)")
        print(f"인구 손실 (아사 누적)  : -{(1 - r['pop_loss']) * 100:.1f}%")

# ---------- 비교 요약 ----------
b, s = results[0], results[1]
print()
print("#" * 76)
print("# 무너지는 지점 요약 (baseline vs stress)")
print("#" * 76)
rows = [
    ("최초 식량 0 (아사 시작)", f"{b['food_zero_floor']}층" if b["food_zero_floor"] else "없음",
     f"{s['food_zero_floor']}층" if s["food_zero_floor"] else "없음"),
    ("아사 누적 층수", f"{b['starve_floors']}", f"{s['starve_floors']}"),
    ("인구 손실", f"-{(1 - b['pop_loss']) * 100:.1f}%", f"-{(1 - s['pop_loss']) * 100:.1f}%"),
    ("최초 골드 <0", f"{b['gold_neg_floor']}층" if b["gold_neg_floor"] else "없음",
     f"{s['gold_neg_floor']}층" if s["gold_neg_floor"] else "없음"),
    ("골드 최저", f"{int(b['gold_min']):,} G ({b['gold_min_f']}층)", f"{int(s['gold_min']):,} G ({s['gold_min_f']}층)"),
    ("★5 파티 (목표 50)", f"{b['p5']}층", f"{s['p5']}층"),
    ("★6 파티 (참고값 — 목표 아님)", f"{b['p6']}층", f"{s['p6']}층"),
    ("런 소요", f"{b['day']}일", f"{s['day']}일"),
]
w = max(len(x) for x, _, _ in rows) + 2
print(f"{'지표':<{w}}{'baseline':>28}{'stress(최악)':>28}")
for label, bv, sv in rows:
    print(f"{label:<{w}}{bv:>28}{sv:>28}")

# ---------- 파산점 해결안 비교 (fixA/B/C) ----------
fixes = [r for r in results if r["name"].startswith("fix")]
if fixes:
    print()
    print("#" * 76)
    print("# 10층 파산점 해결안 비교 (§3.11 발견 1 — greedy 업글 정책 하)")
    print("#" * 76)
    print(f"{'안':<8}{'10층 골드':>14}{'최초 <0':>10}{'골드 최저':>16}{'★5':>6}{'★6':>6}{'100층 골드':>14}")
    for r in fixes:
        g10 = r["log"].get(10, (0, 0, 0, 0, 0))[1]
        g100 = r["log"].get(100, (0, 0, 0, 0, 0))[1]
        neg = f"{r['gold_neg_floor']}층" if r["gold_neg_floor"] else "없음"
        print(f"{r['name']:<8}{g10:>14,}{neg:>10}{int(r['gold_min']):>13,} G{r['p5']:>5}층{r['p6']:>5}층{g100:>14,}")
    g10b = b["log"].get(10, (0, 0, 0, 0, 0))[1]
    print(f"{'baseline':<8}{g10b:>14,}{('' if not b['gold_neg_floor'] else str(b['gold_neg_floor'])+'층'):>10}{int(b['gold_min']):>13,} G{b['p5']:>5}층{b['p6']:>5}층{b['log'][100][1]:>14,}")

# ---------- 클러스터 재설계안 비교 (cluster_*) ----------
clusters = [r for r in results if r["name"].startswith("cluster")]
if clusters:
    print()
    print("#" * 76)
    print("# 지출 클러스터 재설계안 비교 (25·50층 — 전부 D-251 기반)")
    print("#" * 76)
    print(f"{'안':<12}{'25층 잔고':>12}{'50층 잔고':>12}{'최초 <0':>10}{'골드 최저':>15}{'★5':>6}{'★6':>6}")
    for r in clusters:
        g25 = r["log"].get(25, (0, 0, 0, 0, 0))[1]
        g50 = r["log"].get(50, (0, 0, 0, 0, 0))[1]
        neg = f"{r['gold_neg_floor']}층" if r["gold_neg_floor"] else "없음"
        print(f"{r['name']:<12}{g25:>12,}{g50:>12,}{neg:>10}{int(r['gold_min']):>13,} G{r['p5']:>5}층{r['p6']:>5}층")
