using System;
using System.Collections.Generic;
using UnityEngine;
using SoulCommander.Core;
using SoulCommander.Data;

namespace SoulCommander.Save
{
    // 로드 직후 구버전 세이브를 현재 스키마로 끌어올린다. 순수 함수 — 파일 IO 없음.
    public static class SaveMigration
    {
        // 반환: 변환이 일어났으면 true
        public static bool Migrate(SaveData d)
        {
            if (d == null) return false;
            bool migrated = false;
            if (d.schemaVersion == 1)
            {
                MigrateV1ToV2(d);
                migrated = true;
            }
            if (d.schemaVersion == 2)
            {
                MigrateV2ToV3(d);
                migrated = true;
            }
            if (d.schemaVersion == 3)
            {
                MigrateV3ToV4(d);
                migrated = true;
            }
            if (d.schemaVersion == 4)
            {
                MigrateV4ToV5(d);
                migrated = true;
            }
            if (d.schemaVersion == 5)
            {
                MigrateV5ToV6(d);
                migrated = true;
            }
            EnsureCollections(d);
            return migrated;
        }

        private static void MigrateV1ToV2(SaveData d)
        {
            d.gold = 0;
            d.soulStones = 0;
            d.expPool = 0;
            d.ap = GameRules.StartAp;
            d.roster = new List<HeroRecord>();
            d.memorial = new List<MemorialEntry>();
            // v1 슬라이스 영웅은 ★1 Lv1 고정이었다.
            if (!string.IsNullOrEmpty(d.heroRaceId))
            {
                d.roster.Add(new HeroRecord
                {
                    id = HeroRecord.NewId(),
                    name = "주인공",
                    raceId = d.heroRaceId,
                    rank = GameRules.StartRank,
                    level = GameRules.StartLevel,
                });
            }
            d.schemaVersion = 2;
            Debug.Log("[SaveMigration] schemaVersion 1 → 2");
        }

        private static void MigrateV2ToV3(SaveData d)
        {
            d.freeSummonsUsed = 0;
            d.totalSummons = 0;
            d.party = new List<string>();
            if (d.roster != null)
            {
                foreach (var h in d.roster)
                {
                    h.sanity = Hospital.SanityStart;
                    if (d.party.Count < Party.MaxSize) d.party.Add(h.id);
                }
            }
            d.schemaVersion = 3;
            Debug.Log("[SaveMigration] schemaVersion 2 → 3");
        }

        private static void MigrateV3ToV4(SaveData d)
        {
            if (d.roster != null)
            {
                foreach (var h in d.roster)
                {
                    h.personality = Personality.Neutral;
                    h.morale = StateCorrection.MoraleNormal;
                    h.stress = StateCorrection.StressNormal;
                    h.skillRarities = new List<int>();
                }
            }
            d.inventory = new List<EquipmentItem>();
            d.schemaVersion = 4;
            Debug.Log("[SaveMigration] schemaVersion 3 → 4");
        }

        private static void MigrateV4ToV5(SaveData d)
        {
            if (d.roster != null)
            {
                foreach (var h in d.roster)
                {
                    if (string.IsNullOrEmpty(h.job)) h.job = Job.Warrior;
                }
            }
            d.schemaVersion = 5;
            Debug.Log("[SaveMigration] schemaVersion 4 → 5");
        }

        private static void MigrateV5ToV6(SaveData d)
        {
            var estateData = DataLoader.LoadEstate();
            var pop = estateData?.population;
            var morale = estateData?.morale;
            d.estate = new EstateState
            {
                population = pop?.initial ?? 30,
                food = 0,
                morale = morale?.initial ?? 50,
                housingCount = 3,
                currentStageId = "S1",
                lastTickUtc = DateTime.UtcNow.ToString("o"),
                facilities = new List<FacilityState>(),
                activeEdicts = new List<string>()
            };
            if (estateData?.facilities != null)
            {
                foreach (var f in estateData.facilities)
                {
                    d.estate.facilities.Add(new FacilityState
                    {
                        id = f.id,
                        level = f.initial_level,
                        built = f.initial_level > 0,
                        operatorHeroId = null
                    });
                }
            }
            d.schemaVersion = 6;
            Debug.Log("[SaveMigration] schemaVersion 5 → 6");
        }

        private static void EnsureCollections(SaveData d)
        {
            if (d.log == null) d.log = new List<string>();
            if (d.roster == null) d.roster = new List<HeroRecord>();
            if (d.memorial == null) d.memorial = new List<MemorialEntry>();
            if (d.party == null) d.party = new List<string>();
            if (d.inventory == null) d.inventory = new List<EquipmentItem>();
            if (d.estate == null)
            {
                MigrateV5ToV6(d);
            }
            else
            {
                var estateData = DataLoader.LoadEstate();
                if (d.estate.facilities == null || d.estate.facilities.Count == 0)
                {
                    if (estateData?.facilities != null)
                    {
                        foreach (var f in estateData.facilities)
                        {
                            d.estate.facilities.Add(new FacilityState
                            {
                                id = f.id,
                                level = f.initial_level,
                                built = f.initial_level > 0,
                                operatorHeroId = null
                            });
                        }
                    }
                }
                if (d.estate.morale <= 0 && estateData?.morale?.initial > 0) d.estate.morale = estateData.morale.initial;
                if (d.estate.population <= 0 && estateData?.population?.initial > 0) d.estate.population = estateData.population.initial;
                if (d.estate.housingCount <= 0) d.estate.housingCount = 3;
                if (string.IsNullOrEmpty(d.estate.lastTickUtc)) d.estate.lastTickUtc = DateTime.UtcNow.ToString("o");
                if (d.estate.gatheringTeams == null) d.estate.gatheringTeams = new List<GatheringTeamState>();
                if (d.estate.activeEdicts == null) d.estate.activeEdicts = new List<string>();
                if (string.IsNullOrEmpty(d.estate.currentStageId)) d.estate.currentStageId = "S1";
            }
            foreach (var h in d.roster)
            {
                if (h.skillRarities == null) h.skillRarities = new List<int>();
                if (string.IsNullOrEmpty(h.personality)) h.personality = Personality.Neutral;
                if (string.IsNullOrEmpty(h.job)) h.job = Job.Warrior;
            }
        }
    }
}
