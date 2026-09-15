using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.UI;
using SoulCommander.Data;
using SoulCommander.Save;
using SoulCommander.Battle;

namespace SoulCommander.Core
{
    // 게임 진입점.
    // 씬 로드 후 자동으로 게임오브젝트/UI 구성. 씬 파일에는 카메라/방향광만 존재한다.
    // 흐름 (Phase 2): 허브(편성·소환) → 층 전투 → 결산 → 리로드 → 허브 (매 층 허브 복귀 — 사용자 결정 2026-09-14)
    public class GameRoot : MonoBehaviour
    {
        private const int RosterPageSize = 10;

        private enum CommandMode { None, MovePickHero, MovePickPoint, FocusPickEnemy }

        private GameState _state;
        private SaveManager _save;
        private SaveData _data;
        private BattleSystem _battle;
        private readonly System.Random _rng = new System.Random();

        // 이번 전투
        private int _runFloor;
        private BattleOutcome _lastOutcome;
        private RunReward _lastReward;
        private bool _lastFloorAdvanced;
        private readonly List<MemorialEntry> _lastDeaths = new List<MemorialEntry>();
        private readonly List<HeroRecord> _lastRested = new List<HeroRecord>();
        private readonly Dictionary<GameObject, BattleUnit> _unitByVisual = new Dictionary<GameObject, BattleUnit>();
        private readonly List<GameObject> _terrainVisuals = new List<GameObject>();
        private CommandMode _mode;
        private BattleUnit _moveHero;

        // UI 참조
        private Font _font;
        private Canvas _canvas;
        private Text _title;
        private Text _statusLine;
        private Text _log;
        private Text _hpBar;
        private Button _actionButton;
        private Text _actionButtonLabel;
        private GameObject _hubPanel;
        private GameObject _battlePanel;
        private GameObject _gameOverPanel;
        private Slider _gaugeSlider;
        private Text _gaugeLabel;
        private Button _moveButton;
        private Button _focusButton;
        private Text _commandHint;
        private Button[] _rosterButtons;
        private Text[] _rosterLabels;
        private Button _prevPageButton;
        private Button _nextPageButton;
        private Button _summonButton;
        private Text _summonLabel;
        private int _rosterPage;
        private GameObject _ground;
        private Shader _litShader;

        // 허브 영웅 상세 (Phase 3: CP·성격·상태·장비·★7)
        private static readonly string[] SlotKeys = { "weapon", "armor", "accessory" };
        private static readonly string[] SlotNames = { "무기", "방어구", "장신구" };
        private string _selectedHeroId;
        private Text _detailTitle;
        private Text _detailCp;
        private Text _detailPartyLabel;
        private Button _detailTranscendButton;
        private Text _detailTranscendLabel;
        private Text _moraleLabel;
        private Text _stressLabel;
        private Text[] _slotLabels;
        private Button[] _slotSwapButtons;
        private Button[] _slotEnhanceButtons;
        private Text[] _slotEnhanceLabels;
        private readonly List<KeyValuePair<Button, EquipmentEntry>> _shopButtons = new List<KeyValuePair<Button, EquipmentEntry>>();

        private readonly Queue<string> _logLines = new Queue<string>();
        private const int LogMaxLines = 12;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AutoBoot()
        {
            if (FindAnyObjectByType<GameRoot>() != null) return;
            var go = new GameObject("GameRoot");
            go.AddComponent<GameRoot>();
        }

        private void Awake()
        {
            _save = SaveManager.ForPlayer();
            _data = _save.Load(out bool corrupted);
            if (corrupted) AppendLog("이전 세이브 손상 감지. .corrupt.bak 로 격리 후 신규 세이브 시작.");

            _font = Resources.Load<Font>("Fonts/NanumGothic");

            BuildUI();
            EnterState(GameState.Hub);
        }

        private void Update()
        {
            if (_state != GameState.Battle || _battle == null) return;
            _battle.Tick(Time.deltaTime);
            SyncUnitVisuals();
            if (_state != GameState.Battle) return; // Tick 안에서 전투가 끝났으면 결산 화면 유지
            HandleTacticalInput();
            UpdateBattleHud();
        }

        // ============ 상태 전이 ============

        private void EnterState(GameState next)
        {
            _state = next;
            _hubPanel.SetActive(next == GameState.Hub);
            _battlePanel.SetActive(next == GameState.Battle);
            _gameOverPanel.SetActive(next == GameState.GameOver);
            _actionButton.interactable = true;
            _mode = CommandMode.None;

            switch (next)
            {
                case GameState.Hub: OnEnterHub(); break;
                case GameState.Battle: OnEnterBattle(); break;
                case GameState.GameOver: OnEnterGameOver(); break;
            }
        }

        // ============ 허브 ============

        private void OnEnterHub()
        {
            // 보유 영웅 전멸 → 신규 세이브 + 신규 영웅 (00 L13 #4 부활금지 · L12 #3 교첵불가)
            if (Permadeath.IsRunOver(_data)) StartNewRun();
            Party.Sanitize(_data);
            EstateSystem.AdvanceTime(_data, DateTime.UtcNow);
            RefreshHub();
        }

