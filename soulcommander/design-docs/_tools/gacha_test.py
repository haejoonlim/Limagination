#!/usr/bin/env python3
"""소울 커맨더 뽑기 시뮬레이터 v2 — GDD_v8.0_05 전체 반영 (2026-09-14)

반영 규칙:
- 등급 확률표 (00 미정B): ★1 70.04 / ★2 20 / ★3 7 / ★4 2.9 / ★5 0.05 / ★6 0.01
- 계열 6 (부족보정 +0.2 · 픽업 3배) → 종족 15 → 아종 34 (런칭 13종 게이트)
- 직업 13 (공통 8 + 계열 희귀 5%) · 성격 13종 (성실 신규 · 요행 삭제 · 중립→무자비 교체 · 가중치 롤 · 10연차 중복 방지 — 2026-09-14 4차)
- 적성 13 — 직업 정합: 프로필 ±1 · 비프로필 전투 1~2 캡 · 생활 1~5 (05 §6 3차)
- 스탯 13종 = 기본×직업×등급 × 종족·아종 statMods(%) × 성격 실반영 × 개체 변량 ±8% + CP ①식 (05 §7)
- 소환 단가 130석 · 무료 10회 · 쿼터 = 2×인구상한
- 이름 재추첨 (중복 최대 8회) · 등급×종족 독립

실행: python3 gacha_test.py [층수] [연차수] [--pickup 계열]
"""
import hashlib
import random
import sys
from collections import Counter

rng = random.Random(20260914)  # 모듈 기본 — main()에서 실행마다 재설정 (--seed로 고정 재현)

# ── 정본 데이터 (05 문서 §2~§7 · races.json) ──────────────────────────
RATES = {'★1': 0.7004, '★2': 0.20, '★3': 0.07, '★4': 0.029, '★5': 0.0005, '★6': 0.0001}
GRADE_MULT = {1: 1.0, 2: 1.30, 3: 1.69, 4: 2.20, 5: 2.86, 6: 3.71, 7: 4.83}  # 등급당 ×1.3 복리 (2026-09-14 2차 개정)

LINEAGES = ['인간', '엘프', '드워프', '짐승', '전사', '심연']
# (계열 → [(종족, [아종...], 해금층)] — unlock: 인간0·엘프0·드워프0·짐승0 · 시 엘프 update1·조인 update5
RACE_MAP = {
    '인간':  [('인간',   ['초원의 인간', '바다의 인간', '황야의 인간'], 0),
              ('정령족', ['불의 정령족', '대지의 정령족', '물의 정령족', '바람의 정령족', '달의 정령족'], 0)],
    '엘프':  [('하이 엘프', ['태양 엘프', '달 엘프'], 0),
              ('우드 엘프', ['심림 엘프', '초원 엘프'], 0),
              ('다크 엘프', ['지하 엘프', '심연 엘프'], 0),
              ('시 엘프', ['산호 엘프', '폭풍 엘프'], 1)],
    '드워프': [('드워프', ['산악 드워프', '빙원 드워프'], 0),
              ('노움', ['바위 노움', '그림자 노움'], 0),
              ('하프링', ['섬 하프링', '습지 하프링'], 0)],
    '짐승':  [('묘인족', ['표범 묘인족', '살쾡이 묘인족'], 0),
              ('견인족', ['사냥개 견인족', '경비견 견인족'], 0),
              ('조인족', ['독수리 조인족', '까마귀 조인족'], 5),
              ('리자드맨', ['늪지 리자드맨', '사막 리자드맨'], 0)],
    '전사':  [('오크', ['산악 오크', '대초원 오크'], 9)],
    '심연':  [('뱀파이어', ['고귀한 뱀파이어', '야행 뱀파이어'], 13)],
}

