# PORTING_MAP — Godot 구현 참고 인덱스 (전체 201개 .gd, 태그 v0.1-godot-final 기준)

> ⚠️ **v8.0 결정(2026-09-14): Unity 신규 리부트 — 이 문서는 "참고 인덱스"로 강등.**
> 코드 직접 이식 대상이 아니다. Godot 로직이 궁금할 때 zip에서 찾아 읽는 용도.
> (godot-ver.zip은 `soulcommander/` 루트에 있음 — 예: `unzip -p godot-ver.zip "*/scripts/battle/*"`)
>
> 규칙: 슬라이스(Boot→전투→세이브)에 필요한 것만 먼저. 나머지는 'port on demand'.
> 테스트 106개 중 게이트용(저장 원자성·소환 시드/피티·전투 스모크)만 번역, 나머지는 폐기.

## → Assets/Tests/ (106개)
_선택적 → UTF EditMode. 우선: 저장 원자성·소환 시드/피티·전투 스모크. 106개 전부 말고 게이트용만._
- `scripts/tests/ap_chain_check.gd`
- `scripts/tests/atlas_margin_check.gd`
- `scripts/tests/atlas_visual_check.gd`
- `scripts/tests/audio_mapping_check.gd`
- `scripts/tests/audio_probe.gd`
- `scripts/tests/background_layer_check.gd`
- `scripts/tests/battle_ember_capture.gd`
- `scripts/tests/battle_framing_check.gd`
- `scripts/tests/battle_metrics_check.gd`
- `scripts/tests/bg_split_check.gd`
- `scripts/tests/boot_smoke_check.gd`
- `scripts/tests/boot_smoke_gatekeeper_check.gd`
- `scripts/tests/build_flow_check.gd`
- `scripts/tests/building_anim_check.gd`
- `scripts/tests/buildings3d_check.gd`
- `scripts/tests/bvis2_visibility_check.gd`
- `scripts/tests/cast_hud_check.gd`
- `scripts/tests/composer_check.gd`
- `scripts/tests/controls_geom_check.gd`
- `scripts/tests/crowd_instancer_check.gd`
- `scripts/tests/crowd_perf_check.gd`
- `scripts/tests/crowd_wave_check.gd`
- `scripts/tests/defeat_cycle_check.gd`
- `scripts/tests/defeat_economy_check.gd`
- `scripts/tests/drop_simulation_check.gd`
- `scripts/tests/ecology_8b_check.gd`
- `scripts/tests/ecology_boot_check.gd`
- `scripts/tests/ecology_phase1_check.gd`
- `scripts/tests/ecology_resources_check.gd`
- `scripts/tests/ecology_s1s2_check.gd`
- `scripts/tests/economy_longrun_check.gd`
- `scripts/tests/ember_exit_leak_check.gd`
- `scripts/tests/equip_visual_check.gd`
- `scripts/tests/equipment_check.gd`
- `scripts/tests/equipment_legacy_check.gd`
- `scripts/tests/equipment_panel_check.gd`
- `scripts/tests/equipment_spawn_check.gd`
- `scripts/tests/floor_metrics_check.gd`
- `scripts/tests/floor_metrics_report.gd`
- `scripts/tests/floor_progression_check.gd`
- `scripts/tests/flow_capture.gd`
- `scripts/tests/flow_chain_check.gd`
- `scripts/tests/forced_quit_check.gd`
- `scripts/tests/gate_registry_check.gd`
- `scripts/tests/gatekeeper_capture.gd`
- `scripts/tests/gatekeeper_reward_check.gd`
- `scripts/tests/gauge_hud_check.gd`
- `scripts/tests/gdd_anchor_check.gd`
- `scripts/tests/gltf_import_check.gd`
- `scripts/tests/hospital_rule_check.gd`
- `scripts/tests/hub_facility_check.gd`
- `scripts/tests/island3d_check.gd`
- `scripts/tests/keybind_check.gd`
- `scripts/tests/keybind_conflict_check.gd`
- `scripts/tests/keybind_mods_check.gd`
- `scripts/tests/keybind_pad_check.gd`
- `scripts/tests/kill9_child.gd`
- `scripts/tests/kill9_equivalence_check.gd`
- `scripts/tests/landmark_visual_check.gd`
- `scripts/tests/loading_capture.gd`
- `scripts/tests/login_screen_check.gd`
- `scripts/tests/look_dev_check.gd`
- `scripts/tests/memorial_panel_check.gd`
- `scripts/tests/multimesh_builder_check.gd`
- `scripts/tests/namegen_check.gd`
- `scripts/tests/p2_formula_check.gd`
- `scripts/tests/perf_fps_check.gd`
- `scripts/tests/personality_behavior_check.gd`
- `scripts/tests/personality_check.gd`
- `scripts/tests/phase3_slice_check.gd`
- `scripts/tests/render2530_capture.gd`
- `scripts/tests/s2_death_check.gd`
- `scripts/tests/s3_2_status_check.gd`
- `scripts/tests/s3_3_hud_check.gd`
- `scripts/tests/s3_4_icon_check.gd`
- `scripts/tests/s3_4_pattern_check.gd`
- `scripts/tests/s3_skill_check.gd`
- `scripts/tests/save_atomicity_check.gd`
- `scripts/tests/save_corrupt_util.gd`
- `scripts/tests/save_lock_check.gd`
- `scripts/tests/save_v2_migration_check.gd`
- `scripts/tests/save_v3_ecology_check.gd`
- `scripts/tests/save_version_check.gd`
- `scripts/tests/scaffolding_check.gd`
- `scripts/tests/soul_gauge_check.gd`
- `scripts/tests/speed_check.gd`
- `scripts/tests/summon_free_check.gd`
- `scripts/tests/summon_ghost_check.gd`
- `scripts/tests/summon_lineage_check.gd`
- `scripts/tests/summon_multi_check.gd`
- `scripts/tests/summon_pity_check.gd`
- `scripts/tests/summon_preview_capture.gd`
- `scripts/tests/summon_realpath_check.gd`
- `scripts/tests/summon_relationship_check.gd`
- `scripts/tests/summon_reroll_check.gd`
- `scripts/tests/summon_unlock_check.gd`
- `scripts/tests/tap_repro_check.gd`
- `scripts/tests/telegraph_edge_check.gd`
- `scripts/tests/telegraph_render_check.gd`
- `scripts/tests/telegraph_universal_check.gd`
- `scripts/tests/theme_visual_regression_check.gd`
- `scripts/tests/transition_tx_check.gd`
- `scripts/tests/tutorial_check.gd`
- `scripts/tests/tx_integration_check.gd`
- `scripts/tests/ui_back_nav_check.gd`
- `scripts/tests/ui_icons_check.gd`