        private void RefreshHub()
        {
            int floor = _data.currentFloor;
            bool gatekeeper = WaveBuilder.IsGatekeeperFloor(floor);
            int cost = ActionPoints.EntryCost(gatekeeper);
            int partyCount = Party.Members(_data).Count;
            bool apOk = ActionPoints.CanEnter(_data, gatekeeper);
            string gkTag = gatekeeper ? " (게이트키퍼)" : "";
            if (SelectedHero() == null && _data.roster.Count > 0) _selectedHeroId = _data.roster[0].id;
            var owned = OwnedLineageCounts();
            int partyCp = HeroPower.PartyCp(_data, owned);
            int recommendedCp = RecommendedPower.ForFloor(DataLoader.LoadMonsters().monsters, floor, GameRules.EnemiesPerWave);

            _title.text = "허브 (성)";
            _statusLine.text = $"보유 영웅 {_data.roster.Count}명 · 출격 {partyCount}/{Party.MaxSize}  |  현재층 {floor}{gkTag}\n" +
                               $"파티 {HeroPower.Format(partyCp)}  ·  {floor}층 권장 CP {HeroPower.N(recommendedCp)} (입장 제한 없음)\n" +
                               $"AP {_data.ap}/{GameRules.MaxAp}  ·  골드 {_data.gold}  ·  영혼석(하) {_data.soulStones}  ·  경험치 {_data.expPool}\n" +
                               $"영지: 인구 {_data.estate.population}/{EstateSystem.MaxPopulation(_data)} · 식량 {_data.estate.food} · 민심 {_data.estate.morale} · 주택 {_data.estate.housingCount}동\n" +
                               $"재료: 약초 {_data.estate.herb} · 목재 {_data.estate.wood} · 광석 {_data.estate.ore} · 채집대 {EstateSystem.MaxGatheringTeams(_data)}팀\n" +
                               $"농사: 경작지 {_data.estate.farmPlots.Count}/{EstateSystem.MaxFarmPlots(_data)} · 작물 {(EstateSystem.CurrentSeason(DateTime.UtcNow)?.id ?? "-")}\n" +
                               $"칙령: {FormatActiveEdicts(_data.estate.activeEdicts)} (슬롯 {EstateSystem.MaxEdictSlots(_data)})\n" +
                               $"통계: 도전 {_data.runsStarted}회 · 패배 {_data.runsLost}회 · 추모 {_data.memorial.Count}명";
             _hpBar.text = ResonanceSummary() + "\n\n" + FacilitySummary(_data);

            int pages = Mathf.Max(1, (_data.roster.Count + RosterPageSize - 1) / RosterPageSize);
            _rosterPage = Mathf.Clamp(_rosterPage, 0, pages - 1);
            for (int i = 0; i < RosterPageSize; i++)
            {
                int idx = _rosterPage * RosterPageSize + i;
                bool has = idx < _data.roster.Count;
                _rosterButtons[i].gameObject.SetActive(has);
                if (!has) continue;
                var h = _data.roster[idx];
                bool inParty = Party.Contains(_data, h.id);
                bool selected = h.id == _selectedHeroId;
                string tag = inParty ? "[출격]" : "[보유]";
                string marker = selected ? "▶ " : "";
                int cp = HeroPower.Compute(_data, h, owned).Cp;
                _rosterLabels[i].text = $"{marker}{tag} ★{h.rank} {h.name} ({RaceName(h.raceId)}) Lv{h.level} · CP {HeroPower.N(cp)}";
                _rosterButtons[i].GetComponent<Image>().color = selected
                    ? new Color(0.45f, 0.38f, 0.18f, 0.95f)
                    : inParty ? new Color(0.22f, 0.42f, 0.3f, 0.95f) : new Color(0.2f, 0.2f, 0.28f, 0.95f);
                string id = h.id;
                _rosterButtons[i].onClick.RemoveAllListeners();
                _rosterButtons[i].onClick.AddListener(() => OnRosterClicked(id));
            }
            _prevPageButton.interactable = _rosterPage > 0;
            _nextPageButton.interactable = _rosterPage < pages - 1;

            _summonLabel.text = SummonSystem.IsNextFree(_data)
                ? $"소환 (무료 {SummonRules.FreeSummons - _data.freeSummonsUsed}/{SummonRules.FreeSummons})"
                : $"소환 (영혼석(하) {SummonRules.StoneCost})";
            _summonButton.interactable = SummonSystem.CanSummon(_data);

            bool canEnter = apOk && partyCount >= Party.MinSize;
            if (!apOk) _actionButtonLabel.text = $"AP 부족 ({_data.ap}/{cost})";
            else if (partyCount < Party.MinSize) _actionButtonLabel.text = "출격 영웅을 편성하세요";
            else _actionButtonLabel.text = $"탑 {floor}층 진입 (AP -{cost})";
            _actionButton.interactable = canEnter;
            _actionButton.onClick.RemoveAllListeners();
            _actionButton.onClick.AddListener(() => EnterState(GameState.Battle));

            RefreshDetail(owned);
        }

        private void OnRosterClicked(string heroId)
        {
            _selectedHeroId = heroId;
            RefreshHub();
        }

        private HeroRecord SelectedHero() => _data.roster.Find(h => h.id == _selectedHeroId);

        // ---- 영웅 상세: CP 분해 · 성격 · 상태(수동) · 장비 · ★7 ----
        private void RefreshDetail(Dictionary<string, int> owned)
        {
            var h = SelectedHero();
            _detailTitle.transform.parent.gameObject.SetActive(h != null);
            if (h == null) return;

            var cp = HeroPower.Compute(_data, h, owned);
            _detailTitle.text = $"★{h.rank} {h.name} ({RaceName(h.raceId)}) Lv{h.level}  ·  성격 {Personality.DisplayName(h.personality)}  ·  SAN {h.sanity} ({StateCorrection.SanityBand(h.sanity)})";
            _detailCp.text = $"{HeroPower.Format(cp.Cp)}   = (G {cp.G:0} + E {cp.E:0} + K {cp.K:0}) × P {cp.P:0.00} × C {cp.C:0.00} × R {cp.R:0.00}";
            _detailPartyLabel.text = Party.Contains(_data, h.id) ? "출격 해제" : "출격 편성";
            _detailTranscendButton.interactable = Transcendence.CanTranscend(h);
            _detailTranscendLabel.text = Transcendence.IsEligibleRank(h)
                ? $"★7 초월진화 — {Transcendence.DisabledReason}"
                : "★7 초월진화 (★6 전용 · 미정C)";
            _moraleLabel.text = $"사기 {StateCorrection.MoraleName(h.morale)}";
            _stressLabel.text = $"스트레스 {StateCorrection.StressName(h.stress)}";

            var eq = DataLoader.LoadEquipment();
            for (int i = 0; i < SlotKeys.Length; i++)
            {
                var item = EquipmentSystem.EquippedInSlot(_data, eq, h.id, SlotKeys[i]);
                var entry = item != null ? EquipmentSystem.Find(eq, item.equipId) : null;
                int free = EquipmentSystem.FreeItemsForSlot(_data, eq, SlotKeys[i]).Count;
                _slotLabels[i].text = entry != null
                    ? $"{SlotNames[i]}: {entry.name} +{item.enhance}  (보관 {free})"
                    : $"{SlotNames[i]}: 없음  (보관 {free})";
                _slotSwapButtons[i].interactable = free > 0 || item != null;
                bool canEnhance = item != null && item.enhance < eq.meta.enhanceMax;
                if (item == null) _slotEnhanceLabels[i].text = "강화";
                else if (!canEnhance) _slotEnhanceLabels[i].text = "강화 MAX";
                else _slotEnhanceLabels[i].text = $"강화 {EquipmentSystem.EnhanceCost(eq, item)}G";
                _slotEnhanceButtons[i].interactable = canEnhance && _data.gold >= EquipmentSystem.EnhanceCost(eq, item);
            }
            foreach (var kv in _shopButtons) kv.Key.interactable = _data.gold >= EquipmentSystem.ShopPrice(eq, kv.Value);
        }

        private void OnPartyToggleClicked()
        {
            var h = SelectedHero();
            if (h == null) return;
            if (!Party.Toggle(_data, h.id)) AppendLog($"출격은 최대 {Party.MaxSize}명 (00 #3)");
            _save.Save(_data);
            RefreshHub();
        }

        private void OnPersonalityClicked()
        {
            var h = SelectedHero();
            if (h == null) return;
            h.personality = Personality.Next(h.personality);
            _save.Save(_data);
            RefreshHub();
        }