JOB_COEF = {  # (HP ATK DEF ASPD MAG MDEF CRI)
    '전사':     (1.2, 1.0, 1.0, 1.0, 0.5, 1.0, 1.05),
    '수호자':   (1.8, 0.7, 1.5, 0.8, 0.4, 1.5, 1.0),
    '암살자':   (0.8, 1.3, 0.6, 1.4, 0.5, 0.6, 1.3),
    '궁수':     (0.9, 1.1, 0.7, 1.2, 0.5, 0.7, 1.2),
    '마법사':   (0.7, 0.8, 0.5, 0.9, 1.5, 1.4, 1.1),
    '지원가':   (0.9, 0.6, 0.8, 1.1, 1.2, 1.2, 1.0),
    '성기사':   (1.6, 0.8, 1.3, 0.8, 0.7, 1.3, 1.1),
    '드루이드': (1.0, 0.7, 0.9, 0.9, 1.3, 1.3, 1.0),
    '광전사':   (1.4, 1.6, 0.5, 1.0, 0.3, 0.5, 1.4),
    '심연술사': (0.8, 0.9, 0.6, 0.9, 1.8, 1.6, 1.2),
    '광산기사': (1.5, 1.0, 1.4, 0.7, 0.5, 1.2, 1.0),
    '질풍사냥꾼': (1.0, 1.2, 0.7, 1.8, 0.4, 0.8, 1.2),
    '현자':     (0.8, 0.7, 0.7, 0.9, 1.6, 1.7, 1.3),
}
RARE_JOBS = {'전사': '광전사', '심연': '심연술사', '드워프': '광산기사',
             '짐승': '질풍사냥꾼', '인간': '현자', '엘프': '현자'}
RARE_JOB_RATE = 0.05

PERSONALITIES = ['용감', '신중', '냉정', '광폭', '헌신', '교활', '무자비',
                 '불굴', '낭만', '고집', '성실', '천애', '백전노장']
P_MULT = {'용감': 1.03, '신중': 1.02, '냉정': 1.02, '광폭': 1.04, '헌신': 1.02,
          '교활': 1.02, '무자비': 1.03, '불굴': 1.03, '낭만': 1.01,
          '고집': 1.02, '성실': 1.02, '천애': 1.05, '백전노장': 1.04}
P_RARE = {'천애': '★4+', '백전노장': 'Lv30+'}  # 조건부 (백전노장은 시뮬에서 Lv0 기준 비출현)
# 성격 가중치 롤 (05 §5 4차 개정 — 균등 폐지 · 성실 신규 · 요행 삭제 · 중립→무자비 교체). 백전노장은 Lv30+ 재롤 전용이라 롤 제외.
P_WEIGHT = {'용감': 9, '신중': 9, '냉정': 8, '광폭': 8, '헌신': 8, '교활': 8,
            '무자비': 8, '불굴': 8, '낭만': 7, '고집': 9, '성실': 8, '천애': 2}
# 성격 → 스탯 실반영 (01 §4 가안 — CP의 P와 병행)
PERS_STAT_MUL = {'용감': {'ATK': 1.05}, '신중': {'DEF': 1.05},
                 '광폭': {'ATK': 1.08, 'DEF': 0.97}, '헌신': {'MAG': 1.10}}  # 헌신: 치유+10% → MAG
PERS_STAT_PPT = {'냉정': {'CRI': 3.0}, '교활': {'EVA': 5.0}, '무자비': {'CDMG': 10.0}}  # %p 가산
VARIANCE = 0.07   # 개체 변량 ±7% (2026-09-14 확정 — 8% → 7% 사용자 조정)
PCT_KEYS = frozenset(('CRI', 'EVA', 'PEN', 'CDMG'))

# 적성 직업 프로필 (05 §6 안A — 전투 5종 기준값, 광산기사는 광부 포함)
COMBAT_APT = ('근접', '원거리', '마법', '방어', '공속')
JOB_APT = {
    '전사': {'근접': 4, '방어': 3, '공속': 3}, '수호자': {'방어': 5, '근접': 3, '공속': 2},
    '암살자': {'공속': 5, '원거리': 3, '근접': 3}, '궁수': {'원거리': 5, '공속': 3, '근접': 2},
    '마법사': {'마법': 5, '공속': 2, '방어': 2}, '지원가': {'마법': 4, '방어': 3, '근접': 2},
    '성기사': {'방어': 4, '근접': 3, '마법': 3}, '드루이드': {'마법': 4, '방어': 3, '근접': 2},
    '광전사': {'근접': 5, '공속': 4, '방어': 1}, '심연술사': {'마법': 5, '방어': 3, '원거리': 3},
    '광산기사': {'방어': 4, '근접': 3, '광부': 4}, '질풍사냥꾼': {'공속': 5, '근접': 4, '방어': 2},
    '현자': {'마법': 4, '공속': 3, '원거리': 3},
}

