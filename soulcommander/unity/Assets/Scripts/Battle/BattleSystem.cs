using System;
using System.Collections.Generic;
using UnityEngine;
using SoulCommander.Core;
using SoulCommander.Data;

namespace SoulCommander.Battle
{
    public enum BattleOutcome { Ongoing, Victory, Defeat }

    // 1~3층 완전자동 / 4층+ 전술개입 (이동·집중 — Gauge 가 게이트).
    // Arena 가 있으면 위치보정(00 L15 #6) 적용. 공명 tier3 는 보유 기준 판정·출격 적용·사망 시 재계산.
    public class BattleSystem
    {
        public readonly List<BattleUnit> Heroes = new List<BattleUnit>();
        public readonly List<BattleUnit> Enemies = new List<BattleUnit>();
        public BattleOutcome Outcome = BattleOutcome.Ongoing;

        public readonly int Floor;
        public readonly ArenaLayout Arena;   // null 이면 위치보정 없음
        public readonly TacticalGauge Gauge;

        public BattleUnit FocusTarget { get; private set; }
        public float FocusRemaining { get; private set; }

        private Dictionary<string, int> _ownedByLineage;
        private readonly System.Random _rng;

        public event Action<string> OnLog;
        public event Action<BattleUnit, BattleUnit, int> OnHit;
        public event Action<BattleOutcome> OnEnded;

        public BattleSystem() : this(1, null, 0) { }

        public BattleSystem(int floor, ArenaLayout arena, int seed = 0)
        {
            Floor = floor;
            Arena = arena;
            Gauge = new TacticalGauge(floor);
            _rng = seed == 0 ? new System.Random() : new System.Random(seed);
        }

        // equipment: 장착 장비 합산 스탯 (등급·레벨 곱 이후 가산)
        public BattleUnit AddHero(string heroId, string name, RaceEntry race, HeroBaseStats baseStats, int rankTier, int level,
                                  StatBlock equipment = default)
        {
            float rankMul = RankMultiplier(rankTier);
            float lvMul = LevelCurve.Multiplier(level);

            var stats = CombatStats.FromRace(race, baseStats, rankMul);
            int maxHp = Mathf.RoundToInt(stats.Hp * lvMul) + equipment.Hp;
            int atk = Mathf.RoundToInt(stats.Atk * lvMul) + equipment.Atk;
            var u = new BattleUnit
            {
                DisplayName = name,
                MaxHp = maxHp,
                Hp = maxHp,
                Atk = atk,
                Mag = Mathf.RoundToInt(stats.Mag * lvMul) + equipment.Mag,
                Def = Mathf.RoundToInt(stats.Def * lvMul) + equipment.Def,
                MDef = Mathf.RoundToInt(stats.MDef * lvMul) + equipment.MDef,
                Aspd = stats.Aspd + equipment.Aspd,
                Pen = stats.Pen + equipment.Pen,
                Eva = stats.Eva + equipment.Eva,
                Cri = stats.Cri + equipment.Cri,
                Cdmg = stats.Cdmg + equipment.Cdmg,
                Mana = stats.Mana + equipment.Mana,
                SpdCast = stats.SpdCast + equipment.SpdCast,
                Sta = stats.Sta + equipment.Sta,
                IsHero = true,
                HeroId = heroId,
                Lineage = race?.lineage,
                BaseMaxHp = maxHp,
                BaseAtk = atk,
                FacingX = 1f,
            };
            u.ResetCooldown();
            Heroes.Add(u);
            return u;
        }

        public BattleUnit AddEnemyFromMonster(MonsterEntry m)
        {
            if (m == null) throw new ArgumentNullException(nameof(m));
            return AddEnemy(m.name, CombatStats.FromMonster(m));
        }

        public BattleUnit AddEnemy(string name, CombatStats s)
        {
            var u = new BattleUnit
            {
                DisplayName = name,
                MaxHp = s.Hp,
                Hp = s.Hp,
                Atk = s.Atk,
                Mag = s.Mag,
                Def = s.Def,
                MDef = s.MDef,
                Aspd = s.Aspd,
                Pen = s.Pen,
                Eva = s.Eva,
                Cri = s.Cri,
                Cdmg = s.Cdmg,
                Mana = s.Mana,
                SpdCast = s.SpdCast,
                Sta = s.Sta,
                IsHero = false,
                FacingX = -1f,
            };
            u.ResetCooldown();
            Enemies.Add(u);
            return u;
        }