        private void OnMoraleDelta(int delta)
        {
            var h = SelectedHero();
            if (h == null) return;
            h.morale = StateCorrection.ClampMorale(h.morale + delta);
            _save.Save(_data);
            RefreshHub();
        }

        private void OnStressDelta(int delta)
        {
            var h = SelectedHero();
            if (h == null) return;
            h.stress = StateCorrection.ClampStress(h.stress + delta);
            _save.Save(_data);
            RefreshHub();
        }

        // 보관함의 같은 슬롯 장비를 순서대로 돌려 끼우고, 끝까지 가면 해제
        private void OnSlotSwap(int slot)
        {
            var h = SelectedHero();
            if (h == null) return;
            var eq = DataLoader.LoadEquipment();
            var current = EquipmentSystem.EquippedInSlot(_data, eq, h.id, SlotKeys[slot]);
            var free = EquipmentSystem.FreeItemsForSlot(_data, eq, SlotKeys[slot]);
            int curIdx = current != null ? _data.inventory.IndexOf(current) : -1;
            EquipmentItem next = null;
            foreach (var it in free)
            {
                if (_data.inventory.IndexOf(it) > curIdx)
                {
                    next = it;
                    break;
                }
            }
            if (next != null)
            {
                EquipmentSystem.Equip(_data, eq, next.uid, h.id);
                AppendLog($"장착: {h.name} ← {EquipmentSystem.Find(eq, next.equipId)?.name} +{next.enhance}");
            }
            else if (current != null)
            {
                EquipmentSystem.Unequip(current);
                AppendLog($"해제: {h.name} {SlotNames[slot]}");
            }
            _save.Save(_data);
            RefreshHub();
        }

        private void OnSlotEnhance(int slot)
        {
            var h = SelectedHero();
            if (h == null) return;
            var eq = DataLoader.LoadEquipment();
            var item = EquipmentSystem.EquippedInSlot(_data, eq, h.id, SlotKeys[slot]);
            if (item == null) return;
            int cost = EquipmentSystem.EnhanceCost(eq, item);
            if (EquipmentSystem.TryEnhance(_data, eq, item))
                AppendLog($"강화: {EquipmentSystem.Find(eq, item.equipId)?.name} +{item.enhance} (골드 -{cost})");
            else
                AppendLog($"강화 불가: 골드 {_data.gold}/{cost} 또는 상한");
            _save.Save(_data);
            RefreshHub();
        }

        private void OnShopBuy(EquipmentEntry entry)
        {
            var eq = DataLoader.LoadEquipment();
            int price = EquipmentSystem.ShopPrice(eq, entry);
            var item = EquipmentSystem.Buy(_data, eq, entry.id);
            if (item == null)
            {
                AppendLog($"골드 부족: {_data.gold}/{price}");
                RefreshHub();
                return;
            }
            string equipped = "";
            var h = SelectedHero();
            if (h != null && EquipmentSystem.EquippedInSlot(_data, eq, h.id, entry.slot) == null)
            {
                EquipmentSystem.Equip(_data, eq, item.uid, h.id);
                equipped = $" → {h.name} 장착";
            }
            AppendLog($"구매: {entry.name} (골드 -{price}){equipped}");
            _save.Save(_data);
            RefreshHub();
        }

        private void OnSummonClicked()
        {
            bool free = SummonSystem.IsNextFree(_data);
            var h = SummonSystem.TrySummon(_data, DataLoader.LoadRaces().races, _rng);
            if (h == null)
            {
                AppendLog($"영혼석 부족: {_data.soulStones}/{SummonRules.StoneCost}");
                RefreshHub();
                return;
            }
            bool joined = _data.party.Count < Party.MaxSize && Party.Toggle(_data, h.id);
            string costText = free ? "무료" : $"영혼석 -{SummonRules.StoneCost}";
            string joinText = joined ? " · 출격 편성" : "";
            AppendLog($"소환: ★{h.rank} {h.name} ({RaceName(h.raceId)}) — {costText}{joinText}");
            _save.Save(_data);
            RefreshHub();
        }

        private void StartNewRun()
        {
            var hero = HeroFactory.CreateRandom(DataLoader.LoadRaces().races, _rng);
            _data = Permadeath.StartNewRun(_data, hero);
            AppendLog($"신규 세이브 + 신규 영웅: {hero.name} ({RaceName(hero.raceId)}) ★{hero.rank} Lv{hero.level}");
            _save.Save(_data);
        }

        private Dictionary<string, int> OwnedLineageCounts()
        {
            var raceIds = new List<string>();
            foreach (var h in _data.roster) raceIds.Add(h.raceId);
            return Resonance.CountByLineage(raceIds, id => DataLoader.GetRace(id)?.lineage);
        }

        private string ResonanceSummary()
        {
            var counts = OwnedLineageCounts();
            var sb = new System.Text.StringBuilder("<b>공명 (보유 기준 · 출격 멤버에 적용)</b>\n");
            foreach (var kv in counts)
            {
                int tier = Resonance.Tier(counts, kv.Key);
                string effect = tier >= 3 ? " → tier3 HP/ATK +5%" : "";
                string later = tier >= 5 ? $" (tier{tier} 효과는 후속)" : "";
                sb.AppendLine($"{kv.Key} {kv.Value}명{effect}{later}");
            }
            return sb.ToString();
        }

        // ============ 전투 ============

