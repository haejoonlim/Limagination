using System;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 00 L14 (#5) 행동력. 시간회복 없음 — 회복 수단은 처치뿐.
    public static class ActionPoints
    {
        public static int EntryCost(bool gatekeeperFloor) =>
            gatekeeperFloor ? GameRules.ApCostGateFloor : GameRules.ApCostNormalFloor;

        public static bool CanEnter(SaveData d, bool gatekeeperFloor) => d.ap >= EntryCost(gatekeeperFloor);

        public static bool TrySpendForEntry(SaveData d, bool gatekeeperFloor)
        {
            if (!CanEnter(d, gatekeeperFloor)) return false;
            d.ap -= EntryCost(gatekeeperFloor);
            return true;
        }

        // 처치 +1, MAX 초과분 소멸
        public static void OnKill(SaveData d) => d.ap = Math.Min(GameRules.MaxAp, d.ap + GameRules.ApPerKill);
    }

    public struct RunReward
    {
        public int Floor;
        public int Gold;
        public int SoulStones;
        public int Jackpot;   // 게이트잭팟 (게이트층²×1,000 — 00 L31 #19 · 04 §3.9). 일반층 0.
        public int Exp;
    }

    // 전투 종료(퇴장) 정산. 진입층 기준·승패 무관 (사용자 결정 2026-09-14).
    // 영혼석 = 퇴장층×30 + 게이트잭팟(게이트층²×1,000) (00 L31 #19 · 04 §3.9). 골드에 식민섬 배율은 아직 0 (00 L29 #22).
    // 몬스터 개별 loot 필드는 미사용 (후속).
    public static class RunRewards
    {
        public static RunReward ForFloor(int floor)
        {
            floor = Math.Max(0, floor);
            bool gate = SoulCommander.Battle.WaveBuilder.IsGatekeeperFloor(floor);
            return new RunReward
            {
                Floor = floor,
                Gold = GameRules.GoldPerFloor * floor,
                SoulStones = GameRules.SoulStonesPerFloor * floor,
                Jackpot = gate ? GameRules.GateJackpotPerFloorSq * floor * floor : 0,
                Exp = GameRules.ExpPerFloor * floor,
            };
        }

        public static RunReward Settle(SaveData d, int floor)
        {
            var r = ForFloor(floor);
            d.gold += r.Gold;
            d.soulStones += r.SoulStones + r.Jackpot;
            d.expPool += r.Exp;
            return r;
        }
    }
}
