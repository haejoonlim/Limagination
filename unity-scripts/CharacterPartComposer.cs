using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

/// <summary>
/// 캐릭터/몬스터 무한 생성 시스템 - "조건부 가중치 파츠 조합기".
///
/// 이건 WFC가 아닙니다. WFC는 공간적으로 인접한 셀들 사이의 제약을 다루는
/// 알고리즘이고, 여기서 필요한 건 "슬롯 간 논리적 종속 관계"이기 때문에
/// 훨씬 단순한 가중치 조정 방식이 맞습니다.
///
/// 핵심 흐름:
/// 1. 슬롯을 정해진 순서대로 하나씩 선택 (Race -> Body -> Weapon -> Armor ...)
/// 2. 슬롯 하나를 선택할 때마다, 그 선택이 다른 슬롯들의 가중치에 영향을 줌
///    (예: GreatSword 선택 -> HeavyArmor 가중치 증가, LightArmor 가중치 감소)
/// 3. 완전 배제(0%)가 아니라 "가중치 조정"만 하는 게 핵심
///    -> 큰 체격 궁수처럼 드문 조합도 낮은 확률로 여전히 나올 수 있음 (다양성 유지)
/// 4. 시드 고정 시 항상 같은 캐릭터 재생성 가능
/// 5. 최종 선택 결과로 스프라이트 레이어 합성 + 애니메이션 세트 결정까지 연결
/// </summary>
public class CharacterPartComposer : MonoBehaviour
{
    [Header("Slot Definitions (인스펙터에서 채우거나 코드로 등록)")]
    public List<SlotDefinition> slots = new List<SlotDefinition>();

    [Serializable]
    public class SlotDefinition
    {
        public string slotName;              // "Race", "Body", "Weapon", "Armor", "Hair" ...
        public List<PartOption> options = new List<PartOption>();
    }

    [Serializable]
    public class PartOption
    {
        public string id;                    // "GreatSword", "LightArmor" 등 고유 ID
        [Range(0.01f, 100f)] public float baseWeight = 1f;
        public Sprite sprite;                // 레이어 합성용 스프라이트
        public int sortingOrder;             // 레이어 순서 (몸 밑, 무기 위 등)

        // 이 파츠가 선택되었을 때 다른 슬롯의 가중치를 어떻게 바꿀지
        // key: "슬롯명:파츠ID", value: 곱연산 배율 (1.0 = 변화없음, 2.0 = 2배, 0.3 = 30%로 감소)
        public List<WeightRule> influencesOnOtherSlots = new List<WeightRule>();
    }

    [Serializable]
    public class WeightRule
    {
        public string targetSlot;
        public string targetPartId;
        [Range(0f, 5f)] public float multiplier = 1f;
    }

    /// <summary>
    /// 생성 결과. 각 슬롯에서 선택된 파츠 ID와 시드를 담음.
    /// </summary>
    public class CharacterDNA
    {
        public int seed;
        public Dictionary<string, string> selectedParts = new Dictionary<string, string>();

        public string Get(string slotName) =>
            selectedParts.TryGetValue(slotName, out var v) ? v : null;
    }