        private void OnEnterBattle()
        {
            var members = Party.Members(_data);
            int floor = _data.currentFloor;
            bool gatekeeper = WaveBuilder.IsGatekeeperFloor(floor);
            int cost = ActionPoints.EntryCost(gatekeeper);
            if (members.Count < Party.MinSize)
            {
                AppendLog("출격 영웅 없음 — 허브에서 편성");
                EnterState(GameState.Hub);
                return;
            }
            if (!ActionPoints.TrySpendForEntry(_data, gatekeeper))
            {
                AppendLog($"AP 부족: {_data.ap}/{cost} — 진입 불가");
                EnterState(GameState.Hub);
                return;
            }
            _runFloor = floor;
            _data.runsStarted++;
            // 진입 즉시 저장 — 전투 도중 종료로 AP 차감이 되돌아가지 않게.
            _save.Save(_data);

            var arena = ArenaLayout.ForFloor(floor);
            _battle = new BattleSystem(floor, arena);
            _battle.OnLog += AppendLog;
            _battle.OnHit += (a, t, dmg) =>
            {
                if (!t.IsAlive && a.IsHero) ActionPoints.OnKill(_data); // 00 L14: 처치 +1, MAX 초과분 소멸
            };
            _battle.OnEnded += HandleBattleEnded;
            _unitByVisual.Clear();

            string mode = gatekeeper ? "게이트키퍼" : (_battle.Gauge.Enabled ? "전술 개입" : "자동 전투");
            _title.text = $"탑 {floor}층 — {mode}";
            AppendLog($"{floor}층 진입: AP -{cost} → {_data.ap}/{GameRules.MaxAp}");

            SpawnTerrainVisuals(arena);

            var baseStats = DataLoader.GetHeroBaseStats();
            var equipment = DataLoader.LoadEquipment();
            for (int i = 0; i < members.Count; i++)
            {
                var h = members[i];
                var u = _battle.AddHero(h.id, h.name, DataLoader.GetRace(h.raceId), baseStats, h.rank, h.level,
                    EquipmentSystem.EquippedStats(_data, equipment, h.id));
                u.X = -3.5f - (i % 2) * 1.2f;
                u.Z = (i - (members.Count - 1) / 2f) * 1.4f;
                SpawnUnitVisual(u, new Color(0.4f, 0.7f, 1f), 1f);
            }
            var owned = OwnedLineageCounts();
            _battle.SetOwnedLineageCounts(owned);
            int recommendedCp = RecommendedPower.ForFloor(DataLoader.LoadMonsters().monsters, floor, GameRules.EnemiesPerWave);
            AppendLog($"파티 {HeroPower.Format(HeroPower.PartyCp(_data, owned))} · 권장 CP {HeroPower.N(recommendedCp)}");

            var wave = WaveBuilder.BuildWave(DataLoader.LoadMonsters().monsters, floor, GameRules.EnemiesPerWave, _rng);
            if (wave.Count == 0) AppendLog($"{floor}층 편성 몬스터 없음 (monsters.json spawn)");
            for (int i = 0; i < wave.Count; i++)
            {
                var m = wave[i];
                if (gatekeeper)
                {
                    var s = BossScaling.Apply(m, floor);
                    var boss = _battle.AddEnemy(m.name, s);
                    boss.X = 4f;
                    boss.Z = 0f;
                    AppendLog($"게이트키퍼: {m.name} (스케일 ×{BossScaling.Factor(m, floor):0.###} → HP {s.Hp} · ATK {s.Atk})");
                    SpawnUnitVisual(boss, new Color(0.85f, 0.3f, 0.35f), 1.5f);
                }
                else
                {
                    var u = _battle.AddEnemyFromMonster(m);
                    u.X = 3f + (i % 2) * 1.2f;
                    u.Z = (i - (wave.Count - 1) / 2f) * 1.2f;
                    bool slimy = m.id.Contains("slime") || m.id.Contains("ooze");
                    var col = slimy ? new Color(0.5f, 0.9f, 0.4f) : new Color(0.9f, 0.9f, 0.85f);
                    SpawnUnitVisual(u, col, 1f);
                }
            }

            AppendLog($"전투 시작: 아군 {_battle.Heroes.Count} vs 적 {_battle.Enemies.Count} ({floor}층)");
            _actionButtonLabel.text = "포기(패배)";
            _actionButton.onClick.RemoveAllListeners();
            _actionButton.onClick.AddListener(() => HandleBattleEnded(BattleOutcome.Defeat));

            SetMode(CommandMode.None);
            UpdateBattleHud();
        }

        private void OnMoveButton()
        {
            if (_battle == null || !_battle.Gauge.CanSpend(TacticalCommands.MoveCost))
            {
                AppendLog($"게이지 부족: 이동 {TacticalCommands.MoveCost:0} 필요");
                return;
            }
            SetMode(CommandMode.MovePickHero);
        }

        private void OnFocusButton()
        {
            if (_battle == null || !_battle.Gauge.CanSpend(TacticalCommands.FocusCost))
            {
                AppendLog($"게이지 부족: 집중 {TacticalCommands.FocusCost:0} 필요");
                return;
            }
            SetMode(CommandMode.FocusPickEnemy);
        }

        private void SetMode(CommandMode mode)
        {
            _mode = mode;
            if (_battle == null || !_battle.Gauge.Enabled)
            {
                _commandHint.text = "1~3층 완전자동";
                return;
            }
            switch (mode)
            {
                case CommandMode.MovePickHero: _commandHint.text = "이동할 영웅 클릭 (우클릭 취소)"; break;
                case CommandMode.MovePickPoint: _commandHint.text = "목표 지점 클릭 (우클릭 취소)"; break;
                case CommandMode.FocusPickEnemy: _commandHint.text = "집중 공격할 적 클릭 (우클릭 취소)"; break;
                default: _commandHint.text = "명령: 이동 · 집중"; break;
            }
        }

        // 신 Input System 전용 (StandaloneInputModule 금지)
        private void HandleTacticalInput()
        {
            if (!_battle.Gauge.Enabled) return;
            var mouse = Mouse.current;
            if (mouse == null) return;

            bool cancel = mouse.rightButton.wasPressedThisFrame ||
                          (Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame);
            if (cancel)
            {
                if (_mode != CommandMode.None) SetMode(CommandMode.None);
                return;
            }
            if (_mode == CommandMode.None || !mouse.leftButton.wasPressedThisFrame) return;
            if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject()) return;

            var cam = Camera.main;
            if (cam == null) return;
            var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
            if (!Physics.Raycast(ray, out var hit, 500f)) return;
            _unitByVisual.TryGetValue(hit.collider.gameObject, out var unit);

            switch (_mode)
            {
                case CommandMode.MovePickHero:
                    if (unit != null && unit.IsHero && unit.IsAlive)
                    {
                        _moveHero = unit;
                        SetMode(CommandMode.MovePickPoint);
                    }
                    break;
                case CommandMode.MovePickPoint:
                    if (!_battle.CommandMove(_moveHero, hit.point.x, hit.point.z)) AppendLog("이동 명령 실패 (게이지/대상)");
                    SetMode(CommandMode.None);
                    break;
                case CommandMode.FocusPickEnemy:
                    if (unit != null && !unit.IsHero && unit.IsAlive)
                    {
                        if (!_battle.CommandFocus(unit)) AppendLog("집중 명령 실패 (게이지)");
                        SetMode(CommandMode.None);
                    }
                    break;
            }
        }

