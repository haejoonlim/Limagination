using System;
using NUnit.Framework;
using UnityEngine;
using SoulCommander.Core;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // 00 L13 (#4) 영구사망 · 00 L12 (#3) 교체불가
    public class PermadeathTests
    {
        [Test]
        public void Death_Writes_Memorial_And_New_Run_Keeps_Only_Memorial_And_Stats()
        {
            var d = new SaveData { runsStarted = 3, runsLost = 2, gold = 500, soulStones = 60, expPool = 160, ap = 12, currentFloor = 1 };
            var hero = new HeroRecord { id = "hero_a", name = "시온", raceId = "race_human", rank = 1, level = 1 };
            d.roster.Add(hero);

            var when = new DateTime(2026, 9, 14, 12, 0, 0, DateTimeKind.Utc);
            var e = Permadeath.RecordDeath(d, hero, 1, "스켈레톤", when);

            Assert.AreEqual(1, d.memorial.Count);
            Assert.AreEqual("시온", e.name);
            Assert.AreEqual(1, e.floor);
            Assert.AreEqual("스켈레톤", e.killedBy);
            Assert.AreEqual(when.ToString("o"), e.date);
            Assert.AreEqual(0, d.roster.Count, "부활 없음 — roster 에서 제거");
            Assert.IsTrue(Permadeath.IsRunOver(d));

            var newHero = new HeroRecord { id = "hero_b", name = "리프", raceId = "race_woodelf", rank = 1, level = 1 };
            var next = Permadeath.StartNewRun(d, newHero);

            Assert.AreEqual(3, next.runsStarted);
            Assert.AreEqual(2, next.runsLost);
            Assert.AreEqual(0, next.gold);
            Assert.AreEqual(0, next.soulStones);
            Assert.AreEqual(0, next.expPool);
            Assert.AreEqual(GameRules.MaxAp, next.ap);
            Assert.AreEqual(1, next.roster.Count);
            Assert.AreEqual("hero_b", next.roster[0].id);
            CollectionAssert.AreEqual(new[] { "hero_b" }, next.party);
            Assert.AreEqual(0, next.freeSummonsUsed, "소환 무료분도 신규 런에서 초기화");

            // 추모 기록은 세이브 직렬화를 거쳐도 남는다
            var rt = JsonUtility.FromJson<SaveData>(JsonUtility.ToJson(next));
            Assert.AreEqual(1, rt.memorial.Count);
            Assert.AreEqual("시온", rt.memorial[0].name);
            Assert.AreEqual("스켈레톤", rt.memorial[0].killedBy);
        }
    }
}