# 종족·아종 statMods (races.json 정본 → 표시 13종 키, %보정 가안: ×(1+값/100))
# cool(쿨타임 −N) → SPD_CAST +N% 가안 · hpRegenPer4sPct는 13종 외 제외
RACE_MODS = {
    '인간': {}, '정령족': {}, '하이 엘프': {'MAG': 10}, '우드 엘프': {'ASPD': 10},
    '다크 엘프': {'CRI': 5, 'MAG': 5}, '시 엘프': {'HP': 5, 'MAG': 5},
    '드워프': {'DEF': 10, 'HP': 5}, '노움': {'MAG': 5, 'SPD_CAST': 5},
    '하프링': {'ASPD': 8, 'EVA': 5}, '묘인족': {'ASPD': 8, 'CRI': 3},
    '견인족': {'HP': 5, 'ATK': 5}, '조인족': {'ASPD': 10},
    '리자드맨': {'DEF': 8, 'HP': 5}, '오크': {'HP': 8, 'ATK': 8},
    '뱀파이어': {'MAG': 8, 'CRI': 3},
}
SUB_MODS = {
    '초원의 인간': {'ASPD': 3}, '바다의 인간': {'HP': 3}, '황야의 인간': {'ATK': 3},
    '불의 정령족': {'ATK': 3}, '대지의 정령족': {'DEF': 5}, '물의 정령족': {'HP': 3},
    '바람의 정령족': {'ASPD': 5}, '달의 정령족': {},
    '태양 엘프': {'MAG': 3}, '달 엘프': {'SPD_CAST': 3}, '심림 엘프': {'CRI': 3},
    '초원 엘프': {'HP': 3}, '지하 엘프': {'CRI': 2}, '심연 엘프': {'MAG': 3},
    '산호 엘프': {'HP': 3}, '폭풍 엘프': {'MAG': 3},
    '산악 드워프': {'DEF': 5}, '빙원 드워프': {'HP': 5}, '바위 노움': {'MAG': 3},
    '그림자 노움': {'EVA': 3}, '섬 하프링': {'HP': 3}, '습지 하프링': {'EVA': 3},
    '표범 묘인족': {'CRI': 2}, '살쾡이 묘인족': {'EVA': 3}, '사냥개 견인족': {'ATK': 3},
    '경비견 견인족': {'DEF': 3}, '독수리 조인족': {'ATK': 3}, '까마귀 조인족': {'MAG': 3},
    '늪지 리자드맨': {'HP': 3}, '사막 리자드맨': {'ATK': 3},
    '산악 오크': {'DEF': 3}, '대초원 오크': {'ATK': 3},
    '고귀한 뱀파이어': {'MAG': 3}, '야행 뱀파이어': {'ATK': 3},
}

COMMON_APT = ['근접', '원거리', '마법', '방어', '공속',
              '채집', '벌목', '농부', '목수', '광부']
# 희귀 적성 13 — 공용 6 + 종족 전용 7 (05 §6 · 2026-09-14 2차 개정)
COMMON_RARE_APT = ['용광로', '야생심', '심연감각', '왕의 혈맥', '정령 조화', '전쟁의 기억']
RACE_RARE_APT = {
    '인간': '왕의 혈맥', '정령족': '달의 심장',
    '하이 엘프': '숲의 언어', '우드 엘프': '숲의 언어', '다크 엘프': '숲의 언어', '시 엘프': '숲의 언어',
    # ↑ 버그 수정 (2026-09-14 3차): '엘프' 키는 롤 결과에 절대 없음 — 엘프 4분파 전부 직접 매핑 (05 §6)
    '드워프': '산맥의 뼈', '노움': '산맥의 뼈', '하프링': '산맥의 뼈',
    '묘인족': '무리의 본능', '견인족': '무리의 본능', '리자드맨': '무리의 본능',
    '조인족': '폭풍의 날개', '오크': '타천의 근육', '뱀파이어': '피의 기억',
}
RARE_APT_RATE = 0.05

