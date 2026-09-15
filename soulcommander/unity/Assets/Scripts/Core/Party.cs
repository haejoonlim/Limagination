using System.Collections.Generic;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 00 L12 (#3): 출격 5인 · 예비 없음 · 사망 시 교체불가.
    // 출격 1~5명 허용 (사용자 결정 2026-09-14). 매 층 허브 복귀 구조라 교체불가는 전투 중에만 해당하고,
    // 빈 슬롯은 허브에서 보유 영웅으로 채운다.
    public static class Party
    {
        public const int MaxSize = 5;
        public const int MinSize = 1;

        public static bool Contains(SaveData d, string heroId) => d.party.Contains(heroId);

        // 편성 토글. 추가는 보유 영웅 + 5명 미만일 때만.
        public static bool Toggle(SaveData d, string heroId)
        {
            if (d.party.Remove(heroId)) return true;
            if (d.party.Count >= MaxSize) return false;
            if (d.roster.Find(h => h.id == heroId) == null) return false;
            d.party.Add(heroId);
            return true;
        }

        // 보유하지 않은 id·중복 제거, 상한 초과분 절삭.
        public static void Sanitize(SaveData d)
        {
            var seen = new HashSet<string>();
            d.party.RemoveAll(id => !seen.Add(id) || d.roster.Find(h => h.id == id) == null);
            if (d.party.Count > MaxSize) d.party.RemoveRange(MaxSize, d.party.Count - MaxSize);
        }

        public static List<HeroRecord> Members(SaveData d)
        {
            Sanitize(d);
            var list = new List<HeroRecord>();
            foreach (var id in d.party) list.Add(d.roster.Find(h => h.id == id));
            return list;
        }

        public static bool CanSortie(SaveData d) => Members(d).Count >= MinSize;
    }
}
