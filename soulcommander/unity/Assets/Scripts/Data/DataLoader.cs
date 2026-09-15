using System.Collections.Generic;
using UnityEngine;

namespace SoulCommander.Data
{
    // Resources/Data/*.json 을 런타임에 직접 로드한다.
    // ScriptableObject bake 은 후속. 현 슬라이스는 파싱 성공만 확인하면 됨.
    public static class DataLoader
    {
        private static RacesRoot _racesCache;
        private static MonstersRoot _monstersCache;
        private static EquipmentRoot _equipmentCache;

        public static RacesRoot LoadRaces()
        {
            if (_racesCache != null) return _racesCache;
            var ta = Resources.Load<TextAsset>("Data/races");
            if (ta == null)
            {
                Debug.LogError("[DataLoader] Resources/Data/races.json missing");
                _racesCache = new RacesRoot { races = new List<RaceEntry>() };
                return _racesCache;
            }
            _racesCache = JsonUtility.FromJson<RacesRoot>(ta.text);
            if (_racesCache?.races == null) _racesCache = new RacesRoot { races = new List<RaceEntry>() };
            return _racesCache;
        }

        public static MonstersRoot LoadMonsters()
        {
            if (_monstersCache != null) return _monstersCache;
            var ta = Resources.Load<TextAsset>("Data/monsters");
            if (ta == null)
            {
                Debug.LogError("[DataLoader] Resources/Data/monsters.json missing");
                _monstersCache = new MonstersRoot { monsters = new List<MonsterEntry>() };
                return _monstersCache;
            }
            _monstersCache = JsonUtility.FromJson<MonstersRoot>(ta.text);
            if (_monstersCache?.monsters == null) _monstersCache = new MonstersRoot { monsters = new List<MonsterEntry>() };
            return _monstersCache;
        }

        public static EquipmentRoot LoadEquipment()
        {
            if (_equipmentCache != null) return _equipmentCache;
            var ta = Resources.Load<TextAsset>("Data/equipment");
            if (ta == null)
            {
                Debug.LogError("[DataLoader] Resources/Data/equipment.json missing");
                _equipmentCache = new EquipmentRoot { meta = new EquipmentMeta(), equipment = new List<EquipmentEntry>() };
                return _equipmentCache;
            }
            _equipmentCache = JsonUtility.FromJson<EquipmentRoot>(ta.text);
            if (_equipmentCache?.equipment == null) _equipmentCache = new EquipmentRoot { meta = new EquipmentMeta(), equipment = new List<EquipmentEntry>() };
            if (_equipmentCache.meta == null) _equipmentCache.meta = new EquipmentMeta();
            return _equipmentCache;
        }

        // 영웅 공통 기준스탯 (races.json meta.heroBaseStats — 가안). 없거나 0 이면 null.
        public static HeroBaseStats GetHeroBaseStats()
        {
            var b = LoadRaces().meta?.heroBaseStats;
            if (b == null || b.hp <= 0)
            {
                Debug.LogError("[DataLoader] races.json meta.heroBaseStats missing");
                return null;
            }
            return b;
        }

        public static RaceEntry GetRace(string id)
        {
            var root = LoadRaces();
            for (int i = 0; i < root.races.Count; i++)
                if (root.races[i].id == id) return root.races[i];
            return null;
        }

        public static MonsterEntry GetMonster(string id)
        {
            var root = LoadMonsters();
            for (int i = 0; i < root.monsters.Count; i++)
                if (root.monsters[i].id == id) return root.monsters[i];
            return null;
        }

        // 테스트에서 캐시 리셋용. Play 시작 시에도 리셋 — 프로젝트가 Enter Play Mode 의
        // Reload Domain 을 끄고 있어 static 캐시가 이전 Play 의 JSON 을 들고 있게 되기 때문.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        public static void ResetCache()
        {
            _racesCache = null;
            _monstersCache = null;
            _equipmentCache = null;
        }
    }
}