## → Assets/Scripts/Battle/ (20개)
_전투 코어. 슬라이스는 최소 루프만 (입장→자율전투→승패→보상→귀환)._
- `scripts/battle/battle_flow_controller.gd`
- `scripts/battle/battle_manager.gd`
- `scripts/battle/battle_metrics.gd`
- `scripts/battle/cast_hud_bar.gd`
- `scripts/battle/damage_system.gd`
- `scripts/battle/death_epitaph.gd`
- `scripts/battle/ember_burst.gd`
- `scripts/battle/enemy_patterns.gd`
- `scripts/battle/hit_feedback.gd`
- `scripts/battle/keybind_conflict_policy.gd`
- `scripts/battle/keybind_service.gd`
- `scripts/battle/part_damage.gd`
- `scripts/battle/party_spawner.gd`
- `scripts/battle/personality_policy.gd`
- `scripts/battle/soul_gauge_overlay.gd`
- `scripts/battle/speed_control.gd`
- `scripts/battle/status_effects.gd`
- `scripts/battle/status_hud_icons.gd`
- `scripts/battle/tactical_phase_controller.gd`
- `scripts/battle/telegraph_engine.gd`

## → Assets/Scripts/Estate/ (16개)
_시설 10종. 슬라이스 범위 밖 — Phase 3에서._
- `scripts/hub/alchemist_lab.gd`
- `scripts/hub/building_anim.gd`
- `scripts/hub/building_mesh.gd`
- `scripts/hub/dining_hall.gd`
- `scripts/hub/dormitory.gd`
- `scripts/hub/equipment_panel.gd`
- `scripts/hub/estate_island.gd`
- `scripts/hub/estate_island_3d.gd`
- `scripts/hub/facility_actions.gd`
- `scripts/hub/facility_effects.gd`
- `scripts/hub/hub_facility_controller.gd`
- `scripts/hub/hub_visual_effects.gd`
- `scripts/hub/keybind_panel.gd`
- `scripts/hub/memorial_panel.gd`
- `scripts/hub/research_lab.gd`
- `scripts/hub/scaffolding_overlay.gd`

