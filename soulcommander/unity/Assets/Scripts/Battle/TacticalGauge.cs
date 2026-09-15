using System;

namespace SoulCommander.Battle
{
    // 전술게이지. 수치 근거: AGENTS §4 전투 행 · 03 P2-3 (00 #6 행에는 게이지 수치 없음).
    // 1~3층 완전자동(게이지 비활성) / 4층+ 전술개입.
    public class TacticalGauge
    {
        public const float Max = 100f;
        public const float StartValue = 50f;
        public const float PerSecond = 2f;
        public const float PerKill = 10f;
        public const int TacticalFromFloor = 4;

        public readonly bool Enabled;
        public float Value { get; private set; }

        public TacticalGauge(int floor)
        {
            Enabled = floor >= TacticalFromFloor;
            Value = StartValue;
        }

        public static bool IsTacticalFloor(int floor) => floor >= TacticalFromFloor;

        public void Tick(float dt) => Value = Math.Min(Max, Math.Max(0f, Value + PerSecond * dt));

        public void OnKill() => Value = Math.Min(Max, Value + PerKill);

        public bool CanSpend(float cost) => Enabled && Value >= cost;

        public bool TrySpend(float cost)
        {
            if (!CanSpend(cost)) return false;
            Value -= cost;
            return true;
        }
    }

    // 전술 명령 (4층+). 비용·지속·이동속도 가안 — 사용자 결정 2026-09-14, 00 미등재. TODO(P5)
    // 04 §3.10 전술소 L1 = 이동·집중.
    public static class TacticalCommands
    {
        public const float MoveCost = 20f;
        public const float FocusCost = 30f;
        public const float FocusDuration = 8f;
        public const float MoveSpeed = 3f; // 아레나 단위/초
    }
}
