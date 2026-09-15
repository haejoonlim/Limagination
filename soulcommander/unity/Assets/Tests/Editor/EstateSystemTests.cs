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
        public void AdvanceTime_ConsumesFoodAndGrantsTax()
        {
            var d = new SaveData();
            SaveMigration.Migrate(d);
            d.estate.food = 100;
            d.gold = 0;
            d.estate.population = 10;
            // 섬 1일 = 현실 24/7 시간 ≈ 12342.857초
            double realSeconds = EstateSystem.SecondsPerIslandDay / EstateSystem.IslandTimeMultiplier;
            DateTime now = DateTime.UtcNow.AddSeconds(realSeconds);
            EstateSystem.AdvanceTime(d, now);
            Assert.AreEqual(90, d.estate.food); // 100 - 10인 * 1일
            Assert.AreEqual(10, d.gold); // 10인 * 1일 * 1G
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
            var team = new GatheringTeamState { id = "team_1", floor = 50 };
            var yield = EstateSystem.CalculateYield(d, team);
            Assert.AreEqual(300, yield.food); // 150 * (1 + 50/50)
        }
    }
}