        private void HandleBattleEnded(BattleOutcome outcome)
        {
            if (_state != GameState.Battle) return;
            _battle.Outcome = outcome; // 이중 호출 방지
            _lastOutcome = outcome;
            AppendLog(outcome == BattleOutcome.Victory ? "승리!" : "패배 — 파티 전멸.");
            if (outcome == BattleOutcome.Defeat) _data.runsLost++;

            // 보상 정산 (퇴장지급) — 진입층 기준·승패 무관. 게이트층이면 잭팟 (00 L31 #19)
            _lastReward = RunRewards.Settle(_data, _runFloor);
            string jackpotText = _lastReward.Jackpot > 0 ? $" + 잭팟 {_lastReward.Jackpot}" : "";
            AppendLog($"보상: 골드 +{_lastReward.Gold} · 영혼석(하) +{_lastReward.SoulStones}{jackpotText} · 경험치 +{_lastReward.Exp}");

            // 영구사망 — 쓰러진 영웅 + 패배(포기 포함) 시 남은 영웅 전원. 부활 없음.
            _lastDeaths.Clear();
            var survivors = new List<string>();
            foreach (var u in _battle.Heroes)
            {
                if (u.IsAlive && outcome != BattleOutcome.Defeat)
                {
                    survivors.Add(u.HeroId);
                    continue;
                }
                var rec = _data.roster.Find(h => h.id == u.HeroId);
                if (rec == null) continue;
                string killer = u.IsAlive ? "전투 포기" : (u.KilledBy ?? "알 수 없음");
                var entry = Permadeath.RecordDeath(_data, rec, _runFloor, killer, System.DateTime.UtcNow);
                _lastDeaths.Add(entry);
                AppendLog($"영구사망: {entry.name} — {entry.floor}층 · 상대 {entry.killedBy} · {Permadeath.EquipmentReturnText(entry.returnedEquipment)}");
            }

            // 생존자 Sanity → 병원 요양 (부활 없음)
            if (survivors.Count > 0)
            {
                Hospital.ApplyBattleStress(_data, survivors, _lastDeaths.Count);
                AppendLog($"생존자 {survivors.Count}명 Sanity -{Hospital.StressFor(_lastDeaths.Count)}");
            }
            _lastRested.Clear();
            _lastRested.AddRange(Hospital.Rest(_data));
            foreach (var r in _lastRested) AppendLog($"병원 요양: {r.name} SAN +{Hospital.RestRecovery} → {r.sanity}");

            // 층 진행 — 승리 시 다음 층 (03 P2-1: 1~20층)
            _lastFloorAdvanced = false;
            if (outcome == BattleOutcome.Victory && _data.currentFloor == _runFloor && _runFloor < GameRules.MaxFloor)
            {
                _data.currentFloor = _runFloor + 1;
                _lastFloorAdvanced = true;
                AppendLog($"{_runFloor}층 돌파 → 다음 {_data.currentFloor}층");
            }

            // 영지: 층 클리어 시 주민 세금/식량 소비 (04 §3.4 · §3.11)
            EstateSystem.OnFloorCleared(_data, _runFloor);

            // 세이브 (원자성)
            _save.Save(_data);
            AppendLog($"세이브 완료: {_save.FilePath}");

            EnterState(GameState.GameOver);
        }

        private void OnEnterGameOver()
        {
            _title.text = "결산";
            string result = _lastOutcome == BattleOutcome.Victory ? "승리" : "패배";
            string advance = _lastFloorAdvanced ? $" → 다음 {_data.currentFloor}층" : "";
            string jackpotNote = _lastReward.Jackpot > 0 ? $" · 잭팟 +{_lastReward.Jackpot}" : "";
            _statusLine.text = $"{_runFloor}층 {result}{advance}  ·  보상: 골드 +{_lastReward.Gold} · 영혼석(하) +{_lastReward.SoulStones}{jackpotNote} · 경험치 +{_lastReward.Exp}\n" +
                               $"보유: 골드 {_data.gold} · 영혼석(하) {_data.soulStones} · 경험치 {_data.expPool} · AP {_data.ap}/{GameRules.MaxAp}\n" +
                               $"영지: 인구 {_data.estate.population}/{EstateSystem.MaxPopulation(_data)} · 식량 {_data.estate.food} · 민심 {_data.estate.morale} · 주택 {_data.estate.housingCount}동\n" +
                               $"재료: 약초 {_data.estate.herb} · 목재 {_data.estate.wood} · 광석 {_data.estate.ore} · 채집대 {EstateSystem.MaxGatheringTeams(_data)}팀\n" +
                               $"농사: 경작지 {_data.estate.farmPlots.Count}/{EstateSystem.MaxFarmPlots(_data)} · 작물 {(EstateSystem.CurrentSeason(DateTime.UtcNow)?.id ?? "-")}\n" +
                               $"칙령: {FormatActiveEdicts(_data.estate.activeEdicts)} (슬롯 {EstateSystem.MaxEdictSlots(_data)})\n" +
                               $"통계: 도전 {_data.runsStarted}회 · 패배 {_data.runsLost}회  |  세이브: {_save.FilePath}";

            var sb = new System.Text.StringBuilder();
            sb.AppendLine("<b>사망 기록</b>");
            if (_lastDeaths.Count == 0) sb.AppendLine("이번 전투 사망자 없음");
            foreach (var d in _lastDeaths)
                sb.AppendLine($"{d.name} ({RaceName(d.raceId)} ★{d.rank}) — {d.floor}층 · 상대 {d.killedBy} · {FormatDate(d.date)} · {Permadeath.EquipmentReturnText(d.returnedEquipment)}");
            if (_lastRested.Count > 0)
            {
                sb.AppendLine("<b>병원 요양</b>");
                foreach (var r in _lastRested) sb.AppendLine($"{r.name} SAN {r.sanity}");
            }
            if (Permadeath.IsRunOver(_data)) sb.AppendLine("보유 영웅 전멸 — 다음 진입은 신규 세이브 + 신규 영웅으로 시작합니다.");
            _hpBar.text = sb.ToString();

            _actionButtonLabel.text = "리로드 (허브 복귀)";
            _actionButton.onClick.RemoveAllListeners();
            _actionButton.onClick.AddListener(() =>
            {
                ClearBattleVisuals();
                bool corrupt;
                _data = _save.Load(out corrupt);
                if (corrupt) AppendLog("리로드 중 손상 감지");
                AppendLog($"리로드 완료: 도전 {_data.runsStarted} · 패배 {_data.runsLost} · 추모 {_data.memorial.Count}");
                EnterState(GameState.Hub);
            });
        }

        private static string RaceName(string raceId) => DataLoader.GetRace(raceId)?.name ?? raceId;

        private static string FormatDate(string iso)
        {
            return System.DateTime.TryParse(iso, null, System.Globalization.DateTimeStyles.RoundtripKind, out var dt)
                ? dt.ToLocalTime().ToString("yyyy-MM-dd HH:mm")
                : iso;
        }

        private static string FormatActiveEdicts(List<string> ids)
        {
            if (ids == null || ids.Count == 0) return "없음";
            var sb = new System.Text.StringBuilder();
            bool first = true;
            foreach (var id in ids)
            {
                if (string.IsNullOrEmpty(id)) continue;
                if (!first) sb.Append(" · ");
                first = false;
                var ed = EstateSystem.GetEdictData(id);
                sb.Append(ed?.name_ko ?? id);
            }
            return sb.Length > 0 ? sb.ToString() : "없음";
        }