        // 등급계수 (01 §2 · 00 L16 #7 — 등급당 ×1.3 복리, 2026-09-14 개정). ★1~7 = 1..7.
        public static float RankMultiplier(int rank)
        {
            switch (rank)
            {
                case 1: return 1.00f;
                case 2: return 1.30f;
                case 3: return 1.69f;
                case 4: return 2.20f;
                case 5: return 2.86f;
                case 6: return 3.71f;
                case 7: return 4.83f;
                default: return 1.00f;
            }
        }

        // ============ 공명 ============

        public void SetOwnedLineageCounts(Dictionary<string, int> ownedByLineage)
        {
            _ownedByLineage = ownedByLineage == null ? null : new Dictionary<string, int>(ownedByLineage);
            ApplyResonance();
        }

        // 전투 중 영웅 사망 → 보유 수 감소 → 공명 재계산 (races.json resonance.note)
        public void HandleHeroDeath(BattleUnit hero)
        {
            if (hero == null || !hero.IsHero || _ownedByLineage == null || string.IsNullOrEmpty(hero.Lineage)) return;
            if (!_ownedByLineage.TryGetValue(hero.Lineage, out int n) || n <= 0) return;
            int before = Resonance.Tier(_ownedByLineage, hero.Lineage);
            _ownedByLineage[hero.Lineage] = n - 1;
            int after = Resonance.Tier(_ownedByLineage, hero.Lineage);
            if (before != after) OnLog?.Invoke($"공명 재계산: {hero.Lineage} 보유 {n - 1}명 → tier{after}");
            ApplyResonance();
        }

        private void ApplyResonance()
        {
            foreach (var u in Heroes)
            {
                if (!u.IsAlive) continue;
                float mul = Resonance.HpAtkMultiplier(_ownedByLineage, u.Lineage);
                if (Math.Abs(mul - u.ResonanceMul) < 0.0001f) continue;
                int newMax = Mathf.RoundToInt(u.BaseMaxHp * mul);
                u.Hp = Math.Max(1, Mathf.RoundToInt((float)u.Hp * newMax / Math.Max(1, u.MaxHp)));
                u.MaxHp = newMax;
                u.Atk = Mathf.RoundToInt(u.BaseAtk * mul);
                u.ResonanceMul = mul;
            }
        }

        // ============ 전술 명령 (4층+) ============

        public bool CommandMove(BattleUnit hero, float x, float z)
        {
            if (Outcome != BattleOutcome.Ongoing || hero == null || !hero.IsHero || !hero.IsAlive) return false;
            if (!Gauge.TrySpend(TacticalCommands.MoveCost)) return false;
            hero.MoveX = ArenaLayout.ClampX(x);
            hero.MoveZ = ArenaLayout.ClampZ(z);
            hero.HasMoveTarget = true;
            OnLog?.Invoke($"[명령] 이동: {hero.DisplayName} → ({hero.MoveX:0.0}, {hero.MoveZ:0.0}) · 게이지 -{TacticalCommands.MoveCost:0}");
            return true;
        }

        public bool CommandFocus(BattleUnit enemy)
        {
            if (Outcome != BattleOutcome.Ongoing || enemy == null || enemy.IsHero || !enemy.IsAlive) return false;
            if (!Gauge.TrySpend(TacticalCommands.FocusCost)) return false;
            FocusTarget = enemy;
            FocusRemaining = TacticalCommands.FocusDuration;
            OnLog?.Invoke($"[명령] 집중: {enemy.DisplayName} {TacticalCommands.FocusDuration:0}초 · 게이지 -{TacticalCommands.FocusCost:0}");
            return true;
        }

        // ============ 진행 ============

        public void Tick(float dt)
        {
            if (Outcome != BattleOutcome.Ongoing) return;

            Gauge.Tick(dt);
            if (FocusRemaining > 0f)
            {
                FocusRemaining -= dt;
                if (FocusRemaining <= 0f || FocusTarget == null || !FocusTarget.IsAlive)
                {
                    FocusRemaining = 0f;
                    FocusTarget = null;
                }
            }

            TickSide(Heroes, Enemies, dt);
            if (Outcome != BattleOutcome.Ongoing) return;
            TickSide(Enemies, Heroes, dt);

            EvaluateOutcome();
        }