    /// <summary>
    /// 시드를 받아 캐릭터 하나를 결정론적으로 생성.
    /// 같은 시드 -> 항상 같은 결과.
    /// </summary>
    public CharacterDNA Compose(int seed)
    {
        var rng = new System.Random(seed);
        var dna = new CharacterDNA { seed = seed };

        // 슬롯별 현재 가중치 테이블 (base에서 시작, 선택이 진행되며 조정됨)
        var currentWeights = new Dictionary<string, Dictionary<string, float>>();
        foreach (var slot in slots)
        {
            currentWeights[slot.slotName] = slot.options.ToDictionary(o => o.id, o => o.baseWeight);
        }

        foreach (var slot in slots)
        {
            var weights = currentWeights[slot.slotName];
            var validOptions = slot.options.Where(o => weights[o.id] > 0.0001f).ToList();

            if (validOptions.Count == 0)
            {
                Debug.LogWarning($"[Composer] 슬롯 '{slot.slotName}'에 선택 가능한 파츠가 없습니다. 이전 제약이 너무 강하게 걸렸을 수 있습니다.");
                continue;
            }

            string chosen = WeightedPick(validOptions, weights, rng);
            dna.selectedParts[slot.slotName] = chosen;

            // 방금 선택한 파츠가 다른 슬롯들에 미치는 영향 적용
            var chosenOption = slot.options.First(o => o.id == chosen);
            foreach (var rule in chosenOption.influencesOnOtherSlots)
            {
                if (currentWeights.TryGetValue(rule.targetSlot, out var targetWeights) &&
                    targetWeights.ContainsKey(rule.targetPartId))
                {
                    targetWeights[rule.targetPartId] *= rule.multiplier;
                }
            }
        }

        return dna;
    }

    private string WeightedPick(List<PartOption> options, Dictionary<string, float> weights, System.Random rng)
    {
        float total = options.Sum(o => weights[o.id]);
        double roll = rng.NextDouble() * total;
        double cumulative = 0;

        foreach (var opt in options)
        {
            cumulative += weights[opt.id];
            if (roll <= cumulative)
                return opt.id;
        }
        return options[options.Count - 1].id;
    }

    /// <summary>
    /// DNA를 받아 실제 스프라이트 레이어를 합성해서 SpriteRenderer들을 구성.
    /// 자식 오브젝트로 슬롯별 SpriteRenderer를 생성/갱신.
    /// </summary>
    public void ApplyToGameObject(CharacterDNA dna, Transform target)
    {
        foreach (var slot in slots)
        {
            string chosenId = dna.Get(slot.slotName);
            if (chosenId == null) continue;

            var option = slot.options.FirstOrDefault(o => o.id == chosenId);
            if (option == null || option.sprite == null) continue;

            string childName = $"Layer_{slot.slotName}";
            Transform layer = target.Find(childName);
            SpriteRenderer sr;

            if (layer == null)
            {
                var go = new GameObject(childName);
                go.transform.SetParent(target, false);
                sr = go.AddComponent<SpriteRenderer>();
            }
            else
            {
                sr = layer.GetComponent<SpriteRenderer>();
            }

            sr.sprite = option.sprite;
            sr.sortingOrder = option.sortingOrder;
        }
    }

    /// <summary>
    /// 무기 타입에 따라 어떤 애니메이션 세트를 쓸지 결정.
    /// 예: GreatSword -> "AttackSet_HeavyMelee", Bow -> "AttackSet_Ranged"
    /// 애니메이터 컨트롤러를 이 이름 기준으로 스위칭하는 데 사용.
    /// </summary>
    public string ResolveAnimationSet(CharacterDNA dna, Dictionary<string, string> weaponToAnimSet)
    {
        string weapon = dna.Get("Weapon");
        if (weapon != null && weaponToAnimSet.TryGetValue(weapon, out var animSet))
            return animSet;
        return "AttackSet_Default";
    }
}