        private static string FacilitySummary(SaveData d)
        {
            var sb = new System.Text.StringBuilder("<b>시설</b>\n");
            foreach (var s in d.estate.facilities)
            {
                var data = EstateSystem.GetFacilityData(s.id);
                string name = data?.name_ko ?? s.id;
                string status;
                if (s.constructionRemainingFloors > 0)
                    status = $"공사 중 ({s.constructionRemainingFloors}층)";
                else if (!s.built)
                    status = "미건설";
                else
                    status = $"Lv{s.level}";
                string op = "";
                if (s.built && data != null && data.operate_required)
                    op = string.IsNullOrEmpty(s.operatorHeroId) ? " [미배치]" : " [가동]";
                sb.AppendLine($"{name}: {status}{op}");
            }
            return sb.ToString();
        }

        // ============ UI 구성 ============

        private void BuildUI()
        {
            var canvasGo = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            _canvas = canvasGo.GetComponent<Canvas>();
            _canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;

            // EventSystem (Input System 패키지 전용 설정이므로 신 Input 모듈 사용)
            if (FindAnyObjectByType<EventSystem>() == null)
            {
                new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
            }

            _hubPanel = MakePanel("HubPanel");
            _battlePanel = MakePanel("BattlePanel");
            _gameOverPanel = MakePanel("GameOverPanel");

            _title = MakeText(_canvas.transform, "Title", new Vector2(0f, 1f), new Vector2(1f, 1f),
                new Vector2(20, -60), new Vector2(-660, -10), 42, TextAnchor.MiddleLeft);
            _title.text = "소울 커맨더";

            _statusLine = MakeText(_canvas.transform, "Status", new Vector2(0f, 1f), new Vector2(1f, 1f),
                new Vector2(20, -200), new Vector2(-660, -70), 22, TextAnchor.UpperLeft);

            _log = MakeText(_canvas.transform, "Log", new Vector2(0f, 0f), new Vector2(1f, 0f),
                new Vector2(20, 20), new Vector2(-660, 200), 18, TextAnchor.LowerLeft);
            _log.horizontalOverflow = HorizontalWrapMode.Wrap;

            _hpBar = MakeText(_canvas.transform, "HpBar", new Vector2(0f, 1f), new Vector2(1f, 1f),
                new Vector2(20, -300), new Vector2(-660, -210), 20, TextAnchor.UpperLeft);
            _hpBar.verticalOverflow = VerticalWrapMode.Overflow;

            // Action button (우하단 — 허브 상세 패널과 겹치지 않게)
            _actionButton = MakeButton(_canvas.transform, "ActionButton",
                new Vector2(1f, 0f), new Vector2(1f, 0f),
                new Vector2(-640, 120), new Vector2(-20, 200), out _actionButtonLabel);

            // ---- 전투 패널: 전술 명령 (4층+) + 전술 게이지 ----
            _moveButton = MakeButton(_battlePanel.transform, "MoveButton",
                new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
                new Vector2(-420, 210), new Vector2(-190, 280), out var moveLabel);
            moveLabel.text = $"이동 ({TacticalCommands.MoveCost:0})";
            _moveButton.onClick.AddListener(OnMoveButton);

            _focusButton = MakeButton(_battlePanel.transform, "FocusButton",
                new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
                new Vector2(190, 210), new Vector2(420, 280), out var focusLabel);
            focusLabel.text = $"집중 ({TacticalCommands.FocusCost:0})";
            _focusButton.onClick.AddListener(OnFocusButton);

            _commandHint = MakeText(_battlePanel.transform, "CommandHint",
                new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
                new Vector2(-180, 210), new Vector2(180, 280), 20, TextAnchor.MiddleCenter);

            var sliderGo = new GameObject("TacticalGauge", typeof(RectTransform), typeof(Slider));
            sliderGo.transform.SetParent(_battlePanel.transform, false);
            var sRT = (RectTransform)sliderGo.transform;
            sRT.anchorMin = new Vector2(1f, 1f); sRT.anchorMax = new Vector2(1f, 1f);
            sRT.pivot = new Vector2(1f, 1f);
            sRT.anchoredPosition = new Vector2(-20, -20);
            sRT.sizeDelta = new Vector2(400, 30);
            _gaugeSlider = sliderGo.GetComponent<Slider>();
            _gaugeSlider.minValue = 0f; _gaugeSlider.maxValue = TacticalGauge.Max; _gaugeSlider.value = TacticalGauge.StartValue;
            _gaugeSlider.interactable = false;
            var fillArea = new GameObject("Fill", typeof(RectTransform), typeof(Image));
            fillArea.transform.SetParent(sliderGo.transform, false);
            var fillRT = (RectTransform)fillArea.transform;
            fillRT.anchorMin = new Vector2(0, 0); fillRT.anchorMax = new Vector2(1, 1);
            fillRT.offsetMin = Vector2.zero; fillRT.offsetMax = Vector2.zero;
            fillArea.GetComponent<Image>().color = new Color(0.4f, 0.3f, 0.9f, 0.35f);
            var fill2 = new GameObject("FillVal", typeof(RectTransform), typeof(Image));
            fill2.transform.SetParent(fillArea.transform, false);
            var fill2RT = (RectTransform)fill2.transform;
            fill2RT.anchorMin = new Vector2(0, 0); fill2RT.anchorMax = new Vector2(1, 1);
            fill2RT.offsetMin = Vector2.zero; fill2RT.offsetMax = Vector2.zero;
            fill2.GetComponent<Image>().color = new Color(0.7f, 0.5f, 1f, 1f);
            _gaugeSlider.fillRect = fill2RT;

            _gaugeLabel = MakeText(_battlePanel.transform, "GaugeLabel",
                new Vector2(1f, 1f), new Vector2(1f, 1f),
                new Vector2(-420, -80), new Vector2(-20, -55), 18, TextAnchor.MiddleRight);

            // ---- 허브 패널: 보유 영웅/출격 편성 + 소환 ----
            var rosterTitle = MakeText(_hubPanel.transform, "RosterTitle", new Vector2(1f, 1f), new Vector2(1f, 1f),
                new Vector2(-640, -110), new Vector2(-20, -70), 22, TextAnchor.MiddleLeft);
            rosterTitle.text = $"보유 영웅 — 클릭해 상세 (출격 최대 {Party.MaxSize}명)";

            _rosterButtons = new Button[RosterPageSize];
            _rosterLabels = new Text[RosterPageSize];
            for (int i = 0; i < RosterPageSize; i++)
            {
                float top = -120 - i * 62;
                _rosterButtons[i] = MakeButton(_hubPanel.transform, $"Roster{i}", new Vector2(1f, 1f), new Vector2(1f, 1f),
                    new Vector2(-640, top - 56), new Vector2(-20, top), out _rosterLabels[i]);
                _rosterLabels[i].fontSize = 20;
                _rosterLabels[i].alignment = TextAnchor.MiddleLeft;
                var lrt = (RectTransform)_rosterLabels[i].transform;
                lrt.offsetMin = new Vector2(14, 0);
                lrt.offsetMax = new Vector2(-14, 0);
            }
            float pageTop = -120 - RosterPageSize * 62;
            _prevPageButton = MakeButton(_hubPanel.transform, "PrevPage", new Vector2(1f, 1f), new Vector2(1f, 1f),
                new Vector2(-640, pageTop - 50), new Vector2(-340, pageTop), out var prevLabel);
            prevLabel.text = "◀ 이전";
            prevLabel.fontSize = 20;
            _prevPageButton.onClick.AddListener(() => { _rosterPage--; RefreshHub(); });
            _nextPageButton = MakeButton(_hubPanel.transform, "NextPage", new Vector2(1f, 1f), new Vector2(1f, 1f),
                new Vector2(-320, pageTop - 50), new Vector2(-20, pageTop), out var nextLabel);
            nextLabel.text = "다음 ▶";
            nextLabel.fontSize = 20;
            _nextPageButton.onClick.AddListener(() => { _rosterPage++; RefreshHub(); });

            _summonButton = MakeButton(_hubPanel.transform, "SummonButton", new Vector2(1f, 1f), new Vector2(1f, 1f),
                new Vector2(-640, pageTop - 124), new Vector2(-20, pageTop - 64), out _summonLabel);
            _summonLabel.fontSize = 24;
            _summonButton.onClick.AddListener(OnSummonClicked);

            BuildHeroDetail();

            // 바닥 플레인 (전장 지면) — 20×15, 아레나 ±9 × ±6.5 를 덮는다
            _ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            _ground.name = "Floor";
            _ground.transform.position = Vector3.zero;
            _ground.transform.localScale = new Vector3(2f, 1f, 1.5f);
            var mr = _ground.GetComponent<MeshRenderer>();
            mr.material = NewMaterial(new Color(0.15f, 0.15f, 0.17f));
        }