## → Assets/Scripts/Battle/Entities/ (7개)
_영웅/적 엔티티. 3D 모델 + Humanoid Avatar (Quaternius/KayKit 재사용)._
- `scripts/hero/boss_model_map.gd`
- `scripts/hero/character_composer.gd`
- `scripts/hero/enemy_entity.gd`
- `scripts/hero/hero_entity.gd`
- `scripts/hero/runtime_anim_retarget.gd`
- `scripts/hero/unit_animator.gd`
- `scripts/hero/wing_flap_driver.gd`

## → Assets/Editor/ or 삭제 (6개)
_개발용 스크립트 — 필요분만._
- `scripts/dev/dev_toggle.gd`
- `scripts/dev/gen_ui_icons.gd`
- `scripts/dev/shot_login.gd`
- `scripts/dev/shot_mainmenu.gd`
- `scripts/dev/theme_capture.gd`
- `scripts/dev/ui_atlas_showcase.gd`

## → 삭제 (아카이브된 서버 코드) (4개)
_참고용으로만._
- `docs/archive/net_server_ap/api_client.gd`
- `docs/archive/net_server_ap/game_services.gd`
- `docs/archive/net_server_ap/net_deprecated.gd`
- `docs/archive/net_server_ap/stamina_manager.gd`

## → Port on demand (Phase 8) (4개)
_런타임 0행 — 설계만 있음._
- `scripts/ecology/ecology_tick.gd`
- `scripts/ecology/habitat_mapper.gd`
- `scripts/ecology/population_ledger.gd`
- `scripts/ecology/resource_pool.gd`

## → 유지 — 3D 확정, 군중 인스턴싱 핵심 (4개)
_100+ 엔티티 draw call 방어. Unity에선 GPU Instancing + LODGroup으로 이전._
- `scripts/render/crowd_instancer.gd`
- `scripts/render/crowd_proxy_baker.gd`
- `scripts/render/crowd_render_adapter.gd`
- `scripts/render/crowd_render_coordinator.gd`

## → Assets/Editor/ (3개)
_*.py는 C# Editor 스크립트로 재작성 또는 삭제._
- `art/tools/anim_lookdev.gd`
- `art/tools/anim_showcase.gd`
- `art/tools/composer_showcase.gd`

## → Assets/Scripts/Core/ (3개)
- `scripts/battle_background.gd`
- `scripts/hero_visual.gd`
- `scripts/hub_scene.gd`

## → Assets/Scripts/Summon/ (3개)
_최저비용 빅윈: pity+시드 수학은 결정론이라 거의 줄 단위 포트. 테스트도 1:1 번역._
- `scripts/summon/name_generator.gd`
- `scripts/summon/soul_altar.gd`
- `scripts/summon/summon_pity.gd`

