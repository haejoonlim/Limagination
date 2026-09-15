using System.IO;
using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    public class SaveMigrationTests
    {
        private string _dir;

        [SetUp]
        public void SetUp()
        {
            _dir = Path.Combine(Path.GetTempPath(), "soulcmd_migr_test_" + System.Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_dir);
        }

        [TearDown]
        public void TearDown()
        {
            if (Directory.Exists(_dir)) Directory.Delete(_dir, true);
        }

        [Test]
        public void V1_Save_Migrates_To_Current_On_Load()
        {
            var sm = new SaveManager(_dir, "migr");
            // Phase 1 이전 슬라이스가 실제로 쓰던 v1 형태
            File.WriteAllText(sm.FilePath,
                "{\"schemaVersion\":1,\"createdAt\":\"2026-09-01T00:00:00Z\",\"updatedAt\":\"2026-09-01T00:00:00Z\"," +
                "\"runsStarted\":4,\"runsLost\":2,\"currentFloor\":1,\"heroRaceId\":\"race_human\",\"log\":[\"a\",\"b\"]}");

            var d = sm.Load(out bool corrupt);

            Assert.IsFalse(corrupt);
            Assert.AreEqual(SaveData.CurrentSchemaVersion, d.schemaVersion);
            // 기존 필드 유지
            Assert.AreEqual(4, d.runsStarted);
            Assert.AreEqual(2, d.runsLost);
            Assert.AreEqual(1, d.currentFloor);
            Assert.AreEqual(2, d.log.Count);
            // v2 필드 초기화
            Assert.AreEqual(0, d.gold);
            Assert.AreEqual(0, d.soulStones);
            Assert.AreEqual(0, d.expPool);
            Assert.AreEqual(GameRules.MaxAp, d.ap);
            Assert.IsNotNull(d.memorial);
            Assert.AreEqual(0, d.memorial.Count);
            // v1 영웅 → roster
            Assert.AreEqual(1, d.roster.Count);
            Assert.AreEqual("race_human", d.roster[0].raceId);
            Assert.AreEqual(1, d.roster[0].rank);
            Assert.AreEqual(1, d.roster[0].level);
            Assert.IsFalse(string.IsNullOrEmpty(d.roster[0].id));
            // v3: 소환 횟수 0 · 기존 영웅 출격 편성 · Sanity 시작값
            Assert.AreEqual(0, d.freeSummonsUsed);
            CollectionAssert.AreEqual(new[] { d.roster[0].id }, d.party);
            Assert.AreEqual(Hospital.SanityStart, d.roster[0].sanity);
            // v4: 성격 중립 · 상태 보통 · 스킬 슬롯 비어있음 · 보관함 비어있음
            Assert.AreEqual(Personality.Neutral, d.roster[0].personality);
            Assert.AreEqual(0, d.roster[0].morale);
            Assert.AreEqual(0, d.roster[0].stress);
            Assert.AreEqual(0, d.roster[0].skillRarities.Count);
            Assert.AreEqual(0, d.inventory.Count);
            // v5: 직업 기본값 전사
            Assert.AreEqual(Job.Warrior, d.roster[0].job);

            // 재저장 후 다시 로드해도 v2 그대로
            sm.Save(d);
            var again = sm.Load();
            Assert.AreEqual(SaveData.CurrentSchemaVersion, again.schemaVersion);
            Assert.AreEqual(d.roster[0].id, again.roster[0].id);
        }
    }
}
