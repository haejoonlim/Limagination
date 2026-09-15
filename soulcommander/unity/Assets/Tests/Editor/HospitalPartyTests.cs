using System;
using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    public class HospitalPartyTests
    {
        private static HeroRecord Hero(string id) => new HeroRecord { id = id, name = id, raceId = "race_human", rank = 1, level = 1 };

        // P2-1 파티: 00 L12 (#3) 출격 5인 상한 · 사망 시 교체불가
        [Test]
        public void Party_Max_Five_Owned_Only_And_Death_Frees_Slot()
        {
            var d = new SaveData();
            for (int i = 0; i < 7; i++) d.roster.Add(Hero("h" + i));

            for (int i = 0; i < 5; i++) Assert.IsTrue(Party.Toggle(d, "h" + i));
            Assert.IsFalse(Party.Toggle(d, "h5"), "6번째 출격 불가 (예비 없음)");
            Assert.AreEqual(5, d.party.Count);
            Assert.IsFalse(Party.Toggle(d, "ghost"), "미보유 영웅 편성 불가");

            Assert.IsTrue(Party.Toggle(d, "h0"), "편성 해제");
            Assert.AreEqual(4, d.party.Count);

            Permadeath.RecordDeath(d, d.roster.Find(h => h.id == "h1"), 3, "고블린", DateTime.UtcNow);
            Assert.IsFalse(d.party.Contains("h1"), "사망자는 편성에서 빠진다");
            Assert.AreEqual(3, Party.Members(d).Count);

            d.party.Add("ghost");
            Party.Sanitize(d);
            Assert.IsFalse(d.party.Contains("ghost"));

            Assert.IsTrue(Party.CanSortie(d));
            d.party.Clear();
            Assert.IsFalse(Party.CanSortie(d));
        }

        // P2-5 병원: 생존자 Sanity 요양만 (00 L13 #4) — 가안 수치
        [Test]
        public void Survivors_Lose_Sanity_And_Hospital_Rests_Two_Lowest()
        {
            var d = new SaveData();
            var a = Hero("a"); var b = Hero("b"); var c = Hero("c"); var e = Hero("e");
            d.roster.AddRange(new[] { a, b, c, e });
            Assert.AreEqual(100, a.sanity);

            Hospital.ApplyBattleStress(d, new[] { "a", "b", "c" }, allyDeaths: 2); // 5 + 10×2
            Assert.AreEqual(75, a.sanity);
            Assert.AreEqual(75, b.sanity);
            Assert.AreEqual(75, c.sanity);
            Assert.AreEqual(100, e.sanity, "불참자는 영향 없음");

            a.sanity = 40;
            b.sanity = 60;
            var rested = Hospital.Rest(d);
            Assert.AreEqual(Hospital.Beds, rested.Count);
            Assert.AreEqual(50, a.sanity);
            Assert.AreEqual(70, b.sanity);
            Assert.AreEqual(75, c.sanity, "병상 2 — 3순위는 대기");
            Assert.AreEqual(4, d.roster.Count, "병원은 부활을 다루지 않는다");
        }
    }
}
