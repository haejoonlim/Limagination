using System;

namespace SoulCommander.Core
{
    // 01 §4 성격 7종 가안. P(CP 보정)에만 반영 — 전투 스탯 효과는 후속 (사용자 결정 2026-09-14).
    // 부여: 영웅 생성 시 7종 균등 랜덤 · 허브에서 수동 변경 가능.
    public static class Personality
    {
        public const string Neutral = "neutral";
        public static readonly string[] Keys = { "brave", "careful", "cool", "berserk", "devoted", "cunning", Neutral };

        public static float Multiplier(string key)
        {
            switch (key)
            {
                case "brave": return 1.03f;    // 용감 — ATK +5%
                case "careful": return 1.02f;  // 신중 — DEF +5%
                case "cool": return 1.02f;     // 냉정 — CRI +3%
                case "berserk": return 1.04f;  // 광폭 — ATK +8% / DEF -3%
                case "devoted": return 1.00f;  // 헌신 — 힐러만 1.02. 힐러 개념 전까지 1.00. TODO(P5)
                case "cunning": return 1.02f;  // 교활 — 회피 +5%
                default: return 1.00f;         // 중립
            }
        }

        public static string DisplayName(string key)
        {
            switch (key)
            {
                case "brave": return "용감";
                case "careful": return "신중";
                case "cool": return "냉정";
                case "berserk": return "광폭";
                case "devoted": return "헌신";
                case "cunning": return "교활";
                default: return "중립";
            }
        }

        public static string Random(System.Random rng) => Keys[rng.Next(Keys.Length)];

        public static string Next(string key)
        {
            int i = Array.IndexOf(Keys, key);
            return Keys[(i + 1) % Keys.Length];
        }
    }
}
