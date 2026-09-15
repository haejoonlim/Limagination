using System;

namespace SoulCommander.Battle
{
    // v8.0 확정: 데미지 감소율 = DEF / (DEF + 200)
    //           최종피해 = ATK × (1 - 감소율)
    // 관통 완화식: (DEF × (1 - pen)) / (DEF × (1 - pen) + 200)
    // 최소피해 1 보장. 위치보정은 감소율 적용 후 곱한다.
    // 05 §7 확장: MAG/MDEF(마법), EVA(회피), CRI/CDMG(치명타) 추가.
    public enum AttackAngle { Front, Flank, Back }
    public enum DamageType { Physical, Magical }

    public static class DamageFormula
    {
        public const int DefConstant = 200;

        // 00 L15 (#6) 위치 D-182: 측면 +10% / 배후 +25% / 고지대 +15% / 커버 ×0.75
        public const float FlankBonus = 0.10f;
        public const float BackBonus = 0.25f;
        public const float HighGroundBonus = 0.15f;
        public const float CoverMultiplier = 0.75f;

        public static int Compute(int atk, int def, float penetration = 0f, float positionMultiplier = 1f)
        {
            if (atk <= 0) return 0;
            if (def < 0) def = 0;
            float effDef = def * (1f - Clamp01(penetration));
            float mitigation = effDef / (effDef + DefConstant);
            float dealt = atk * (1f - mitigation) * positionMultiplier;
            int rounded = (int)Math.Round(dealt);
            return Math.Max(1, rounded);
        }

        // 합산: 가산(측면|배후 택1 + 고지대) 후 커버 곱 (사용자 결정 2026-09-14). 최대 ×1.40
        public static float PositionMultiplier(AttackAngle angle, bool attackerOnHighGround, bool targetInCover)
        {
            float add = angle == AttackAngle.Back ? BackBonus : angle == AttackAngle.Flank ? FlankBonus : 0f;
            if (attackerOnHighGround) add += HighGroundBonus;
            float mul = 1f + add;
            if (targetInCover) mul *= CoverMultiplier;
            return mul;
        }

        // 회피 판정. eva = 0~100 (%)
        public static bool TryEvade(int eva, System.Random rng)
        {
            if (eva <= 0 || rng == null) return false;
            return rng.Next(100) < Clamp(eva, 0, 100);
        }

        // 치명타 판정. cri = 0~100 (%)
        public static bool TryCrit(int cri, System.Random rng)
        {
            if (cri <= 0 || rng == null) return false;
            return rng.Next(100) < Clamp(cri, 0, 100);
        }

        // cdmg = 100 → 2.0배, 150 → 2.5배 (05 §7)
        public static int ApplyCrit(int baseDamage, int cdmg)
        {
            if (cdmg <= 0) return baseDamage;
            float mul = 1f + Clamp(cdmg, 0, 500) / 100f;
            return (int)Math.Round(baseDamage * mul);
        }

        // 물리 공격 전체 (05 §7).
        public static int ComputePhysical(int atk, int def, int pen, int eva, int cri, int cdmg, float posMul, System.Random rng)
        {
            if (TryEvade(eva, rng)) return 0;
            int dmg = Compute(atk, def, pen / 100f, posMul);
            if (TryCrit(cri, rng)) dmg = ApplyCrit(dmg, cdmg);
            return dmg;
        }

        // 마법 공격 전체 (05 §7). 마법은 관통 미적용.
        public static int ComputeMagical(int mag, int mdef, int eva, int cri, int cdmg, float posMul, System.Random rng)
        {
            if (TryEvade(eva, rng)) return 0;
            int dmg = Compute(mag, mdef, 0f, posMul);
            if (TryCrit(cri, rng)) dmg = ApplyCrit(dmg, cdmg);
            return dmg;
        }

        private static float Clamp01(float v) => v < 0 ? 0 : (v > 1 ? 1 : v);
        private static int Clamp(int v, int min, int max) => v < min ? min : (v > max ? max : v);
    }
}