/*
=========================================================
사용 예시
=========================================================

// 1. 슬롯 & 파츠 & 제약 규칙 설정 (인스펙터 또는 코드)

var weaponSlot = new CharacterPartComposer.SlotDefinition { slotName = "Weapon" };

var greatSword = new CharacterPartComposer.PartOption {
    id = "GreatSword", baseWeight = 1f, sortingOrder = 5,
    influencesOnOtherSlots = new List<CharacterPartComposer.WeightRule> {
        new CharacterPartComposer.WeightRule { targetSlot = "Armor", targetPartId = "HeavyArmor", multiplier = 2.5f },
        new CharacterPartComposer.WeightRule { targetSlot = "Armor", targetPartId = "LightArmor", multiplier = 0.3f },
        new CharacterPartComposer.WeightRule { targetSlot = "Body",  targetPartId = "Large",      multiplier = 1.8f },
    }
};

var bow = new CharacterPartComposer.PartOption {
    id = "Bow", baseWeight = 1f, sortingOrder = 5,
    influencesOnOtherSlots = new List<CharacterPartComposer.WeightRule> {
        new CharacterPartComposer.WeightRule { targetSlot = "Armor", targetPartId = "LightArmor", multiplier = 2.0f },
        new CharacterPartComposer.WeightRule { targetSlot = "Body",  targetPartId = "Small",      multiplier = 1.5f },
    }
};

weaponSlot.options.Add(greatSword);
weaponSlot.options.Add(bow);

// 2. 슬롯 순서 = 영향력이 퍼지는 순서.
//    Weapon을 Armor/Body보다 먼저 넣으면 "무기가 체형/방어구에 영향"을 주는 흐름이 됨.
//    반대로 Body를 먼저 넣으면 "체형이 무기 선택에 영향"을 주는 흐름이 됨.
//    둘 다 넣고 싶으면 양쪽에 서로 영향을 주는 규칙을 걸어도 되지만,
//    슬롯 순서상 나중 슬롯이 이미 확정된 이전 슬롯의 영향만 받는다는 점은 기억할 것.

composer.slots.Add(bodySlot);    // 1순위: 체형 결정
composer.slots.Add(weaponSlot);  // 2순위: 체형 영향 받아 무기 결정
composer.slots.Add(armorSlot);   // 3순위: 무기 영향 받아 방어구 결정
composer.slots.Add(hairSlot);
composer.slots.Add(headSlot);

// 3. 캐릭터 생성 (시드 고정 -> 항상 동일 결과)
var dna = composer.Compose(seed: 829174023);

// 4. 실제 게임 오브젝트에 스프라이트 레이어 적용
composer.ApplyToGameObject(dna, someTransform);

// 5. 무기 타입 -> 애니메이션 세트 매핑
var animMap = new Dictionary<string, string> {
    { "GreatSword", "AttackSet_HeavyMelee" },
    { "Bow", "AttackSet_Ranged" },
    { "Dagger", "AttackSet_FastMelee" },
};
string animSet = composer.ResolveAnimationSet(dna, animMap);
// -> Animator Controller Override 또는 Animator.SetInteger 등으로 실제 적용

=========================================================
설계 팁
=========================================================
1. 완전 배제(0%)가 아니라 가중치 조정(예: x0.3)만 쓰는 걸 강력 추천.
   완전 배제하면 "이상한데 재밌는" 희귀 조합(작은 체격 + 대검 등)이
   원천 차단되어 무한 생성의 다양성이 오히려 줄어듭니다.

2. 슬롯 순서를 어떻게 짜느냐가 곧 "캐릭터 성격의 인과관계 설계"입니다.
   Body -> Weapon -> Armor -> Personality -> Stats 순으로 두면
   "덩치가 크니까 무거운 무기를 들 확률이 높고, 그래서 중갑을 입을 확률도 높고,
   그래서 성격도 터프한 쪽으로..." 같은 자연스러운 서사가 생깁니다.

3. 파츠 스프라이트는 반드시 같은 pivot/캔버스 크기로 통일해야
   레이어 합성 시 어긋나지 않습니다. (PIXEL_EDITOR_ARTIST_SKILL 문서의
   "Bottom Center Pivot, 고정 Canvas" 규칙을 파츠 제작에도 그대로 적용하세요.)

4. 실제 병목은 알고리즘이 아니라 파츠 에셋 수입니다.
   슬롯 5개 x 슬롯당 파츠 5개 x 4방향 x 애니메이션 프레임...
   조합 수는 기하급수적으로 늘어나지만 에셋 제작량은 슬롯당 파츠 수에 비례해서만
   늘어나므로, 파츠 수를 늘리는 게 캐릭터 하나하나를 새로 그리는 것보다
   훨씬 효율적입니다.
=========================================================
*/