## → Assets/Scripts/Core/Auth.cs (2개)
_게스트 로그인만._
- `scripts/auth/auth_service.gd`
- `scripts/auth/auth_session.gd`

## → 2D: Cinemachine or PixelPerfect follow (2개)
_파일명 매칭 (game_camera.gd / game_camera_3d.gd)._
- `scripts/game_camera.gd`
- `scripts/game_camera_3d.gd`

## → 삭제 (2D 스프라이트 조합기 — Unity에선 불필요) (2개)
_lpc_composer/lpc_demo._
- `scripts/lpc_composer.gd`
- `scripts/lpc_demo.gd`

## → 유지 — 3D 확정 (2개)
_WFC 지형 생성기 + MultiMesh 인스턴싱 규약 그대로 이전._
- `scripts/terrain/battle_ambient.gd`
- `scripts/terrain/wfc_dungeon_generator.gd`

## → — (1개)
_범위 밖_
- `[rtk] output capped at 200 results`

## → Assets/Scripts/Core/SceneLoader.cs (1개)
_씬 전환 트랜잭션 개념 유지._
- `scripts/application_flow.gd`

## → Assets/Scripts/Core/AssetLoader.cs (1개)
_Resources/Addressables 로더._
- `scripts/asset_manager.gd`

## → Assets/Scripts/Audio/ (1개)
_AudioMixer + AudioSource 풀._
- `scripts/audio/audio_assets.gd`

## → Assets/Scripts/Audio/AudioManager.cs (1개)
_同上._
- `scripts/audio_manager.gd`

## → Assets/Scenes/Boot.unity + Core/Bootstrapper.cs (1개)
_부팅 체인._
- `scripts/boot/boot_scene.gd`

## → Assets/Scripts/Data/ (1개)
_JSON 런타임 로드 우선. ScriptableObject bake은 나중._
- `scripts/data/game_data.gd`

## → Assets/Scripts/Core/DebugHUD.cs (1개)
_FPS/프레임타임 바인딩._
- `scripts/debug_overlay.gd`

## → Assets/Scenes/DungeonSelect.unity (1개)
_슬라이스 범위 밖이면 스킵._
- `scripts/dungeon_select.gd`

## → Assets/Scripts/Estate/Equipment/ (1개)
_슬라이스 범위 밖._
- `scripts/equipment/equipment_system.gd`

## → Assets/Scripts/Core/GameState.cs (1개)
_Canonical state 원장. 단일 진실 공급원 규칙 유지._
- `scripts/game_scene_manager.gd`

## → Assets/Scenes/MainMenu.unity (1개)
_슬라이스: 최소 버튼만._
- `scripts/main_menu.gd`

## → Port on demand (1개)
_슬라이스 범위 밖._
- `scripts/minigames/anvil_minigame.gd`

## → Assets/Scripts/Core/PlayerController.cs (1개)
_Input System 액션 기반._
- `scripts/player_controller.gd`

## → Assets/Scripts/Save/SaveManager.cs (1개)
_세션락+원자적 쓰기 개념 유지. 첫 번째 테스트 대상._
- `scripts/save_manager.gd`

## → 삭제 (1개)
_스파이크 씬. 이력으로만 남김._
- `scripts/spike_node3d_iso.gd`

## → 삭제 (1개)
_Unity Test Framework로 대체._
- `scripts/test.gd`

---
## 비-.gd 대응표
- `scenes/*.tscn (10개)` → Assets/Scenes/*.unity
- `data/*.json (13개)` → Assets/Resources/Data/ — 런타임 로드
- `sprites/ (PNG)` → Assets/Art/Sprites/ — LFS
- `audio/ (WAV/OGG)` → Assets/Art/Audio/ — LFS, 태그에서 복원
- `fonts/ (TTF/OTF)` → Assets/Art/Fonts/ — LFS