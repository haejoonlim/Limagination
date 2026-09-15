using System;
using System.Collections.Generic;

namespace SoulCommander.Battle
{
    public enum TerrainKind { HighGround, Cover }

    public struct TerrainZone
    {
        public TerrainKind Kind;
        public float X, Z, Radius;
    }

    // 전장 지형 배치 가안 — 층 번호 시드로 고지대·커버 원형 구역을 몇 칸 둔다.
    // TODO(P5): 층별 지형 설계 (00 미등재)
    public class ArenaLayout
    {
        public const float HalfWidth = 9f;
        public const float HalfDepth = 6.5f;
        public const int HighGroundZones = 2;
        public const int CoverZones = 2;
        public const float ZoneRadius = 1.0f;

        public readonly List<TerrainZone> Zones = new List<TerrainZone>();

        public static ArenaLayout ForFloor(int floor)
        {
            var layout = new ArenaLayout();
            var rng = new Random(floor * 7919 + 17);
            for (int i = 0; i < HighGroundZones + CoverZones; i++)
            {
                layout.Zones.Add(new TerrainZone
                {
                    Kind = i < HighGroundZones ? TerrainKind.HighGround : TerrainKind.Cover,
                    X = (float)(rng.NextDouble() * 8.0 - 4.0),
                    Z = (float)(rng.NextDouble() * 8.0 - 4.0),
                    Radius = ZoneRadius,
                });
            }
            return layout;
        }

        public bool IsIn(TerrainKind kind, float x, float z)
        {
            foreach (var zone in Zones)
            {
                if (zone.Kind != kind) continue;
                float dx = x - zone.X, dz = z - zone.Z;
                if (dx * dx + dz * dz <= zone.Radius * zone.Radius) return true;
            }
            return false;
        }

        public static float ClampX(float x) => Math.Max(-HalfWidth, Math.Min(HalfWidth, x));
        public static float ClampZ(float z) => Math.Max(-HalfDepth, Math.Min(HalfDepth, z));
    }

    // 00 L15 (#6) 측면/배후 판정: 대상이 바라보는 방향과 (공격자−대상) 벡터의 각도.
    // 45° 미만 정면 · 45~135° 측면 · 135° 이상 배후 (사용자 승인 2026-09-14)
    public static class Positioning
    {
        public const float FlankMinDeg = 45f;
        public const float BackMinDeg = 135f;

        public static AttackAngle Classify(BattleUnit target, BattleUnit attacker) =>
            Classify(target.X, target.Z, target.FacingX, target.FacingZ, attacker.X, attacker.Z);

        public static AttackAngle Classify(float tx, float tz, float fx, float fz, float ax, float az)
        {
            float dx = ax - tx, dz = az - tz;
            double len = Math.Sqrt(dx * dx + dz * dz);
            double flen = Math.Sqrt(fx * fx + fz * fz);
            if (len < 1e-4 || flen < 1e-4) return AttackAngle.Front;
            double cos = (dx * fx + dz * fz) / (len * flen);
            cos = Math.Max(-1.0, Math.Min(1.0, cos));
            // 경계(45°/135°)의 부동소수 오차 흡수
            double deg = Math.Round(Math.Acos(cos) * 180.0 / Math.PI, 3);
            if (deg < FlankMinDeg) return AttackAngle.Front;
            if (deg < BackMinDeg) return AttackAngle.Flank;
            return AttackAngle.Back;
        }
    }
}
