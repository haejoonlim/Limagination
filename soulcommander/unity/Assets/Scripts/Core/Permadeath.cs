using System;
using System.Collections.Generic;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 00 L13 (#4): 영구사망 · 부활금지. 00 L12 (#3): 사망 시 교체불가.
    // TODO(P5): 100층 영웅의 전당 부활 — 재화·방식 미정H (00 L41), 용도 미정I (00 L42)
    public static class Permadeath
    {
        public static string EquipmentReturnText(int returned) =>
            returned > 0 ? $"장비 반환 {returned}개 → 보관함" : "장착 장비 없음";

        public static MemorialEntry RecordDeath(SaveData d, HeroRecord hero, int floor, string killedBy, DateTime utcNow)
        {
            var entry = new MemorialEntry
            {
                heroId = hero.id,
                name = hero.name,
                raceId = hero.raceId,
                rank = hero.rank,
                floor = floor,
                killedBy = killedBy,
                date = utcNow.ToString("o"),
                returnedEquipment = EquipmentSystem.ReturnAll(d, hero.id), // 03 P1-4 장비반환
            };
            d.memorial.Add(entry);
            d.roster.RemoveAll(h => h.id == hero.id);
            d.party?.Remove(hero.id);
            return entry;
        }

        public static bool IsRunOver(SaveData d) => d.roster == null || d.roster.Count == 0;

        // 전멸 후 신규 세이브: memorial·통계(runsStarted/runsLost)만 보존 (사용자 결정 2026-09-14).
        // 재화·AP·보유영웅·층·소환 무료분은 초기화. log 는 진단용이라 이어 붙인다.
        public static SaveData StartNewRun(SaveData prev, HeroRecord newHero)
        {
            var next = new SaveData
            {
                runsStarted = prev.runsStarted,
                runsLost = prev.runsLost,
                memorial = new List<MemorialEntry>(prev.memorial ?? new List<MemorialEntry>()),
                log = prev.log ?? new List<string>(),
            };
            if (newHero != null)
            {
                next.roster.Add(newHero);
                next.party.Add(newHero.id);
            }
            return next;
        }
    }
}
