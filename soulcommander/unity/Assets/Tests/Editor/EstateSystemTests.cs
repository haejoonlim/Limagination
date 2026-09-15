using System;
using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    public class EstateSystemTests
    {
        [SetUp]
        public void SetUp()
        {
            DataLoader.ResetCache();
        }

        [Test]
        public void LoadEstate_Returns12Facilities()
        {
            var root = DataLoader.LoadEstate();
            Assert.IsNotNull(root);
            Assert.IsNotNull(root.facilities);
            Assert.AreEqual(12, root.facilities.Count);
            Assert.IsNotNull(root.population);
            Assert.AreEqual(30, root.population.initial);
        }

        [Test]
        public void NewSave_HasBuiltSummonAltarAndHospital()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            Assert.IsNotNull(d.estate);
            Assert.IsFalse(string.IsNullOrEmpty(d.estate.lastTickUtc));
            var altar = EstateSystem.GetFacilityState(d, "summon_altar");
            var hospital = EstateSystem.GetFacilityState(d, "hospital");
            Assert.IsNotNull(altar);
            Assert.IsTrue(altar.built);
            Assert.IsNotNull(hospital);
            Assert.IsTrue(hospital.built);
            var tactics = EstateSystem.GetFacilityState(d, "tactics_office");
            Assert.IsFalse(tactics.built);
        }

        [Test]
        public void AdvanceTime_DoesNotConsumeFoodOrGrantTax()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.food = 100;
            d.gold = 0;
            d.estate.population = 10;
            double realSeconds = EstateSystem.SecondsPerIslandDay / EstateSystem.IslandTimeMultiplier;
            DateTime now = DateTime.UtcNow.AddSeconds(realSeconds);
            EstateSystem.AdvanceTime(d, now);
            Assert.AreEqual(100, d.estate.food);
            Assert.AreEqual(0, d.gold);
        }

        [Test]
        public void OnFloorCleared_ConsumesFoodAndGrantsTax()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.food = 100;
            d.gold = 0;
            d.estate.population = 10;
            EstateSystem.OnFloorCleared(d, 5);
            Assert.AreEqual(90, d.estate.food); // 100 - 10인
            Assert.AreEqual(10, d.gold); // 10인 * 1G
        }

        [Test]
        public void NaturalGrowth_RespectsBedsAndStageCap()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.population = 30;
            d.estate.housingCount = 3; // 60 beds
            double realSeconds = EstateSystem.SecondsPerIslandDay / EstateSystem.IslandTimeMultiplier;
            EstateSystem.AdvanceTime(d, DateTime.UtcNow.AddSeconds(realSeconds));
            Assert.AreEqual(30, d.estate.population); // 30 * 0.02 * 1 = 0.6 -> 0
            d.estate.population = 50;
            EstateSystem.AdvanceTime(d, DateTime.UtcNow.AddSeconds(realSeconds * 10));
            Assert.Greater(d.estate.population, 50); // 50 * 0.02 * 10 = 10 growth, capped by beds/stage
            Assert.LessOrEqual(d.estate.population, EstateSystem.MaxPopulation(d));
        }

        [Test]
        public void NaturalGrowth_Spring_Bonus()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.population = 100;
            d.estate.housingCount = 10; // plenty of beds
            d.estate.currentStageId = "S4"; // stage cap 1300
            EstateSystem.SeasonOverride = "spring";
            try
            {
                var season = EstateSystem.CurrentSeason(DateTime.UtcNow);
                Assert.IsNotNull(season);
                Assert.AreEqual(1.5f, season.natural_growth_mul, 0.001f);
                Assert.AreEqual(100, d.estate.population);
                Assert.AreEqual("spring", EstateSystem.SeasonOverride);
                Assert.AreEqual(1300, EstateSystem.MaxPopulation(d)); // verify stage cap
                EstateSystem.ApplyNaturalGrowth(d, 100f, DateTime.UtcNow);
                Assert.AreEqual(400, d.estate.population); // 100 * 0.02 * 1.5 * 100 = 300
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void MoraleProductionBonus_AtInitialIsZero()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            Assert.AreEqual(0f, EstateSystem.MoraleProductionBonus(d), 0.001f);
            d.estate.morale = 100;
            Assert.Greater(EstateSystem.MoraleProductionBonus(d), 0f);
        }

        [Test]
        public void MaxGatheringTeams_AltarLevel1_Is1()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            Assert.AreEqual(1, EstateSystem.MaxGatheringTeams(d));
        }

        [Test]
        public void TryHarvest_WhenCooldownReady_IncreasesFood()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.gatheringTeams.Add(new GatheringTeamState
            {
                id = "team_1",
                floor = 5,
                lastHarvestUtc = DateTime.UtcNow.AddHours(-25).ToString("o"),
                memberHeroIds = new System.Collections.Generic.List<string>()
            });
            int before = d.estate.food;
            bool ok = EstateSystem.TryHarvest(d, "team_1", DateTime.UtcNow);
            Assert.IsTrue(ok);
            Assert.Greater(d.estate.food, before);
        }

        [Test]
        public void TryHarvest_WhenCooldownNotReady_ReturnsFalse()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.gatheringTeams.Add(new GatheringTeamState
            {
                id = "team_1",
                floor = 5,
                lastHarvestUtc = DateTime.UtcNow.ToString("o"),
                memberHeroIds = new System.Collections.Generic.List<string>()
            });
            int before = d.estate.food;
            bool ok = EstateSystem.TryHarvest(d, "team_1", DateTime.UtcNow);
            Assert.IsFalse(ok);
            Assert.AreEqual(before, d.estate.food);
        }

        [Test]
        public void CalculateYield_AppliesFloorMultiplierToFood()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "summer";
            try
            {
                var team = new GatheringTeamState { id = "team_1", floor = 50 };
                var yield = EstateSystem.CalculateYield(d, team, DateTime.UtcNow);
                Assert.AreEqual(300, yield.food); // 150 * (1 + 50/50)
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void MaxFarmPlots_InitialHousing3_Is3()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            Assert.AreEqual(3, EstateSystem.MaxFarmPlots(d));
        }

        [Test]
        public void TryPlant_InSpring_SucceedsAndCountsPlot()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "spring";
            try
            {
                bool ok = EstateSystem.TryPlant(d, "plot_1", "grain", DateTime.UtcNow);
                Assert.IsTrue(ok);
                Assert.AreEqual(1, d.estate.farmPlots.Count);
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void TryPlant_InWinter_Fails()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "winter";
            try
            {
                bool ok = EstateSystem.TryPlant(d, "plot_1", "grain", DateTime.UtcNow);
                Assert.IsFalse(ok);
                Assert.AreEqual(0, d.estate.farmPlots.Count);
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void TryHarvestCrop_AfterGrowthPeriod_YieldsFood()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "summer";
            try
            {
                DateTime planted = DateTime.UtcNow;
                EstateSystem.TryPlant(d, "plot_1", "grain", planted);
                // 곡물 성장 2일(섬 시간). 현실 시간 = 2 * 24 * 3600 / 7 초
                double realSeconds = 2 * 24 * 3600 / EstateSystem.IslandTimeMultiplier;
                DateTime now = planted.AddSeconds(realSeconds);
                int before = d.estate.food;
                bool ok = EstateSystem.TryHarvestCrop(d, "plot_1", now);
                Assert.IsTrue(ok);
                Assert.AreEqual(before + 30, d.estate.food); // 여름 배율 1.0
                Assert.AreEqual(0, d.estate.farmPlots.Count);
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void TryHarvestCrop_BeforeGrowthPeriod_Fails()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "summer";
            try
            {
                DateTime planted = DateTime.UtcNow;
                EstateSystem.TryPlant(d, "plot_1", "grain", planted);
                int before = d.estate.food;
                bool ok = EstateSystem.TryHarvestCrop(d, "plot_1", planted);
                Assert.IsFalse(ok);
                Assert.AreEqual(before, d.estate.food);
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void AutoHarvestMatureCrops_HarvestsAllMature()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            EstateSystem.SeasonOverride = "autumn"; // +10% 식량
            try
            {
                DateTime planted = DateTime.UtcNow;
                EstateSystem.TryPlant(d, "plot_1", "grain", planted);
                double realSeconds = 2 * 24 * 3600 / EstateSystem.IslandTimeMultiplier;
                int before = d.estate.food;
                int harvested = EstateSystem.AutoHarvestMatureCrops(d, planted.AddSeconds(realSeconds));
                Assert.AreEqual(1, harvested);
                Assert.AreEqual(before + 33, d.estate.food); // 30 * 1.1
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }

        [Test]
        public void MaxEdictSlots_Before10Floor_Is0()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 5;
            Assert.AreEqual(0, EstateSystem.MaxEdictSlots(d));
        }

        [Test]
        public void MaxEdictSlots_At10Floor_Is1()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 10;
            Assert.AreEqual(1, EstateSystem.MaxEdictSlots(d));
        }

        [Test]
        public void MaxEdictSlots_At30Floor_Is2()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 30;
            Assert.AreEqual(2, EstateSystem.MaxEdictSlots(d));
        }

        [Test]
        public void TrySetEdict_BeforeUnlock_Fails()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 5;
            bool ok = EstateSystem.TrySetEdict(d, "mercantilism", 0, 5);
            Assert.IsFalse(ok);
        }

        [Test]
        public void TrySetEdict_AtUnlock_AppliesMoraleAndTaxMultiplier()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 10;
            d.estate.morale = 50;
            bool ok = EstateSystem.TrySetEdict(d, "mercantilism", 0, 10);
            Assert.IsTrue(ok);
            Assert.AreEqual(35, d.estate.morale); // 50 - 15
            Assert.AreEqual(1.30f, EstateSystem.GetActiveTaxMultiplier(d), 0.001f);
        }

        [Test]
        public void TrySetEdict_RespectsCooldown()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 10;
            EstateSystem.TrySetEdict(d, "mercantilism", 0, 10);
            bool ok = EstateSystem.TrySetEdict(d, "distributism", 0, 12); // 2층 지남, 쿨다운 5층
            Assert.IsFalse(ok);
            ok = EstateSystem.TrySetEdict(d, "distributism", 0, 15); // 5층 지남
            Assert.IsTrue(ok);
        }

        [Test]
        public void GatheringYield_GatheringOrder_EdictBonus()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.currentFloor = 10;
            EstateSystem.TrySetEdict(d, "gathering_order", 0, 10);
            EstateSystem.SeasonOverride = "summer";
            try
            {
                var team = new GatheringTeamState { id = "team_1", floor = 0 };
                var yield = EstateSystem.CalculateYield(d, team, DateTime.UtcNow);
                Assert.AreEqual(180, yield.food); // 150 * 1.2
            }
            finally
            {
                EstateSystem.SeasonOverride = null;
            }
        }
    }
}