# 소환 단가 130석 · 무료 10회 (00 #16·#17)
TICKET_COST = 130
FREE_SUMMONS = 10
# 수급: 퇴장 층×30×(1+0.2×식민섬) + 게이트잭팟 층²×1,000 (04 §3.9)
MUL_COLONY = 0.2


def roll_grade(rng, pity):
    """등급 롤 — 천장 미정(00 미정A) → 순수 확률표"""
    r = rng.random()
    acc = 0.0
    for g in ['★1', '★2', '★3', '★4', '★5', '★6']:
        acc += RATES[g]
        if r < acc:
            return g
    return '★1'


def _weighted(rng, items):
    """items: [(key, weight)] — 가중치 랜덤 선택"""
    x = rng.random() * sum(w for _, w in items)
    acc = 0.0
    for k, w in items:
        acc += w
        if x < acc:
            return k
    return items[-1][0]


def roll_personality(rng, grade, exclude=()):
    """성격 롤 — 13종 가중치 · 배치 내 중복 제외 · 천애=★4+ 게이트 (05 §5 4차 개정)"""
    pool = [(p, w) for p, w in P_WEIGHT.items() if p not in exclude]
    if not pool:  # 10연차보다 긴 배치 — 풀 소진 시 원복
        pool = list(P_WEIGHT.items())
    pers = _weighted(rng, pool)
    if pers == '천애' and grade not in ('★4', '★5', '★6'):
        # 미정A 전에는 천애 미달을 중립 강제 전환 — 4차부터 가중치 재롤 (05 §5 4차)
        pool2 = [(p, w) for p, w in pool if p != '천애'] or list(P_WEIGHT.items())
        pers = _weighted(rng, pool2)
    return pers


def roll_lineage(rng, counts, pickup=None):
    """계열 롤 — 부족보정 +0.2/부족분 · 픽업 3배 (05 §5.6 승계)"""
    keys = [l for l in LINEAGES if counts.get('floor', 0) >= RACE_MAP[l][0][2] or
            any(g >= 1 for _, _, g in RACE_MAP[l])]
    keys = [l for l in keys if any(g <= counts.get('floor', 0) for _, _, g in RACE_MAP[l])]
    if not keys:
        keys = ['인간']
    owned = counts.get('owned', {})
    mx = max(owned.get(l, 0) for l in keys)
    w = []
    for l in keys:
        wt = 1.0 + (mx - owned.get(l, 0)) * 0.2
        if pickup == l:
            wt *= 3.0
        w.append(max(wt, 0.0))
    r = rng.random() * sum(w)
    acc = 0.0
    for l, wt in zip(keys, w):
        acc += wt
        if r < acc:
            return l
    return keys[-1]


