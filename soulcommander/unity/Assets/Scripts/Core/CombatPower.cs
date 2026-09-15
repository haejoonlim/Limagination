using System;
using SoulCommander.Battle;
using SoulCommander.Data;

namespace SoulCommander.Core
{
    // 05 §7 + 01 §3 기반스탯 13종.
    public struct StatBlock
    {
        public int Hp, Atk, Mag, Pen, Def, MDef, Eva, Aspd, Cdmg, Cri, Mana, SpdCast, Sta;

        public static StatBlock operator +(StatBlock a, StatBlock b) => new StatBlock
        {
            Hp = a.Hp + b.Hp,
            Atk = a.Atk + b.Atk,
            Mag = a.Mag + b.Mag,
            Pen = a.Pen + b.Pen,
            Def = a.Def + b.Def,
            MDef = a.MDef + b.MDef,
            Eva = a.Eva + b.Eva,
            Aspd = a.Aspd + b.Aspd,
            Cdmg = a.Cdmg + b.Cdmg,
            Cri = a.Cri + b.Cri,
            Mana = a.Mana + b.Mana,
            SpdCast = a.SpdCast + b.SpdCast,
            Sta = a.Sta + b.Sta,
        };
    }

    // 01 §3 전투력 v1.0 가안 (05 §7 13종 동기화).
    //   S = HP×0.12 + ATK×2.0 + MAG×2.0 + DEF×1.5 + MDEF×1.5
    //     + ASPD×3.0 + SPD_CAST×2.0 + CRI×3.0 + CDMG×1.0
    //     + PEN×2.5 + EVA×2.5 + MANA×0.05 + STA×0.03
    //   G = S × 등급계수(01 §2) × 레벨계수
    //   CP = round((G + E + K) × P × C × R)
    public static class CombatPower
    {
        public const float HpWeight = 0.12f;
        public const float AtkWeight = 2.0f;
        public const float MagWeight = 2.0f;
        public const float DefWeight = 1.5f;
        public const float MDefWeight = 1.5f;
        public const float AspdWeight = 3.0f;
        public const float SpdCastWeight = 2.0f;
        public const float CriWeight = 3.0f;
        public const float CdmgWeight = 1.0f;
        public const float PenWeight = 2.5f;
        public const float EvaWeight = 2.5f;
        public const float ManaWeight = 0.05f;
        public const float StaWeight = 0.03f;

        // 01 §3 ⑤⑥⑦ 범위
        public const float PersonalityMin = 0.95f, PersonalityMax = 1.10f;
        public const float StateMin = 0.80f, StateMax = 1.10f;
        public const float ResonanceMin = 1.00f, ResonanceMax = 1.10f;

        // 01 §3 ④ 스킬 희귀도 점수: 일반1 / 희귀2 / 영웅3 / 전설5 / 신화8
        public static readonly int[] SkillRarityPoints = { 1, 2, 3, 5, 8 };

        public static float StatScore(StatBlock s) =>
            s.Hp * HpWeight
            + s.Atk * AtkWeight
            + s.Mag * MagWeight
            + s.Def * DefWeight
            + s.MDef * MDefWeight
            + s.Aspd * AspdWeight
            + s.SpdCast * SpdCastWeight
            + s.Cri * CriWeight
            + s.Cdmg * CdmgWeight
            + s.Pen * PenWeight
            + s.Eva * EvaWeight
            + s.Mana * ManaWeight
            + s.Sta * StaWeight;

        // 종족 보정만 적용한 기준 스탯 (등급·레벨은 G 에서 곱한다)
        public static StatBlock RaceBase(RaceEntry race, HeroBaseStats b)
        {
            var m = race?.statMods ?? new RaceStatMods();
            return new StatBlock
            {
                Hp = Round(b.hp * (1f + m.hp / 100f)),
                Atk = Round(b.atk * (1f + m.atk / 100f)),
                Mag = Round(b.mag * (1f + m.mag / 100f)),
                Def = Round(b.def * (1f + m.def / 100f)),
                MDef = Round(b.mdef * (1f + m.mdef / 100f)),
                Aspd = Round(b.aspd * (1f + m.aspd / 100f)),
                Pen = Round(b.pen * (1f + m.pen / 100f)),
                Eva = Round(b.eva * (1f + m.eva / 100f)),
                Cri = Round(b.cri * (1f + m.cri / 100f)),
                Cdmg = Round(b.cdmg * (1f + m.cdmg / 100f)),
                Mana = Round(b.mana * (1f + m.mana / 100f)),
                SpdCast = Round(b.spd_cast * (1f + m.spd_cast / 100f)),
                Sta = Round(b.sta * (1f + m.sta / 100f)),
            };
        }

        public static float Growth(StatBlock baseStats, int rank, int level) =>
            StatScore(baseStats) * BattleSystem.RankMultiplier(rank) * LevelCurve.Multiplier(level);

        public static int Compute(float g, float e, float k, float p, float c, float r)
        {
            p = Clamp(p, PersonalityMin, PersonalityMax);
            c = Clamp(c, StateMin, StateMax);
            r = Clamp(r, ResonanceMin, ResonanceMax);
            return (int)Math.Round((g + e + k) * p * c * r);
        }

        public static float Clamp(float v, float min, float max) => Math.Max(min, Math.Min(max, v));

        private static int Round(float v) => (int)Math.Round(v);
    }
}
