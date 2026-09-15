using UnityEngine;

namespace SoulCommander.Battle
{
    // 전장 유닛. 캡슐 프리미티브 하나로 표시.
    // ASPD 는 "초당 공격 횟수" (05 §7). attackInterval = 1 / ASPD (최소 0.25초, 최대 3초).
    public class BattleUnit
    {
        public string DisplayName;
        public int MaxHp;
        public int Hp;
        public int Atk;   // 물리 공격력
        public int Mag;   // 마법 공격력
        public int Def;   // 물리 방어
        public int MDef;  // 마법 방어
        public int Aspd;  // 공격속도 (초당 공격)
        public int Pen;   // 관통 (0~100%)
        public int Eva;   // 회피 (0~100%)
        public int Cri;   // 치명타 확률 (0~100%)
        public int Cdmg;  // 치명타 피핵 (100% 기준 추가 배율)
        public int Mana;  // 스킬 자원
        public int SpdCast; // 시전속도
        public int Sta;   // 스태미너
        public float AttackCooldown; // 초 (남은 쿨)
        public GameObject Visual;    // 캡슐 프리미티브
        public bool IsHero;
        public string HeroId;   // 세이브 roster 연결 (영웅만)
        public string KilledBy; // 마지막 일격을 가한 유닛 이름

        // 아레나 좌표(XZ 평면)·바라보는 방향 — 위치보정 판정용
        public float X, Z;
        public float FacingX = 1f, FacingZ;
        public bool HasMoveTarget;
        public float MoveX, MoveZ;

        // 공명 (영웅만): 공명 적용 전 스탯
        public string Lineage;
        public int BaseMaxHp, BaseAtk;
        public float ResonanceMul = 1f;

        public bool IsAlive => Hp > 0;

        // ASPD 1 = 1초/공, ASPD 4 = 0.25초/공. 05 §7 튜닝값.
        public float AttackInterval => Mathf.Clamp(1f / Mathf.Max(0.25f, Aspd / 50f), 0.25f, 3f);

        public void ResetCooldown() => AttackCooldown = AttackInterval;

        public void TakeDamage(int dmg)
        {
            Hp = Mathf.Max(0, Hp - dmg);
        }
    }
}
