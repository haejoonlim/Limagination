using System;
using UnityEngine;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 영지(공중섬 왕국) 도메인 로직 — Pure C#.
    // SaveData.estate 를 조작하고 estate.json 정본을 참조한다.
    // 시간 기반: 섬 시간 = 현실 시간 × 7 (04 §3.13).
    public static class EstateSystem
    {
        public const float IslandTimeMultiplier = 7f;
        public const float SecondsPerIslandDay = 24f * 3600f;

        public static EstateFacilityEntry GetFacilityData(string id)
        {
            var root = DataLoader.LoadEstate();
            if (root?.facilities == null) return null;
            foreach (var f in root.facilities)
                if (f.id == id) return f;
            return null;
        }

        public static FacilityState GetFacilityState(SaveData d, string id)
        {
            if (d?.estate?.facilities == null) return null;
            foreach (var f in d.estate.facilities)
                if (f.id == id) return f;
            return null;
        }

        public static int Beds(SaveData d)
        {
            var root = DataLoader.LoadEstate();
            int bedsPer = root?.population?.housing_beds_per_building ?? 20;
            return d.estate.housingCount * bedsPer;
        }

        public static int MaxPopulation(SaveData d)
        {
            var root = DataLoader.LoadEstate();
            int stageMax = 60;
            if (root?.stages != null)
            {
                foreach (var s in root.stages)
                {
                    if (s.id == d.estate.currentStageId)
                    {
                        stageMax = s.max_population;
                        break;
                    }
                }
            }
            return Math.Min(stageMax, Beds(d));
        }

        // 현실 시간 경과를 섬 시간으로 환산해 영지를 진행.
        // GameRoot 허브 진입/로드 시 호출. 이전 tick 이후 누적분만큼만 정산.
        public static void AdvanceTime(SaveData d, DateTime nowUtc)
        {
            if (d?.estate == null) return;
            DateTime last = ParseLastTick(d.estate.lastTickUtc);
            double elapsedRealSeconds = (nowUtc - last).TotalSeconds;
            if (elapsedRealSeconds <= 0) return;
            float islandDays = (float)(elapsedRealSeconds * IslandTimeMultiplier / SecondsPerIslandDay);
            ApplyFoodConsumption(d, islandDays);
            ApplyTax(d, islandDays);
            ApplyNaturalGrowth(d, islandDays);
            d.estate.lastTickUtc = nowUtc.ToString("o");
        }

        private static DateTime ParseLastTick(string s)
        {
            if (DateTime.TryParse(s, null, System.Globalization.DateTimeStyles.RoundtripKind, out var dt))
                return dt.ToUniversalTime();
            return DateTime.UtcNow;
        }

        public static void ApplyFoodConsumption(SaveData d, float islandDays)
        {
            if (d?.estate == null || islandDays <= 0) return;
            var root = DataLoader.LoadEstate();
            int consumption = (int)Math.Floor((root?.food?.consumption_per_pop_per_island_day ?? 1) * d.estate.population * islandDays);
            d.estate.food -= consumption;
            if (d.estate.food < 0) d.estate.food = 0;
        }

        public static void ApplyTax(SaveData d, float islandDays)
        {
            if (d?.estate == null || islandDays <= 0) return;
            var root = DataLoader.LoadEstate();
            int tax = (int)Math.Floor((root?.tax?.gold_per_pop_per_island_day ?? 1) * d.estate.population * islandDays);
            d.gold += tax;
        }

        public static void ApplyNaturalGrowth(SaveData d, float islandDays)
        {
            if (d?.estate == null || islandDays <= 0) return;
            var root = DataLoader.LoadEstate();
            float growthRate = root?.population?.natural_growth_rate_per_island_day ?? 0.02f;
            int maxPop = MaxPopulation(d);
            int room = Math.Max(0, Math.Min(Beds(d), maxPop) - d.estate.population);
            int growth = (int)Math.Floor(d.estate.population * growthRate * islandDays);
            growth = Math.Min(growth, room);
            if (growth > 0) d.estate.population += growth;
        }

        public static float MoraleProductionBonus(SaveData d)
        {
            if (d?.estate == null) return 0f;
            var root = DataLoader.LoadEstate();
            float factor = root?.morale?.production_bonus_factor ?? 0.20f;
            int baseMorale = root?.morale?.initial ?? 50;
            return (d.estate.morale - baseMorale) / (float)baseMorale * factor;
        }

        public static bool IsFacilityOperational(SaveData d, string id)
        {
            var state = GetFacilityState(d, id);
            var data = GetFacilityData(id);
            if (state == null || data == null) return false;
            if (!state.built || state.level <= 0) return false;
            if (!data.operate_required) return true;
            return !string.IsNullOrEmpty(state.operatorHeroId);
        }

        // ============ 채집 (04 §3.3) ============

        public static EstateGathering GetGatheringData() => DataLoader.LoadEstate()?.gathering;

        public static int MaxGatheringTeams(SaveData d)
        {
            var altar = GetFacilityState(d, "summon_altar");
            var g = GetGatheringData();
            if (g?.max_teams_by_altar_level == null) return 0;
            int lv = Mathf.Clamp(altar?.level ?? 1, 1, g.max_teams_by_altar_level.Count);
            return g.max_teams_by_altar_level[lv - 1];
        }

        public static GatheringTeamState GetTeam(SaveData d, string teamId)
        {
            if (d?.estate?.gatheringTeams == null) return null;
            foreach (var t in d.estate.gatheringTeams)
                if (t.id == teamId) return t;
            return null;
        }

        public static bool CanHarvest(SaveData d, string teamId, DateTime nowUtc)
        {
            var team = GetTeam(d, teamId);
            if (team == null) return false;
            var g = GetGatheringData();
            if (g == null) return false;
            double elapsedIslandHours = (nowUtc - ParseLastTick(team.lastHarvestUtc)).TotalSeconds * IslandTimeMultiplier / 3600.0;
            return elapsedIslandHours >= g.cooldown_island_hours;
        }

        public static double CooldownRemainingIslandHours(SaveData d, string teamId, DateTime nowUtc)
        {
            var team = GetTeam(d, teamId);
            var g = GetGatheringData();
            if (team == null || g == null) return 0;
            double elapsedIslandHours = (nowUtc - ParseLastTick(team.lastHarvestUtc)).TotalSeconds * IslandTimeMultiplier / 3600.0;
            return Math.Max(0, g.cooldown_island_hours - elapsedIslandHours);
        }

        // 수확을 시도한다. 성공 시 재화를 SaveData.estate에 반영하고 true 를 반환.
        public static bool TryHarvest(SaveData d, string teamId, DateTime nowUtc)
        {
            if (!CanHarvest(d, teamId, nowUtc)) return false;
            var team = GetTeam(d, teamId);
            var g = GetGatheringData();
            if (team == null || g?.base_yield == null) return false;
            var yield = CalculateYield(d, team);
            d.estate.food += yield.food;
            d.estate.herb += yield.herb;
            d.estate.wood += yield.wood;
            d.estate.ore += yield.ore;
            team.lastHarvestUtc = nowUtc.ToString("o");
            return true;
        }

        public static EstateGatheringYield CalculateYield(SaveData d, GatheringTeamState team)
        {
            var g = GetGatheringData();
            var result = new EstateGatheringYield();
            if (g?.base_yield == null || team == null) return result;
            float floorMul = 1f + team.floor / 50f;
            result.food = (int)Math.Floor(g.base_yield.food * floorMul);
            result.herb = g.base_yield.herb;
            result.wood = g.base_yield.wood;
            // 광석 채굴은 광부 적성 티어 5+ 필요 — 05 §6 적성 시스템 후속 연동 예정
            result.ore = g.base_yield.ore;
            return result;
        }
    }
}
