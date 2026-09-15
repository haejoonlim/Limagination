using System;
using System.Collections.Generic;

namespace SoulCommander.Data
{
    // races.json / monsters.json 은 필드가 많고 nested 하다.
    // Vertical Slice 는 전투에 필요한 최소 필드만 매핑한다.
    // JsonUtility 는 [Serializable] + public 필드 방식만 인식한다.

    [Serializable]
    public class RaceStatMods
    {
        public int hp;
        public int atk;
        public int def;
        public int aspd; // 공격속도 (05 §7)
        public int mag;
        public int mdef;
        public int pen;
        public int eva;
        public int cdmg;
        public int cri;
        public int mana;
        public int spd_cast;
        public int sta;

        // 레거시 JSON/C# 호환: 예전 "spd" 키를 aspd로 동기화
        public int spd { get => aspd; set => aspd = value; }
    }

    [Serializable]
    public class RaceNamePool
    {
        public string dir;
        public List<string> examples;
    }

    [Serializable]
    public class RaceEntry
    {
        public string id;
        public string name;
        public string lineage;
        public RaceStatMods statMods;
        public RaceNamePool namePool;
    }

    // races.json meta.heroBaseStats — 무한 영웅 생성 공통 기준스탯 (가안, 01 §2 하단 · 05 §7 13종 동기화).
    [Serializable]
    public class HeroBaseStats
    {
        public int hp;
        public int atk;
        public int def;
        public int aspd; // 공격속도 (05 §7)
        public int mag;
        public int mdef;
        public int pen;
        public int eva;
        public int cdmg;
        public int cri;
        public int mana;
        public int spd_cast;
        public int sta;

        // 레거시 JSON/C# 호환
        public int spd { get => aspd; set => aspd = value; }
    }

    [Serializable]
    public class RacesMeta
    {
        public HeroBaseStats heroBaseStats;
    }

    [Serializable]
    public class RacesRoot
    {
        public RacesMeta meta;
        public List<RaceEntry> races;
    }

    [Serializable]
    public class MonsterStats
    {
        public int hp;
        public int atk;
        public int def;
        public int aspd; // 공격속도 (05 §7)
        public int mdef;

        // 레거시 JSON/C# 호환
        public int spd { get => aspd; set => aspd = value; }
    }

    [Serializable]
    public class MonsterSpawn
    {
        public List<int> floors;
        public List<string> wave;
        public int bossScaleRefFloor; // 0 = 스케일 없음 (P2-1 보스 배치용 기준층)
    }

    [Serializable]
    public class MonsterEntry
    {
        public string id;
        public string name;
        public int tier;
        public string aiType;
        public MonsterStats stats;
        public MonsterSpawn spawn;
    }

    [Serializable]
    public class MonstersRoot
    {
        public List<MonsterEntry> monsters;
    }

    // equipment.json — 장비 최소 세트 가안 (P3-3)
    [Serializable]
    public class EquipmentStats
    {
        public int hp;
        public int atk;
        public int def;
        public int aspd;
        public int mag;
        public int mdef;
        public int pen;
        public int eva;
        public int cdmg;
        public int cri;
        public int mana;
        public int spd_cast;
        public int sta;

        // 레거시 JSON/C# 호환
        public int spd { get => aspd; set => aspd = value; }
    }

    [Serializable]
    public class EquipmentEntry
    {
        public string id;
        public string name;
        public string slot;
        public int grade;
        public EquipmentStats stats;
    }

    [Serializable]
    public class EquipmentMeta
    {
        public int enhanceMax;
        public int enhancePctPerLevel;
        public int enhanceGoldCostPerNextLevel;
        public List<int> shopPriceByGrade;
    }

    [Serializable]
    public class EquipmentRoot
    {
        public EquipmentMeta meta;
        public List<string> slots;
        public List<EquipmentEntry> equipment;
    }

    // 전투 진입 시 스탯 스냅샷. 원본 데이터에 등급/레벨 곱을 적용한 결과 (05 §7 13종).
    public struct CombatStats
    {
        public int Hp;
        public int Atk;
        public int Mag;
        public int Pen;
        public int Def;
        public int MDef;
        public int Eva;
        public int Aspd;
        public int Cdmg;
        public int Cri;
        public int Mana;
        public int SpdCast;
        public int Sta;

