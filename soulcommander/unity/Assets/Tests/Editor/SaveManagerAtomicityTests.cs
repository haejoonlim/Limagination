using System.IO;
using NUnit.Framework;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // 세이브 원자성 = 최우선 테스트 (AGENTS §5, README Vertical Slice).
    public class SaveManagerAtomicityTests
    {
        private string _dir;

        [SetUp]
        public void SetUp()
        {
            _dir = Path.Combine(Path.GetTempPath(), "soulcmd_save_test_" + System.Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_dir);
        }

        [TearDown]
        public void TearDown()
        {
            if (Directory.Exists(_dir)) Directory.Delete(_dir, true);
        }

        [Test]
        public void Save_Then_Load_RoundTrip()
        {
            var sm = new SaveManager(_dir, "session_a");
            var d = new SaveData { runsStarted = 3, runsLost = 1, currentFloor = 1, heroRaceId = "race_human" };
            sm.Save(d);
            var loaded = sm.Load(out bool corrupt);
            Assert.IsFalse(corrupt);
            Assert.AreEqual(3, loaded.runsStarted);
            Assert.AreEqual(1, loaded.runsLost);
            Assert.AreEqual(1, loaded.currentFloor);
            Assert.AreEqual("race_human", loaded.heroRaceId);
        }

        [Test]
        public void Tmp_File_Should_Not_Persist_After_Save()
        {
            var sm = new SaveManager(_dir, "session_b");
            sm.Save(new SaveData { runsStarted = 1 });
            Assert.IsFalse(File.Exists(sm.TmpPath), "임시파일은 원자 교체 후 남아있으면 안 됨");
            Assert.IsTrue(File.Exists(sm.FilePath), "본 세이브 파일이 존재해야 함");
        }

        [Test]
        public void Corrupt_File_Is_Quarantined_And_Fresh_Returned()
        {
            var sm = new SaveManager(_dir, "session_c");
            // 손상된 JSON 을 직접 심는다
            File.WriteAllText(sm.FilePath, "{ this is not valid json ");
            var loaded = sm.Load(out bool corrupt);
            Assert.IsTrue(corrupt, "손상된 JSON 은 corrupt=true 여야 함");
            Assert.IsNotNull(loaded);
            Assert.IsTrue(File.Exists(sm.CorruptPath), ".corrupt.bak 로 격리돼야 함");
            Assert.IsFalse(File.Exists(sm.FilePath), "손상 원본은 격리 후 사라져야 함");
        }

        [Test]
        public void Overwrite_Preserves_File_On_Save()
        {
            var sm = new SaveManager(_dir, "session_d");
            sm.Save(new SaveData { runsStarted = 1 });
            long size1 = new FileInfo(sm.FilePath).Length;
            sm.Save(new SaveData { runsStarted = 2, runsLost = 5 });
            Assert.IsTrue(File.Exists(sm.FilePath));
            var loaded = sm.Load();
            Assert.AreEqual(2, loaded.runsStarted);
            Assert.AreEqual(5, loaded.runsLost);
        }

        [Test]
        public void Session_Isolation()
        {
            var a = new SaveManager(_dir, "player_a");
            var b = new SaveManager(_dir, "player_b");
            a.Save(new SaveData { runsStarted = 10 });
            b.Save(new SaveData { runsStarted = 20 });
            Assert.AreEqual(10, a.Load().runsStarted);
            Assert.AreEqual(20, b.Load().runsStarted);
            Assert.AreNotEqual(a.FilePath, b.FilePath);
        }
    }
}