        // 허브 좌하단: 영웅 상세 + 장비 상점 (좌표는 1920×1080 기준, 좌하단 앵커)
        private void BuildHeroDetail()
        {
            var detail = new GameObject("HeroDetail", typeof(RectTransform));
            detail.transform.SetParent(_hubPanel.transform, false);
            var drt = (RectTransform)detail.transform;
            drt.anchorMin = Vector2.zero; drt.anchorMax = Vector2.one;
            drt.offsetMin = Vector2.zero; drt.offsetMax = Vector2.zero;
            var t = detail.transform;

            _detailTitle = MakeText(t, "DetailTitle", Vector2.zero, Vector2.zero, new Vector2(20, 610), new Vector2(1240, 650), 22, TextAnchor.MiddleLeft);
            _detailCp = MakeText(t, "DetailCp", Vector2.zero, Vector2.zero, new Vector2(20, 570), new Vector2(1240, 606), 20, TextAnchor.MiddleLeft);

            SmallButton(t, "PartyToggle", 20, 522, 200, 40, out _detailPartyLabel, OnPartyToggleClicked);
            SmallButton(t, "Personality", 230, 522, 200, 40, out var personalityLabel, OnPersonalityClicked);
            personalityLabel.text = "성격 변경";
            _detailTranscendButton = SmallButton(t, "Transcend", 440, 522, 420, 40, out _detailTranscendLabel, () => AppendLog(Transcendence.DisabledReason));

            // 상태 — 영지 전까지 수동 설정 (01 §5)
            SmallButton(t, "MoraleDown", 20, 474, 44, 40, out var md, () => OnMoraleDelta(-1)); md.text = "−";
            _moraleLabel = MakeText(t, "Morale", Vector2.zero, Vector2.zero, new Vector2(70, 474), new Vector2(230, 514), 20, TextAnchor.MiddleCenter);
            SmallButton(t, "MoraleUp", 236, 474, 44, 40, out var mu, () => OnMoraleDelta(1)); mu.text = "+";
            SmallButton(t, "StressDown", 300, 474, 44, 40, out var sd, () => OnStressDelta(-1)); sd.text = "−";
            _stressLabel = MakeText(t, "Stress", Vector2.zero, Vector2.zero, new Vector2(350, 474), new Vector2(530, 514), 20, TextAnchor.MiddleCenter);
            SmallButton(t, "StressUp", 536, 474, 44, 40, out var su, () => OnStressDelta(1)); su.text = "+";
            var stateNote = MakeText(t, "StateNote", Vector2.zero, Vector2.zero, new Vector2(590, 474), new Vector2(810, 514), 14, TextAnchor.MiddleLeft);
            stateNote.text = "사기·스트레스: 영지 전 수동 설정";

            _slotLabels = new Text[SlotKeys.Length];
            _slotSwapButtons = new Button[SlotKeys.Length];
            _slotEnhanceButtons = new Button[SlotKeys.Length];
            _slotEnhanceLabels = new Text[SlotKeys.Length];
            for (int i = 0; i < SlotKeys.Length; i++)
            {
                int slot = i;
                float y = 426 - i * 46;
                _slotLabels[i] = MakeText(t, $"Slot{i}", Vector2.zero, Vector2.zero, new Vector2(20, y), new Vector2(480, y + 40), 20, TextAnchor.MiddleLeft);
                _slotSwapButtons[i] = SmallButton(t, $"Swap{i}", 490, y, 110, 40, out var swapLabel, () => OnSlotSwap(slot));
                swapLabel.text = "교체";
                _slotEnhanceButtons[i] = SmallButton(t, $"Enhance{i}", 610, y, 190, 40, out _slotEnhanceLabels[i], () => OnSlotEnhance(slot));
            }

            // 상점 — 골드 구매 (슬롯 행 × 등급 열)
            var shopTitle = MakeText(t, "ShopTitle", Vector2.zero, Vector2.zero, new Vector2(820, 474), new Vector2(1240, 514), 18, TextAnchor.MiddleLeft);
            shopTitle.text = "상점 (골드) — 구매 시 빈 슬롯이면 자동 장착";
            var eq = DataLoader.LoadEquipment();
            _shopButtons.Clear();
            foreach (var entry in eq.equipment)
            {
                int row = System.Array.IndexOf(SlotKeys, entry.slot);
                if (row < 0) continue;
                int col = Mathf.Clamp(entry.grade - 1, 0, 2);
                var e = entry;
                var b = SmallButton(t, $"Shop_{entry.id}", 820 + col * 142, 426 - row * 46, 136, 40, out var shopLabel, () => OnShopBuy(e));
                shopLabel.fontSize = 15;
                shopLabel.text = $"{entry.name} {EquipmentSystem.ShopPrice(eq, entry)}";
                _shopButtons.Add(new KeyValuePair<Button, EquipmentEntry>(b, entry));
            }
        }

        private Button SmallButton(Transform parent, string name, float x, float y, float w, float h, out Text label,
                                   UnityEngine.Events.UnityAction onClick)
        {
            var b = MakeButton(parent, name, Vector2.zero, Vector2.zero, new Vector2(x, y), new Vector2(x + w, y + h), out label);
            label.fontSize = 18;
            if (onClick != null) b.onClick.AddListener(onClick);
            return b;
        }

