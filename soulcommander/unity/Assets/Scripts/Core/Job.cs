namespace SoulCommander.Core
{
    // 05 §4 직업 13종: 공통 8 + 계열 희귀 5
    public static class Job
    {
        // 공통
        public const string Warrior = "warrior";
        public const string Guardian = "guardian";
        public const string Assassin = "assassin";
        public const string Archer = "archer";
        public const string Mage = "mage";
        public const string Supporter = "supporter";
        public const string Paladin = "paladin";
        public const string Druid = "druid";

        // 계열 희귀
        public const string Berserker = "berserker";     // 전사 — 오크 전용
        public const string AbyssMage = "abyss_mage";    // 심연 — 뱀파이어 전용
        public const string MountainKnight = "mountain_knight"; // 드워프 계열
        public const string GaleMonk = "gale_monk";      // 짐승
        public const string Sage = "sage";               // 인간·엘프

        public static readonly string[] All =
        {
            Warrior, Guardian, Assassin, Archer, Mage, Supporter, Paladin, Druid,
            Berserker, AbyssMage, MountainKnight, GaleMonk, Sage
        };

        public static readonly string[] Common =
        {
            Warrior, Guardian, Assassin, Archer, Mage, Supporter, Paladin, Druid
        };

        // 05 §4 직업 계수 (HP/ATK/DEF/ASPD/MAG)
        public static JobCoeffs Coeffs(string job)
        {
            switch (job)
            {
                case Warrior: return new JobCoeffs(1.2f, 1.0f, 1.0f, 1.0f, 0.5f);
                case Guardian: return new JobCoeffs(1.8f, 0.7f, 1.5f, 0.8f, 0.4f);
                case Assassin: return new JobCoeffs(0.8f, 1.3f, 0.6f, 1.4f, 0.5f);
                case Archer: return new JobCoeffs(0.9f, 1.1f, 0.7f, 1.2f, 0.5f);
                case Mage: return new JobCoeffs(0.7f, 0.8f, 0.5f, 0.9f, 1.5f);
                case Supporter: return new JobCoeffs(0.9f, 0.6f, 0.8f, 1.1f, 1.2f);
                case Paladin: return new JobCoeffs(1.6f, 0.8f, 1.3f, 0.8f, 0.7f);
                case Druid: return new JobCoeffs(1.0f, 0.7f, 0.9f, 0.9f, 1.3f);
                case Berserker: return new JobCoeffs(1.4f, 1.6f, 0.5f, 1.0f, 0.3f);
                case AbyssMage: return new JobCoeffs(0.8f, 0.9f, 0.6f, 0.9f, 1.8f);
                case MountainKnight: return new JobCoeffs(1.5f, 1.0f, 1.4f, 0.7f, 0.5f);
                case GaleMonk: return new JobCoeffs(1.0f, 1.2f, 0.7f, 1.8f, 0.4f);
                case Sage: return new JobCoeffs(0.8f, 0.7f, 0.7f, 0.9f, 1.6f);
                default: return new JobCoeffs(1.0f, 1.0f, 1.0f, 1.0f, 1.0f);
            }
        }
    }

    public readonly struct JobCoeffs
    {
        public readonly float Hp, Atk, Def, Aspd, Mag;
        public JobCoeffs(float hp, float atk, float def, float aspd, float mag)
        {
            Hp = hp; Atk = atk; Def = def; Aspd = aspd; Mag = mag;
        }
    }
}