def make_hero(rng, counts, floor, pickup=None, exclude_pers=()):
    lin = roll_lineage(rng, counts, pickup)
    owned = counts.setdefault('owned', {})

    # 종족 → 아종 (런칭 게이트 준수)
    avail = [(race, subs) for race, subs, gate in RACE_MAP[lin] if floor >= gate]
    if not avail:
        avail = [RACE_MAP[lin][0]]
    race, subs = rng.choice(avail)
    subrace = rng.choice(subs)

    grade = roll_grade(rng, counts.get('pity', 0))

    # 종족별 직업 가중치 (05 §4 — 2026-09-14)
    RACE_JOB = {
        '인간': {'전사': 1.2, '성기사': 1.2, '마법사': 1.1},
        '정령족': {'마법사': 1.7, '드루이드': 1.5, '지원가': 1.3, '전사': 0.4, '수호자': 0.7},
        '하이 엘프': {'마법사': 1.8, '지원가': 1.1, '전사': 0.3, '광전사': 0.2},
        '우드 엘프': {'궁수': 1.4, '드루이드': 1.4, '마법사': 0.7},
        '다크 엘프': {'암살자': 1.8, '마법사': 1.4, '수호자': 0.5},
        '시 엘프': {'궁수': 1.3, '지원가': 1.3, '전사': 0.6},
        '드워프': {'수호자': 1.5, '광산기사': 1.4, '암살자': 0.4, '마법사': 0.6},
        '노움': {'마법사': 1.3, '현자': 1.2, '전사': 0.6},
        '하프링': {'지원가': 1.4, '궁수': 1.2, '전사': 0.7},
        '묘인족': {'암살자': 1.5, '궁수': 1.3, '수호자': 0.7},
        '견인족': {'전사': 1.3, '수호자': 1.2, '마법사': 0.7},
        '조인족': {'궁수': 1.4, '전사': 0.8},
        '리자드맨': {'전사': 1.3, '질풍사냥꾼': 1.2, '마법사': 0.7},
        '오크': {'전사': 1.9, '수호자': 1.4, '마법사': 0.25, '암살자': 0.5},
        '뱀파이어': {'마법사': 1.6, '암살자': 1.4, '심연술사': 1.0, '전사': 0.6},
    }

    # 직업 — 계열 희귀 5% → 종족 가중치 롤
    common = [j for j in JOB_COEF if j not in set(RARE_JOBS.values())]
    if lin in RARE_JOBS and rng.random() < RARE_JOB_RATE:
        job = RARE_JOBS[lin]
    else:
        w = RACE_JOB.get(race, {})
        weights = [w.get(j, 1.0) for j in common]
        acc, x = 0.0, rng.random() * sum(weights)
        job = common[-1]
        for j, wt in zip(common, weights):
            acc += wt
            if x < acc:
                job = j
                break

    # 성격 — 14종 가중치 롤 (천애=★4+ 게이트 · 백전노장은 시뮬 Lv0이라 비출현)
    pers = roll_personality(rng, grade, exclude_pers)

    # 적성 13 — 직업 정합 롤 (05 §6 3차): 프로필 ±1 · 비프로필 전투 1~2 캡 · 생활 1~5
    prof = JOB_APT.get(job, {})
    apt = {}
    for k in COMMON_APT:
        if k in prof:
            apt[k] = min(5, max(1, prof[k] + rng.randint(-1, 1)))
        elif k in COMBAT_APT:
            apt[k] = rng.randint(1, 2)   # 직업 외 전투 적성 — 마법사 근접 5 방지
        else:
            apt[k] = rng.randint(1, 5)
    # 희귀 적성 — 뜨면 13종 희귀 풀 중 1개 확정 (공용 6 + 종족 전용)
    if rng.random() < RARE_APT_RATE:
        pool = list(COMMON_RARE_APT) + ([RACE_RARE_APT[race]] if race in RACE_RARE_APT else [])
        rare_apt = rng.choice(pool)
        apt[rare_apt] = rng.randint(3, 5)  # 희귀는 최소 3 (가안)
    else:
        rare_apt = None
    # 표시 필터 전에 희귀 태그 카운트용 필드 유지


    # 스탯 13종 (05 §7)
    gm = GRADE_MULT[int(grade[1])]
    hp, atk, df, aspd, mag, mdef, cri = JOB_COEF[job]
    st = {
        'HP': round(100 * hp * gm),
        'ATK': round(10 * atk * gm),
        'MAG': round(10 * mag * gm),
        'PEN': round(2.0 * (df - 0.5) * gm),
        'DEF': round(5 * df * gm),
        'MDEF': round(5 * mdef * gm),
        'EVA': round(3 + 2 * aspd * gm * 0.1),
        'ASPD': round(50 * aspd * gm),
        'CDMG': round(150 + 10 * cri * gm),
        'CRI': round(5 + 3 * (cri - 1) * gm),
        'MANA': round(100 * mdef * gm),
        'SPD_CAST': round(30 * mdef * gm),
        'STA': round(80 * hp * gm),
    }

    # 종족·아종 statMods (races.json — %보정 가안: ×(1+값/100))
    # 성격 → 스탯 실반영 (01 §4 가안) → 개체 변량 ±7% (2026-09-14 확정 — 8%→7% 조정)
    mods = {}
    for m in (RACE_MODS.get(race, {}), SUB_MODS.get(subrace, {})):
        for k, v in m.items():
            mods[k] = mods.get(k, 0) + v
    mul = dict(PERS_STAT_MUL.get(pers, {}))
    ppt = dict(PERS_STAT_PPT.get(pers, {}))
    for k, v in mods.items():
        mul[k] = mul.get(k, 1.0) * (1.0 + v / 100.0)
    for k, f in mul.items():
        if k in st:
            st[k] *= f
    for k, p in ppt.items():
        if k in st:
            st[k] += p
    for k in st:
        st[k] *= 1.0 + VARIANCE * (rng.random() * 2.0 - 1.0)
    for k in st:
        st[k] = round(st[k], 1) if k in PCT_KEYS else round(st[k])

    # CP ①식 13종 (05 §8)
    S = (st['HP'] * 0.12 + st['ATK'] * 2.0 + st['MAG'] * 2.0 +
         st['DEF'] * 1.5 + st['MDEF'] * 1.5 +
         st['ASPD'] * 3.0 + st['SPD_CAST'] * 2.0 +
         st['CRI'] * 3.0 + st['CDMG'] * 1.0 +
         st['PEN'] * 2.5 + st['EVA'] * 2.5 +
         st['MANA'] * 0.05 + st['STA'] * 0.03)
    cp = round(S * P_MULT[pers])

    # 이름 (시드 기반 고유성 — 구 NameGen 3계층의 축약판)
    name = f"{race}·{job}·{subrace}·{rng.randint(1, 9999):04d}"[:32]
    owned[lin] = owned.get(lin, 0) + 1

    return {'등급': grade, '계열': lin, '종족': race, '아종': subrace,
            '직업': job, '성격': pers, '적성': {k: v for k, v in apt.items() if v >= 4},
            'rare_apt': rare_apt if rare_apt in apt else None,
            '이름': name, '스탯': st, 'CP': cp}