        private GameObject MakePanel(string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(_canvas.transform, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = Vector2.zero; rt.offsetMax = Vector2.zero;
            return go;
        }

        private Text MakeText(Transform parent, string name, Vector2 aMin, Vector2 aMax,
                              Vector2 offMin, Vector2 offMax, int size, TextAnchor anchor)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Text));
            go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = aMin; rt.anchorMax = aMax;
            rt.offsetMin = offMin; rt.offsetMax = offMax;
            var t = go.GetComponent<Text>();
            t.font = _font ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            t.fontSize = size;
            t.alignment = anchor;
            t.color = Color.white;
            t.raycastTarget = false;
            t.text = "";
            return t;
        }

        private Button MakeButton(Transform parent, string name, Vector2 aMin, Vector2 aMax,
                                  Vector2 offMin, Vector2 offMax, out Text label)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = aMin; rt.anchorMax = aMax;
            rt.offsetMin = offMin; rt.offsetMax = offMax;
            go.GetComponent<Image>().color = new Color(0.2f, 0.2f, 0.28f, 0.95f);
            label = MakeText(go.transform, "Label", new Vector2(0, 0), new Vector2(1, 1), Vector2.zero, Vector2.zero, 28, TextAnchor.MiddleCenter);
            return go.GetComponent<Button>();
        }

        private Material NewMaterial(Color color)
        {
            if (_litShader == null) _litShader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var mat = new Material(_litShader);
            mat.color = color;
            return mat;
        }

        private void SpawnUnitVisual(BattleUnit u, Color color, float scale)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            go.name = u.DisplayName;
            go.transform.localScale = new Vector3(0.7f, 0.9f, 0.7f) * scale;
            go.transform.position = new Vector3(u.X, 0.9f * scale, u.Z);
            go.GetComponent<MeshRenderer>().material = NewMaterial(color);

            // 바라보는 방향 표시 (측면/배후 판정 시각화)
            var nose = GameObject.CreatePrimitive(PrimitiveType.Cube);
            nose.name = "Facing";
            Destroy(nose.GetComponent<Collider>());
            nose.transform.SetParent(go.transform, false);
            nose.transform.localPosition = new Vector3(0f, 0.35f, 0.55f);
            nose.transform.localScale = new Vector3(0.3f, 0.15f, 0.35f);
            nose.GetComponent<MeshRenderer>().material = NewMaterial(color * 0.5f);

            u.Visual = go;
            _unitByVisual[go] = u;
        }

        private void SpawnTerrainVisuals(ArenaLayout arena)
        {
            foreach (var zone in arena.Zones)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                go.name = zone.Kind == TerrainKind.HighGround ? "HighGround" : "Cover";
                Destroy(go.GetComponent<Collider>());
                go.transform.position = new Vector3(zone.X, 0.03f, zone.Z);
                go.transform.localScale = new Vector3(zone.Radius * 2f, 0.03f, zone.Radius * 2f);
                var col = zone.Kind == TerrainKind.HighGround ? new Color(0.55f, 0.45f, 0.25f) : new Color(0.3f, 0.42f, 0.55f);
                go.GetComponent<MeshRenderer>().material = NewMaterial(col);
                _terrainVisuals.Add(go);
            }
        }

        private void SyncUnitVisuals()
        {
            foreach (var kv in _unitByVisual)
            {
                var go = kv.Key;
                var u = kv.Value;
                if (go == null) continue;
                if (!u.IsAlive)
                {
                    if (go.activeSelf) go.SetActive(false);
                    continue;
                }
                var p = go.transform.position;
                go.transform.position = new Vector3(u.X, p.y, u.Z);
                var facing = new Vector3(u.FacingX, 0f, u.FacingZ);
                if (facing.sqrMagnitude > 1e-6f) go.transform.rotation = Quaternion.LookRotation(facing);
            }
        }

        private void ClearBattleVisuals()
        {
            foreach (var go in _unitByVisual.Keys) if (go != null) Destroy(go);
            _unitByVisual.Clear();
            foreach (var go in _terrainVisuals) if (go != null) Destroy(go);
            _terrainVisuals.Clear();
            _battle = null;
        }

        private void UpdateBattleHud()
        {
            if (_battle == null) return;
            var arena = _battle.Arena;
            var sb = new System.Text.StringBuilder();
            sb.Append("<b>아군</b>\n");
            foreach (var u in _battle.Heroes)
            {
                string reso = u.ResonanceMul > 1f ? " [공명]" : "";
                string state = u.IsAlive ? $"HP {u.Hp}/{u.MaxHp}" : "사망";
                sb.AppendLine($"{u.DisplayName}  {state}  ATK {u.Atk} MAG {u.Mag} DEF {u.Def} MDEF {u.MDef} ASPD {u.Aspd} CRI {u.Cri} EVA {u.Eva}{TerrainTag(arena, u)}{reso}");
            }
            sb.AppendLine();
            sb.Append("<b>적</b>\n");
            foreach (var u in _battle.Enemies)
            {
                if (!u.IsAlive) continue;
                string focus = u == _battle.FocusTarget ? " [집중]" : "";
                sb.AppendLine($"{u.DisplayName}  HP {u.Hp}/{u.MaxHp}  ATK {u.Atk} DEF {u.Def} MDEF {u.MDef} ASPD {u.Aspd}{TerrainTag(arena, u)}{focus}");
            }
            _hpBar.text = sb.ToString();

            var gauge = _battle.Gauge;
            _gaugeSlider.value = gauge.Value;
            if (gauge.Enabled)
            {
                string focusTime = _battle.FocusRemaining > 0f ? $" · 집중 {_battle.FocusRemaining:0.0}s" : "";
                _gaugeLabel.text = $"전술 게이지 {gauge.Value:0}/{TacticalGauge.Max:0}{focusTime}";
            }
            else
            {
                _gaugeLabel.text = "자동 전투 (1~3층 — 전술개입 4층+)";
            }
            _moveButton.interactable = gauge.CanSpend(TacticalCommands.MoveCost);
            _focusButton.interactable = gauge.CanSpend(TacticalCommands.FocusCost);
        }

        private static string TerrainTag(ArenaLayout arena, BattleUnit u)
        {
            if (arena == null) return "";
            if (arena.IsIn(TerrainKind.HighGround, u.X, u.Z)) return " [고지대]";
            if (arena.IsIn(TerrainKind.Cover, u.X, u.Z)) return " [커버]";
            return "";
        }

        private void AppendLog(string line)
        {
            _logLines.Enqueue(line);
            while (_logLines.Count > LogMaxLines) _logLines.Dequeue();
            _data.log.Add(line);
            if (_data.log.Count > 200) _data.log.RemoveAt(0);
            if (_log != null) _log.text = string.Join("\n", _logLines);
            Debug.Log($"[SoulCommander] {line}");
        }
    }
}
