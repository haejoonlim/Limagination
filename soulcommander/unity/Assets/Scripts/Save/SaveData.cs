using System;
using System.Collections.Generic;
using SoulCommander.Core;

namespace SoulCommander.Save
{
    // 세이브 스키마.
    // v1: 슬라이스 최소본 (runsStarted/runsLost/currentFloor/heroRaceId/log)
    // v2: 재화·AP·보유 영웅·추모 기록
    // v3: 소환 횟수·출격 편성·영웅 Sanity (Phase 2)
    // v4: 성격·사기·스트레스·스킬 슬롯·장비 보관함 (Phase 3)
    // v5: 영웅 직업 (05 §4 — Phase 3-4)
    // v6: 영지 상태 — 시설 12종 · 인구 · 식량 · 민심 (Phase 4)
    // 구버전은 SaveMigration 이 로드 시 단계별 변환.
    [Serializable]
    public class SaveData
    {
        public const int CurrentSchemaVersion = 6;

        public int schemaVersion = CurrentSchemaVersion;
        public string createdAt;
        public string updatedAt;
        public int runsStarted;
        public int runsLost;
        public int currentFloor = 1;
        public string heroRaceId; // v1 레거시 — v2 부터는 roster 사용 (마이그레이션 입력용으로만 유지)
        public List<string> log = new List<string>();

        // ---- v2 ----
        public int gold;
        public int soulStones;               // 영혼석(하)
        public int expPool;                  // 경험치 풀 (레벨업은 D-172 곡선 확정 후)
        public int ap = GameRules.StartAp;   // 00 L14 (#5) MAX30 — 초기값 = MAX
        public List<HeroRecord> roster = new List<HeroRecord>();
        public List<MemorialEntry> memorial = new List<MemorialEntry>();

        // ---- v3 ----
        public int freeSummonsUsed;          // 00 L26 (#17) 최초 10회 무료 소진분
        public int totalSummons;
        public List<string> party = new List<string>(); // 출격 편성 hero id — 최대 5 (00 L12 #3)

        // ---- v4 ----
        public List<EquipmentItem> inventory = new List<EquipmentItem>(); // 장비 보관함 (장착 여부는 equippedBy)

        // ---- v6 ----
        public EstateState estate = new EstateState(); // Phase 4 영지 상태
    }

    // 영지 런타임 상태. SaveData v6부터 저장.
    [Serializable]
    public class EstateState
    {
        public int population;
        public int food;
        public int herb;
        public int wood;
        public int ore;
        public int morale;
        public int housingCount = 3; // 초기 3동 (04 §3.1)
        public string currentStageId = "S1";
        public string lastTickUtc; // ISO-8601 UTC. 섬 시간(현실×7) 기준 누적 정산용.
        public int lastEdictChangeFloor; // 칙령 변경 쿨다운 기준층 (04 §3.7)
        public List<FacilityState> facilities = new List<FacilityState>();
        public List<GatheringTeamState> gatheringTeams = new List<GatheringTeamState>();
        public List<FarmPlotState> farmPlots = new List<FarmPlotState>();
        public List<string> activeEdicts = new List<string>();
    }

    [Serializable]
    public class FacilityState
    {
        public string id;
        public int level;
        public string operatorHeroId; // null/empty = 미배치
        public bool built;
        public int constructionRemainingFloors; // 0 = 공사 중 아님. 건설 2층 · 업글 1층 (04 §3.12)
        public int constructionTargetLevel;     // 완료 시 설정될 레벨. 1이면 L1 건설, 2~7은 업그레이드
    }

    [Serializable]
    public class GatheringTeamState
    {
        public string id;
        public int floor;
        public string lastHarvestUtc; // ISO-8601 UTC
        public List<string> memberHeroIds = new List<string>();
    }

    [Serializable]
    public class FarmPlotState
    {
        public string id;
        public string cropId;
        public string plantedAtUtc; // ISO-8601 UTC
    }

    // 보유 영웅 1명. 무한 영웅 생성 시스템 — 고정 주인공 없음.
    [Serializable]
    public class HeroRecord
    {
        public string id;
        public string name;
        public string raceId;
        public int rank;
        public int level;
        public int sanity = Hospital.SanityStart;          // v3 — 01 §5 상태보정 입력원

        // ---- v4 ----
        public string personality = Personality.Neutral;   // 01 §4
        public int morale;                                  // -1 낮음 / 0 보통 / 1 높음 (영지 전 수동)
        public int stress;                                  // 0 보통 / 1 높음 / 2 한계 (영지 전 수동)
        public List<int> skillRarities = new List<int>();   // 스킬 슬롯 구조만 (K)

        // ---- v5 ----
        public string job = Job.Warrior;                    // 05 §4 직업 13종

        public static string NewId() => "hero_" + Guid.NewGuid().ToString("N").Substring(0, 12);
    }

    // 장비 1개 (equipment.json 항목의 인스턴스)
    [Serializable]
    public class EquipmentItem
    {
        public string uid;
        public string equipId;
        public int enhance;
        public string equippedBy; // hero id, 비어 있으면 보관함

        public static string NewUid() => "item_" + Guid.NewGuid().ToString("N").Substring(0, 12);
    }

    // 사망 기록 (00 L13 #4 영구사망). 100층 전당 이관(미정H·I)의 원천 데이터.
    [Serializable]
    public class MemorialEntry
    {
        public string heroId;
        public string name;
        public string raceId;
        public int rank;
        public int floor;
        public string killedBy;
        public string date; // ISO-8601 UTC
        public int returnedEquipment; // 장비 반환 개수 (03 P1-4)
    }
}