def batch(n, counts, floor, pickup=None, rng=None):
    """n연차 — 무료 10회 + 유료 (쿼터 무시 단발 모드)"""
    if rng is None:
        rng = globals()['rng']
    counts.setdefault('pity', 0)
    heroes, rare = [], {'직업': 0, '적성': 0, '이름재추첨': 0}
    used_names = set()
    used_pers = set()  # 배치 내 성격 중복 방지 (05 §5 3차)
    for _ in range(n):
        for _ in range(9):  # 재추첨 최대 8회 (05)
            h = make_hero(rng, counts, floor, pickup, exclude_pers=used_pers)
            if h['이름'] not in used_names:
                break
            rare['이름재추첨'] += 1
        used_names.add(h['이름'])
        used_pers.add(h['성격'])
        heroes.append(h)
        if h['등급'] in ('★4', '★5', '★6'):
            counts['pity'] = 0
        else:
            counts['pity'] += 1
        if RARE_JOBS.get(h['계열']) == h['직업']:
            rare['직업'] += 1
        if h.get('rare_apt'):
            rare['적성'] += 1
    return heroes, rare


def income_by_floor(max_floor):
    """퇴장+게이트 수급 (식민섬 0 기준)"""
    exits = sum(30 * f for f in range(1, max_floor + 1))
    gates = sum((f // 5) ** 2 * 1000 for f in range(5, max_floor + 1, 5))
    return exits, gates


def dashboard(max_floor=100):
    print(f'\n═══ 수급·쿼터 대시보드 ({max_floor}층 기준) ═══')
    colonies = min(9, max_floor // 10)  # 10층마다 식민섬 1 (본섬 제외) — 골드 배율 전용
    exits, gates = income_by_floor(max_floor)
    stones = exits + gates  # 식민섬 배율 없음 (석은 단일섬 기준)
    stage_cap = 60 if max_floor < 10 else 150 if max_floor < 25 else 400 if max_floor < 50 else 1300  # 쿼터 = 2×현행상한 (04 §3.8)
    # 실제 인구 궤적 (자연증가 인구×2%/층 + 게이트+25)
    pop = 30.0
    cap = 60
    for f in range(1, max_floor + 1):
        for sf, cc in [(1, 60), (10, 150), (25, 400), (50, 1300)]:
            if f == sf:
                cap = cc
        pop = min(pop * 1.02, cap)
        if f % 5 == 0 and f < 100:
            pop += 25
        pop = min(pop, cap)
    gold = round(100 * sum(range(1, max_floor + 1)) * (1 + MUL_COLONY * colonies))
    print(f'식민섬 {colonies}개 (골드 배율 전용)')
    print(f'{max_floor}층 누적 석: 퇴장 {exits:,} + 게이트 {gates:,} = {stones:,}석'
          f' (배율 없음 · 골드에만 적용)')
    print(f'{max_floor}층 누적 골드: 던전 {gold:,}G (×{1 + MUL_COLONY * colonies:.1f}) + 세금')
    tickets = stones / TICKET_COST
    print(f'→ 티켓 {tickets:,.0f}장 + 무료 10 = {tickets + 10:,.0f}회')
    quota = stage_cap * 2
    print(f'현행상한 {stage_cap}명 · 실제인구 {pop:.0f}명 → 쿼터(2×상한) = {quota:,}회 → 커버율 {(tickets + 10) / quota * 100:.0f}%')
    for k in ('★5', '★6'):
        print(f'E[{k}] = {(tickets + 10) * RATES[k]:.2f}장')


def main():
    args = [a for a in sys.argv[1:]]
    floor, n, pickup, seed = 50, 1000, None, None
    if args and args[0].isdigit():
        floor = int(args.pop(0))
    if args and args[0].isdigit():
        n = int(args.pop(0))
    if '--pickup' in args:
        pickup = args[args.index('--pickup') + 1]
    if '--seed' in args:  # 고정 재현: --seed 20260914
        seed = int(args[args.index('--seed') + 1])

    global rng
    if seed is None:  # 기본 = 실행마다 새 시드 (2026-09-14: 고정 시드 "같은 결과 반복" 해소)
        seed = random.SystemRandom().randrange(2**31)
    rng = random.Random(seed)
    counts = {'pity': 0, 'floor': floor, 'owned': {}}
    heroes, rare = batch(n, counts, floor, pickup)

    print(f'═══ {n:,}연차 (층 {floor} · 시드 {seed}'
          + (f' · 픽업 {pickup}' if pickup else '') + ') ═══')
    g = Counter(h['등급'] for h in heroes)
    for k in RATES:
        exp = n * RATES[k]
        got = g.get(k, 0)
        bar = '█' * max(1, int(got / max(1, exp) * 10)) if got else '·'
        print(f'{k}: {got:,} / 기대 {exp:,.1f}  [{bar}]')
    print(f'희귀 직업 {rare["직업"]}개 (기대 {n*RARE_JOB_RATE:.0f}) · '
          f'희귀 적성 {rare["적성"]}개 (기대 {n*RARE_APT_RATE:.0f}) · '
          f'이름재추첨 {rare["이름재추첨"]}회')
    print(f'계열 분포: ', end='')
    lin_c = Counter(h['계열'] for h in heroes)
    print(' · '.join(f'{l}{lin_c[l]:,}' for l in LINEAGES))

    dashboard(max_floor=floor)
    cps = sorted(h['CP'] for h in heroes)
    print(f'CP: min {cps[0]:,} / 중간 {cps[len(cps)//2]:,} / max {cps[-1]:,}')
    print('표본 5명:')
    for h in sorted(heroes, key=lambda x: -x['CP'])[:5]:
        st = ' '.join(f'{k}{v}' for k, v in h['스탯'].items())
        print(f"  [{h['등급']}] {h['계열']}·{h['종족']}({h['아종']})·{h['직업']}·"
              f"{h['성격']} CP {h['CP']:,} | {st}")

    income_by_floor(floor)


if __name__ == '__main__':
    main()