        private void TickSide(List<BattleUnit> attackers, List<BattleUnit> targets, float dt)
        {
            for (int i = 0; i < attackers.Count; i++)
            {
                var a = attackers[i];
                if (!a.IsAlive) continue;
                if (a.HasMoveTarget)
                {
                    StepMove(a, dt); // 이동 중에는 공격하지 않음
                    continue;
                }
                a.AttackCooldown -= dt;
                if (a.AttackCooldown > 0f) continue;
                var target = ChooseTarget(a, targets);
                if (target == null) return;

                float posMul = 1f;
                string posTag = "";
                if (Arena != null)
                {
                    var angle = Positioning.Classify(target, a);
                    bool onHigh = Arena.IsIn(TerrainKind.HighGround, a.X, a.Z);
                    bool inCover = Arena.IsIn(TerrainKind.Cover, target.X, target.Z);
                    posMul = DamageFormula.PositionMultiplier(angle, onHigh, inCover);
                    posTag = PositionTag(angle, onHigh, inCover);
                }
                Face(a, target.X - a.X, target.Z - a.Z);

                // 공격 유형: MAG가 ATK보다 20% 이상 높으면 마법 공격 (05 §7 임시 판정 — 스킬 시스템 후속 교체)
                bool magical = a.Mag >= a.Atk * 1.2f;
                int dmg = magical
                    ? DamageFormula.ComputeMagical(a.Mag, target.MDef, target.Eva, a.Cri, a.Cdmg, posMul, _rng)
                    : DamageFormula.ComputePhysical(a.Atk, target.Def, a.Pen, target.Eva, a.Cri, a.Cdmg, posMul, _rng);

                string tag = posTag;
                if (dmg == 0) tag += " [회피]";
                else if (magical) tag += " [마법]";

                if (dmg > 0) target.TakeDamage(dmg);
                if (a.IsHero && !target.IsAlive) Gauge.OnKill();
                OnHit?.Invoke(a, target, dmg);
                OnLog?.Invoke($"{a.DisplayName} → {target.DisplayName} : {dmg} 피해{tag} (HP {target.Hp}/{target.MaxHp})");
                a.ResetCooldown();
                if (!target.IsAlive)
                {
                    target.KilledBy = a.DisplayName;
                    OnLog?.Invoke($"{target.DisplayName} 쓰러짐.");
                    if (target.IsHero) HandleHeroDeath(target);
                }
            }
        }

        private BattleUnit ChooseTarget(BattleUnit a, List<BattleUnit> targets)
        {
            if (a.IsHero && FocusTarget != null && FocusTarget.IsAlive && FocusRemaining > 0f) return FocusTarget;
            BattleUnit best = null;
            float bestD = float.MaxValue;
            foreach (var t in targets)
            {
                if (!t.IsAlive) continue;
                float dx = t.X - a.X, dz = t.Z - a.Z;
                float d = dx * dx + dz * dz;
                if (d < bestD)
                {
                    bestD = d;
                    best = t;
                }
            }
            return best;
        }

        private static void StepMove(BattleUnit u, float dt)
        {
            float dx = u.MoveX - u.X, dz = u.MoveZ - u.Z;
            float dist = (float)Math.Sqrt(dx * dx + dz * dz);
            float step = TacticalCommands.MoveSpeed * dt;
            if (dist <= step || dist < 1e-4f)
            {
                u.X = u.MoveX;
                u.Z = u.MoveZ;
                u.HasMoveTarget = false;
                return;
            }
            u.X += dx / dist * step;
            u.Z += dz / dist * step;
            Face(u, dx, dz);
        }

        private static void Face(BattleUnit u, float dx, float dz)
        {
            float len = (float)Math.Sqrt(dx * dx + dz * dz);
            if (len < 1e-4f) return;
            u.FacingX = dx / len;
            u.FacingZ = dz / len;
        }

        private static string PositionTag(AttackAngle angle, bool onHigh, bool inCover)
        {
            var parts = new List<string>();
            if (angle == AttackAngle.Flank) parts.Add("측면");
            if (angle == AttackAngle.Back) parts.Add("배후");
            if (onHigh) parts.Add("고지대");
            if (inCover) parts.Add("커버");
            return parts.Count == 0 ? "" : " [" + string.Join("·", parts) + "]";
        }

        private static BattleUnit FirstAlive(List<BattleUnit> list)
        {
            for (int i = 0; i < list.Count; i++)
                if (list[i].IsAlive) return list[i];
            return null;
        }

        private void EvaluateOutcome()
        {
            bool heroAlive = FirstAlive(Heroes) != null;
            bool enemyAlive = FirstAlive(Enemies) != null;
            if (!heroAlive) { Outcome = BattleOutcome.Defeat; OnEnded?.Invoke(Outcome); return; }
            if (!enemyAlive) { Outcome = BattleOutcome.Victory; OnEnded?.Invoke(Outcome); return; }
        }
    }
}
