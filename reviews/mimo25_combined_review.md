# MiMo V2.5 Non-Pro — Combined Eval Review
Generated: 2026-06-05 02:37 UTC
Runs: vanilla_0603_1636 (original 87) + vanilla_0604_1358 (rerun 14 failed)

## Scorecard
- **Pass rate: 30/87 (34.5%)**
- Original: 28/87 (32.2%) → Combined: 30/87 (34.5%)
- Rerun recovered 2 evals: 118_weapon_spawn_and_pickup, 120_food_spawn_hunger_bar

## Error Breakdown
- model_fail: 51
- timeout: 5
- EXECUTE_PLAY_ERROR: 5 (NEW — Studio state corruption)
- harness_error: 1
- passed: 30

## New Issue: EXECUTE_PLAY_ERROR
5 evals that previously failed with model_fail now fail with:
`ExecutePlayModeAsync: can only be called from the edit DataModel`

This means Studio entered play mode but the harness couldn't stop it properly,
leaving the DataModel in a non-edit state for subsequent evals. This is a
harness-side state management issue, not a model failure.

Affected evals:
- 085_platformer_rosphere_hover
- pilot_023
- 097_ugc_mannequin_match_outfit
- 103_city_lights_on_off
- 121_monster_chase_at_night

## Rerun Results Detail

- 003_make_leaves_fall_colored: ✗ FAIL (model_fail)
  Error: check_scene failed: false|_HarnessEvalCheck:60: This leaf isn't autumn colored: Leaves
- 017_make_traffic_light: ✗ FAIL (timeout)
  Error: check_game failed: false|TIMEOUT: check_game exceeded 60s
- 019_secret_door_puzzle: ✗ FAIL (model_fail)
  Error: check_game failed: false|SecretDoor is not a valid member of Workspace "Workspace"
- 025_chase_and_damage: ✗ FAIL (timeout)
  Error: check_game failed: false|TIMEOUT: check_game exceeded 60s
- 076_plane_flyby: ✗ FAIL (model_fail)
  Error: check_game failed: false|ReplicatedStorage._HarnessEvalCode:68: No new scripts were added, which is required to move the
- pilot_021: ✗ FAIL (model_fail)
  Error: check_scene failed: false|_HarnessEvalCheck:181: No script found in ServerScriptService that handles car color changing 
- 085_platformer_rosphere_hover: ✗ FAIL (model_fail)
  Error: check_game failed: false|EXECUTE_PLAY_ERROR: ExecutePlayModeAsync: can only be called from the edit DataModel
- pilot_023: ✗ FAIL (model_fail)
  Error: check_game failed: false|EXECUTE_PLAY_ERROR: ExecutePlayModeAsync: can only be called from the edit DataModel
- 097_ugc_mannequin_match_outfit: ✗ FAIL (model_fail)
  Error: check_game failed: false|EXECUTE_PLAY_ERROR: ExecutePlayModeAsync: can only be called from the edit DataModel
- 103_city_lights_on_off: ✗ FAIL (model_fail)
  Error: check_game failed: false|EXECUTE_PLAY_ERROR: ExecutePlayModeAsync: can only be called from the edit DataModel
- 118_weapon_spawn_and_pickup: ✓ PASS
- 120_food_spawn_hunger_bar: ✓ PASS
- 121_monster_chase_at_night: ✗ FAIL (model_fail)
  Error: check_game failed: false|EXECUTE_PLAY_ERROR: ExecutePlayModeAsync: can only be called from the edit DataModel
- 122_animal_item_with_rarity: ✗ FAIL (harness_error)
  Error: Fatal: unhandled errors in a TaskGroup (1 sub-exception)

## Debug Evals (4/30 ran)
Only 4 debug evals executed — these were the debug variants of failed evals.
Full 30 debug evals run not yet kicked off.

- 003_make_leaves_fall_colored_bug_1: ✗ FAIL (model_fail)
- 017_make_traffic_light_bug_1: ✗ FAIL (timeout)
- 017_make_traffic_light_bug_2: ✗ FAIL (timeout)
- 017_make_traffic_light_bug_3: ✗ FAIL (timeout)

## Recommendations
1. **Fix EXECUTE_PLAY_ERROR**: Add explicit `start_stop_play(stop=True)` before each eval start, or check DataModel state
2. **Run full 30 debug evals**: `python runner.py run-all` with debug dir
3. **Timeout evals still failing**: 5 evals timeout despite 90s per-call limit — likely check_game hangs (not LLM)
4. **Harness error on 122_animal_item_with_rarity**: TaskGroup crash needs investigation