        // 기준스탯(가안) × (1 + 종족 statMods%) × 등급계수(01 §2).
        // ASPD/SPD_CAST/STA/CRI/PEN/EVA/CDMG 는 등급계수 미적용 (05 §7).
        public static CombatStats FromRace(RaceEntry race, HeroBaseStats b, float rankMul)
        {
            if (b == null) throw new ArgumentNullException(nameof(b));
            var m = race?.statMods ?? new RaceStatMods();
            return new CombatStats
            {
                Hp = Round(b.hp * (1f + m.hp / 100f) * rankMul),
                Atk = Round(b.atk * (1f + m.atk / 100f) * rankMul),
                Mag = Round(b.mag * (1f + m.mag / 100f) * rankMul),
                Def = Round(b.def * (1f + m.def / 100f) * rankMul),
                MDef = Round(b.mdef * (1f + m.mdef / 100f) * rankMul),
                Aspd = Round(b.aspd * (1f + m.aspd / 100f)),
                Pen = Round(b.pen * (1f + m.pen / 100f)),
                Eva = Round(b.eva * (1f + m.eva / 100f)),
                Cri = Round(b.cri * (1f + m.cri / 100f)),
                Cdmg = Round(b.cdmg * (1f + m.cdmg / 100f)),
                Mana = Round(b.mana * (1f + m.mana / 100f) * rankMul),
                SpdCast = Round(b.spd_cast * (1f + m.spd_cast / 100f)),
                Sta = Round(b.sta * (1f + m.sta / 100f)),
            };
        }

        public static CombatStats FromMonster(MonsterEntry m)
        {
            var s = m.stats;
            return new CombatStats { Hp = s.hp, Atk = s.atk, Def = s.def, MDef = s.mdef, Aspd = s.aspd };
        }

        private static int Round(float v) => (int)System.Math.Round(v);
    }

    // estate.json — 영지 시설 12종 + 인구·식량·민심·세금 상수 (GDD_v8.0_04_영지.md §3)
    [Serializable]
    public class EstateMeta
    {
        public string schema_version;
    }

    [Serializable]
    public class EstateFacilityEntry
    {
        public string id;
        public string name_ko;
        public int unlock_floor;
        public int build_cost;
        public bool operate_required;
        public int initial_level;
        public int max_level;
    }

    [Serializable]
    public class EstatePopulation
    {
        public int initial;
        public List<int> max_by_stage;
        public float natural_growth_rate_per_island_day;
        public int housing_beds_per_building;
    }

    [Serializable]
    public class EstateFood
    {
        public int consumption_per_pop_per_island_day;
    }

    [Serializable]
    public class EstateMorale
    {
        public int initial;
        public int min;
        public int max;
        public float production_bonus_factor;
    }

    [Serializable]
    public class EstateTax
    {
        public int gold_per_pop_per_island_day;
    }

    [Serializable]
    public class EstateGatheringYield
    {
        public int food;
        public int herb;
        public int wood;
        public int ore;
    }

    [Serializable]
    public class EstateGathering
    {
        public int team_size;
        public List<int> max_teams_by_altar_level;
        public int cooldown_island_hours;
        public EstateGatheringYield base_yield;
        public string floor_multiplier_formula;
    }

    [Serializable]
    public class EstateStage
    {
        public string id;
        public int unlock_floor;
        public int expansion_cost;
        public int max_population;
    }

    [Serializable]
    public class EstateCrop
    {
        public string id;
        public string name_ko;
        public int yield_food;
        public int yield_herb;
        public int growth_island_days;
    }

    [Serializable]
    public class EstateSeason
    {
        public string id;
        public List<int> months;
        public float food_yield_mul;
        public float natural_growth_mul;
        public float growth_mul;
    }

    [Serializable]
    public class EstateFarming
    {
        public int plots_per_housing;
        public List<EstateCrop> crops;
        public List<EstateSeason> seasons;
    }

    [Serializable]
    public class EstateEdictSlot
    {
        public int floor;
        public int slots;
    }

    [Serializable]
    public class EstateEdict
    {
        public string id;
        public string name_ko;
        public float tax_mul;
        public int morale_delta;
        public float gathering_yield_mul;
        public float natural_growth_mul;
    }

    [Serializable]
    public class EstateEdicts
    {
        public int unlock_floor;
        public List<EstateEdictSlot> slot_count_by_floor;
        public int change_cooldown_floors;
        public List<EstateEdict> list;
    }

    [Serializable]
    public class EstateRoot
    {
        public EstateMeta meta;
        public List<EstateFacilityEntry> facilities;
        public EstatePopulation population;
        public EstateFood food;
        public EstateMorale morale;
        public EstateTax tax;
        public EstateGathering gathering;
        public EstateFarming farming;
        public EstateEdicts edicts;
        public List<EstateStage> stages;
    }
}
