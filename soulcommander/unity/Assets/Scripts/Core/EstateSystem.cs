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
            ApplyNaturalGrowth(d, islandDays, nowUtc);
            AutoHarvestMatureCrops(d, nowUtc);
            d.estate.lastTickUtc = nowUtc.ToString("o");
        }

        private static DateTime ParseLastTick(string s)
        {
            if (DateTime.TryParse(s, null, System.Globalization.DateTimeStyles.RoundtripKind, out var dt))
                return dt.ToUniversalTime();
            return DateTime.UtcNow;
        }

        // 층 클리어 시 주민 세금/식량 소비 (04 §3.4 · §3.?? 세금 재설계).
        public static void OnFloorCleared(SaveData d, int floor)
        {
            if (d?.estate == null) return;
            ApplyFloorTax(d);
            ApplyFloorFoodConsumption(d);
        }

        private static void ApplyFloorFoodConsumption(SaveData d)
        {
            if (d?.estate == null) return;
            int consumption = d.estate.population; // 1인당 1식량/층 클리어 (04 §3.4)
            d.estate.food -= consumption;
            if (d.estate.food < 0) d.estate.food = 0;
        }

        private static void ApplyFloorTax(SaveData d)
        {
            if (d?.estate == null) return;
            int tax = d.estate.population; // 1인당 1G/층 클리어 (04 §3.11 세금 재설계)
            tax = (int)Math.Floor(tax * GetActiveTaxMultiplier(d));
            d.gold += tax;
        }

        public static void ApplyNaturalGrowth(SaveData d, float islandDays, DateTime nowUtc)
        {
            if (d?.estate == null || islandDays <= 0) return;
            var root = DataLoader.LoadEstate();
            float growthRate = root?.population?.natural_growth_rate_per_island_day ?? 0.02f;
            float seasonMul = CurrentSeason(nowUtc)?.natural_growth_mul ?? 1f;
            float edictMul = GetActiveNaturalGrowthMultiplier(d);
            int maxPop = MaxPopulation(d);
            int room = Math.Max(0, Math.Min(Beds(d), maxPop) - d.estate.population);
            int growth = (int)Math.Floor((double)d.estate.population * growthRate * seasonMul * edictMul * islandDays);
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

        // ============ 계절 (04 §3.13) ============

        public static EstateFarming GetFarmingData() => DataLoader.LoadEstate()?.farming;

        // 테스트용 계절 강제. null 이면 현실 월 기준.
        public static string SeasonOverride { get; set; }

        public static EstateSeason CurrentSeason(DateTime nowUtc)
        {
            var f = GetFarmingData();
            if (f?.seasons == null) return null;
            int month = nowUtc.Month;
            foreach (var s in f.seasons)
            {
                if (!string.IsNullOrEmpty(SeasonOverride))
                {
                    if (s.id == SeasonOverride) return s;
                    continue;
                }
                if (s.months != null && s.months.Contains(month)) return s;
            }
            return null;
        }

        // ============ 칙령 (04 §3.7) ============

        public static EstateEdicts GetEdictsData() => DataLoader.LoadEstate()?.edicts;

        public static EstateEdict GetEdictData(string id)
        {
            var e = GetEdictsData();
            if (e?.list == null || id == null) return null;
            foreach (var ed in e.list)
                if (ed.id == id) return ed;
            return null;
        }

        public static int MaxEdictSlots(SaveData d)
        {
            var e = GetEdictsData();
            if (e?.slot_count_by_floor == null) return 0;
            int floor = d?.currentFloor ?? 1;
            int slots = 0;
            foreach (var s in e.slot_count_by_floor)
            {
                if (floor >= s.floor) slots = s.slots;
            }
            return slots;
        }

        public static bool CanChangeEdict(SaveData d, int currentFloor)
        {
            var e = GetEdictsData();
            if (e == null) return false;
            return currentFloor - d.estate.lastEdictChangeFloor >= e.change_cooldown_floors;
        }

        public static bool TrySetEdict(SaveData d, string edictId, int slotIndex, int currentFloor)
        {
            if (d?.estate == null) return false;
            var data = GetEdictsData();
            if (data == null) return false;
            if (currentFloor < data.unlock_floor) return false;
            if (!CanChangeEdict(d, currentFloor)) return false;
            if (slotIndex < 0 || slotIndex >= MaxEdictSlots(d)) return false;
            var edict = GetEdictData(edictId);
            if (edict == null) return false;

            while (d.estate.activeEdicts.Count <= slotIndex)
                d.estate.activeEdicts.Add(null);
            d.estate.activeEdicts[slotIndex] = edictId;
            d.estate.morale = Mathf.Clamp(d.estate.morale + edict.morale_delta, 0, 100);
            d.estate.lastEdictChangeFloor = currentFloor;
            return true;
        }

        private static float ProductMultiplier(Func<EstateEdict, float> selector, SaveData d)
        {
            float mul = 1f;
            if (d?.estate?.activeEdicts == null) return mul;
            foreach (var id in d.estate.activeEdicts)
            {
                var e = GetEdictData(id);
                if (e != null) mul *= selector(e);
            }
            return mul;
        }

        public static float GetActiveTaxMultiplier(SaveData d) => ProductMultiplier(e => e.tax_mul, d);
        public static float GetActiveGatheringMultiplier(SaveData d) => ProductMultiplier(e => e.gathering_yield_mul, d);
        public static float GetActiveNaturalGrowthMultiplier(SaveData d) => ProductMultiplier(e => e.natural_growth_mul, d);

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
            var yield = CalculateYield(d, team, nowUtc);
            d.estate.food += yield.food;
            d.estate.herb += yield.herb;
            d.estate.wood += yield.wood;
            d.estate.ore += yield.ore;
            team.lastHarvestUtc = nowUtc.ToString("o");
            return true;
        }

        public static EstateGatheringYield CalculateYield(SaveData d, GatheringTeamState team, DateTime nowUtc)
        {
            var g = GetGatheringData();
            var result = new EstateGatheringYield();
            if (g?.base_yield == null || team == null) return result;
            float floorMul = 1f + team.floor / 50f;
            float edictMul = GetActiveGatheringMultiplier(d);
            float seasonMul = CurrentSeason(nowUtc)?.food_yield_mul ?? 1f;
            result.food = (int)Math.Floor(g.base_yield.food * floorMul * edictMul * seasonMul);
            result.herb = (int)Math.Floor(g.base_yield.herb * edictMul);
            result.wood = (int)Math.Floor(g.base_yield.wood * edictMul);
            // 광석 채굴은 광부 적성 티어 5+ 필요 — 05 §6 적성 시스템 후속 연동 예정
            result.ore = (int)Math.Floor(g.base_yield.ore * edictMul);
            return result;
        }

        // ============ 농사 (04 §3.3-2) ============

        public static int MaxFarmPlots(SaveData d)
        {
            var f = GetFarmingData();
            return d.estate.housingCount * (f?.plots_per_housing ?? 1);
        }

        public static EstateCrop GetCrop(string id)
        {
            var f = GetFarmingData();
            if (f?.crops == null || id == null) return null;
            foreach (var c in f.crops)
                if (c.id == id) return c;
            return null;
        }

        public static bool TryPlant(SaveData d, string plotId, string cropId, DateTime nowUtc)
        {
            if (d?.estate == null) return false;
            var season = CurrentSeason(nowUtc);
            if (season == null || season.growth_mul <= 0f) return false; // 겨울 불가
            if (d.estate.farmPlots.Count >= MaxFarmPlots(d)) return false;
            if (GetCrop(cropId) == null) return false;
            d.estate.farmPlots.Add(new FarmPlotState
            {
                id = plotId,
                cropId = cropId,
                plantedAtUtc = nowUtc.ToString("o")
            });
            return true;
        }

        public static FarmPlotState GetPlot(SaveData d, string plotId)
        {
            if (d?.estate?.farmPlots == null) return null;
            foreach (var p in d.estate.farmPlots)
                if (p.id == plotId) return p;
            return null;
        }

        public static bool IsCropMature(SaveData d, string plotId, DateTime nowUtc)
        {
            var plot = GetPlot(d, plotId);
            var crop = GetCrop(plot?.cropId);
            if (plot == null || crop == null) return false;
            var season = CurrentSeason(nowUtc);
            if (season == null || season.growth_mul <= 0f) return false;
            double elapsedIslandDays = (nowUtc - ParseLastTick(plot.plantedAtUtc)).TotalSeconds * IslandTimeMultiplier / SecondsPerIslandDay;
            return elapsedIslandDays >= crop.growth_island_days;
        }

        public static bool TryHarvestCrop(SaveData d, string plotId, DateTime nowUtc)
        {
            if (!IsCropMature(d, plotId, nowUtc)) return false;
            var plot = GetPlot(d, plotId);
            var crop = GetCrop(plot?.cropId);
            if (plot == null || crop == null) return false;
            var yield = CalculateCropYield(d, plot, nowUtc);
            d.estate.food += yield.food;
            d.estate.herb += yield.herb;
            d.estate.farmPlots.Remove(plot);
            return true;
        }

        public static EstateGatheringYield CalculateCropYield(SaveData d, FarmPlotState plot, DateTime nowUtc)
        {
            var result = new EstateGatheringYield();
            var crop = GetCrop(plot?.cropId);
            if (crop == null) return result;
            var season = CurrentSeason(nowUtc);
            float foodMul = (season?.food_yield_mul ?? 1f) * GetActiveGatheringMultiplier(d);
            float herbMul = GetActiveGatheringMultiplier(d);
            // 농부 적성 티어 배율 — 05 §6 적성 시스템 후속 연동 예정
            result.food = (int)Math.Floor(crop.yield_food * foodMul);
            result.herb = (int)Math.Floor(crop.yield_herb * herbMul);
            return result;
        }

        public static int AutoHarvestMatureCrops(SaveData d, DateTime nowUtc)
        {
            if (d?.estate?.farmPlots == null) return 0;
            int count = 0;
            for (int i = d.estate.farmPlots.Count - 1; i >= 0; i--)
            {
                var plot = d.estate.farmPlots[i];
                if (IsCropMature(d, plot.id, nowUtc))
                {
                    var yield = CalculateCropYield(d, plot, nowUtc);
                    d.estate.food += yield.food;
                    d.estate.herb += yield.herb;
                    d.estate.farmPlots.RemoveAt(i);
                    count++;
                }
            }
            return count;
        }
    }
}
