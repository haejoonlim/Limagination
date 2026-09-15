using System;
using System.Collections.Generic;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 장비 최소 세트 가안 (P3-3 · equipment.json). 획득 = 허브 상점 골드 구매 (사용자 결정 2026-09-14).
    // 강화 스탯 = 기본치 × (1 + 10% × 단계) · 강화비 = 100G × 다음단계 · 상한 +10.
    // TODO(P5): 가격·강화 수치 확정
    public static class EquipmentSystem
    {
        public static EquipmentEntry Find(EquipmentRoot data, string equipId)
        {
            if (data?.equipment == null) return null;
            foreach (var e in data.equipment) if (e.id == equipId) return e;
            return null;
        }

        public static string SlotOf(EquipmentRoot data, EquipmentItem item) => Find(data, item?.equipId)?.slot;

        public static int ShopPrice(EquipmentRoot data, EquipmentEntry e)
        {
            var prices = data.meta.shopPriceByGrade;
            if (prices == null || prices.Count == 0) return int.MaxValue;
            return prices[Math.Max(0, Math.Min(prices.Count - 1, e.grade - 1))];
        }

        public static int EnhanceCost(EquipmentRoot data, EquipmentItem item) =>
            data.meta.enhanceGoldCostPerNextLevel * (item.enhance + 1);

        public static EquipmentItem Buy(SaveData d, EquipmentRoot data, string equipId)
        {
            var e = Find(data, equipId);
            if (e == null) return null;
            int price = ShopPrice(data, e);
            if (d.gold < price) return null;
            d.gold -= price;
            var item = new EquipmentItem { uid = EquipmentItem.NewUid(), equipId = e.id, enhance = 0, equippedBy = "" };
            d.inventory.Add(item);
            return item;
        }

        // 같은 슬롯에 끼고 있던 장비는 보관함으로 돌아간다.
        public static bool Equip(SaveData d, EquipmentRoot data, string itemUid, string heroId)
        {
            var item = d.inventory.Find(x => x.uid == itemUid);
            if (item == null || d.roster.Find(h => h.id == heroId) == null) return false;
            string slot = SlotOf(data, item);
            if (slot == null) return false;
            foreach (var other in d.inventory)
                if (other != item && other.equippedBy == heroId && SlotOf(data, other) == slot) other.equippedBy = "";
            item.equippedBy = heroId;
            return true;
        }

        public static void Unequip(EquipmentItem item) => item.equippedBy = "";

        public static bool TryEnhance(SaveData d, EquipmentRoot data, EquipmentItem item)
        {
            if (item == null || item.enhance >= data.meta.enhanceMax) return false;
            int cost = EnhanceCost(data, item);
            if (d.gold < cost) return false;
            d.gold -= cost;
            item.enhance++;
            return true;
        }

        public static StatBlock ItemStats(EquipmentRoot data, EquipmentItem item)
        {
            var e = Find(data, item?.equipId);
            if (e?.stats == null) return default;
            float mul = 1f + data.meta.enhancePctPerLevel / 100f * item.enhance;
            return new StatBlock
            {
                Hp = Round(e.stats.hp * mul),
                Atk = Round(e.stats.atk * mul),
                Mag = Round(e.stats.mag * mul),
                Def = Round(e.stats.def * mul),
                MDef = Round(e.stats.mdef * mul),
                Aspd = Round(e.stats.aspd * mul),
                Pen = Round(e.stats.pen * mul),
                Eva = Round(e.stats.eva * mul),
                Cri = Round(e.stats.cri * mul),
                Cdmg = Round(e.stats.cdmg * mul),
                Mana = Round(e.stats.mana * mul),
                SpdCast = Round(e.stats.spd_cast * mul),
                Sta = Round(e.stats.sta * mul),
            };
        }

        public static StatBlock EquippedStats(SaveData d, EquipmentRoot data, string heroId)
        {
            var sum = new StatBlock();
            foreach (var item in d.inventory)
                if (item.equippedBy == heroId) sum = sum + ItemStats(data, item);
            return sum;
        }

        public static EquipmentItem EquippedInSlot(SaveData d, EquipmentRoot data, string heroId, string slot) =>
            d.inventory.Find(x => x.equippedBy == heroId && SlotOf(data, x) == slot);

        public static List<EquipmentItem> FreeItemsForSlot(SaveData d, EquipmentRoot data, string slot) =>
            d.inventory.FindAll(x => string.IsNullOrEmpty(x.equippedBy) && SlotOf(data, x) == slot);

        // 사망 시 장비 반환 (03 P1-4): 장착 해제 → 보관함. 반환 개수를 돌려준다.
        public static int ReturnAll(SaveData d, string heroId)
        {
            int n = 0;
            foreach (var item in d.inventory)
            {
                if (item.equippedBy != heroId) continue;
                item.equippedBy = "";
                n++;
            }
            return n;
        }

        private static int Round(float v) => (int)Math.Round(v);
    }
}
