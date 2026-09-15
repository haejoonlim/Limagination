using NUnit.Framework;
using SoulCommander.Data;

namespace SoulCommander.Tests
{
    public class DataLoaderTests
    {
        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void Loads_Races_And_Finds_Human()
        {
            var races = DataLoader.LoadRaces();
            Assert.IsNotNull(races);
            Assert.IsNotNull(races.races);
            Assert.Greater(races.races.Count, 0);
            var human = DataLoader.GetRace("race_human");
            Assert.IsNotNull(human, "race_human 은 races.json 정본에 존재해야 함");
            Assert.AreEqual("인간", human.name);
            Assert.AreEqual("human", human.lineage);
        }

        [Test]
        public void Loads_Monsters_And_Finds_Floor1_Enemies()
        {
            var monsters = DataLoader.LoadMonsters();
            Assert.IsNotNull(monsters);
            Assert.IsNotNull(monsters.monsters);
            Assert.Greater(monsters.monsters.Count, 20);
            var skele = DataLoader.GetMonster("mon_skeleton_01");
            var slime = DataLoader.GetMonster("mon_slime_green_01");
            Assert.IsNotNull(skele, "mon_skeleton_01 필수");
            Assert.IsNotNull(slime, "mon_slime_green_01 필수");
            Assert.AreEqual(1, skele.tier);
            Assert.AreEqual(1, slime.tier);
            Assert.IsTrue(skele.spawn.floors.Contains(1));
            Assert.IsTrue(slime.spawn.floors.Contains(1));
        }
    }
}
