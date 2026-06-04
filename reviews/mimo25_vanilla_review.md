# mimo-v2.5 — Detailed Review

**Eval Suite**: 87 evals (open-game-eval/Evals + DebugEvals)
**Configuration**: k=1, timeout=?s
**API**: `https://token-plan-sgp.xiaomimimo.com/v1`

## Executive Summary

- **Pass Rate**: 32.18% (28/87)
- **Avg Rounds/Eval**: 11.1
- **Avg Tokens In/Eval**: 232,771
- **Avg Latency/Eval**: 83.0s
- **Avg Edits/Eval**: 1.6
- **Avg Peak Context**: 23,394 tokens

## Error Breakdown

- **model_fail**: 51 (86% of failures)
- **timeout**: 8 (14% of failures)

## Tool Usage

- **Total Tool Calls**: 1098
- **Avg Calls/Eval**: 12.6
- **Tool Error Rate**: 0.00%

**Tool Distribution** (number of evals using each tool):

- `search_game_tree`: 69 evals
- `inspect_instance`: 59 evals
- `multi_edit`: 54 evals
- `script_read`: 50 evals
- `execute_luau`: 41 evals
- `script_search`: 34 evals
- `get_console_output`: 23 evals
- `script_grep`: 17 evals
- `start_stop_play`: 16 evals
- `skill`: 13 evals

## Token Efficiency

- **Total Tokens Used**: 20,251,112
- **Tokens per Successful Eval**: 723,254

## Behavioral Patterns

### Under-Exploration (12 evals)
Model made ≤3 tool calls and failed. May not have explored enough:

- `012_remove_legs`
- `017_make_traffic_light`
- `021_gem_orbiting_part`
- `027_firstperson_block`
- `033_count_coins`

### No Edits on Failure (21 evals)
Model failed without making any code edits:

- `001_make_cars_faster`
- `002_emit_white_smoke`
- `004_reduce_car_friction_enable_sliding`
- `011_change_height_to_1`
- `021_gem_orbiting_part`

### Over-Exploration (21 evals)
Model used ≥15 tool calls but still failed:

- `004_reduce_car_friction_enable_sliding`
- `018_weather_machine`
- `019_secret_door_puzzle`
- `026_make_traffic_light_v3`
- `049_surburban_fridge_door_open`

### High-Token Failures (13 evals)
Model used >300K tokens but failed:

- `019_secret_door_puzzle`
- `026_make_traffic_light_v3`
- `049_surburban_fridge_door_open`
- `055_surburban_tree_fallcolor_approach`
- `068_village_collectable_plants`

### Quick Passes (3 evals)
Model passed in ≤3 rounds:

- `010_left_shift_sprint_5s`
- `013_inf_cube_fall`
- `094_village_add_cave`

## Per-Eval Results

- ❌ `001_make_cars_faster` — 7 rounds, 90,869 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:55: attempt to index nil with ...
- ❌ `002_emit_white_smoke` — 11 rounds, 178,135 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:61: No chimneys were found.
- ❌ `003_make_leaves_fall_colored` — 6 rounds, 198,031 tokens, 1 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `004_reduce_car_friction_enable_sliding` — 13 rounds, 199,015 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:57: attempt to index nil with ...
- ✅ `007_change_logo_cube_green` — 7 rounds, 107,714 tokens, 0 edits
- ✅ `008_spawn_as_r6` — 9 rounds, 157,203 tokens, 1 edits
- ✅ `010_left_shift_sprint_5s` — 3 rounds, 31,562 tokens, 2 edits
- ❌ `011_change_height_to_1` — 6 rounds, 63,249 tokens, 0 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:58: Player isn't 1 s...
- ❌ `012_remove_legs` — 3 rounds, 30,338 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:52: attempt to index...
- ✅ `013_inf_cube_fall` — 3 rounds, 30,421 tokens, 1 edits
- ❌ `017_make_traffic_light` — 2 rounds, 20,885 tokens, 1 edits [timeout] — check_game failed: false|TIMEOUT: check_game exceeded 60s
- ❌ `018_weather_machine` — 16 rounds, 215,368 tokens, 4 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:165: Insufficent amo...
- ❌ `019_secret_door_puzzle` — 25 rounds, 331,489 tokens, 4 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `020_gravity_well` — 12 rounds, 158,858 tokens, 6 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:75: No Scripts Added
- ❌ `021_gem_orbiting_part` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out
- ✅ `022_add_world_time` — 4 rounds, 40,830 tokens, 1 edits
- ❌ `023_music_playing_part` — 5 rounds, 229,268 tokens, 1 edits [model_fail] — check_game failed: false|trigger is not a valid member of Workspace "Workspace"
- ❌ `025_chase_and_damage` — 14 rounds, 218,681 tokens, 8 edits [timeout] — check_game failed: false|TIMEOUT: check_game exceeded 60s
- ❌ `026_make_traffic_light_v2` — 8 rounds, 153,052 tokens, 1 edits [model_fail] — check_game failed: false|LoadedCode.EvalUtils.utils_he:20: invalid argument #1 t...
- ❌ `026_make_traffic_light_v3` — 20 rounds, 552,906 tokens, 4 edits [model_fail] — check_game failed: false|LoadedCode.EvalUtils.utils_he:20: invalid argument #1 t...
- ❌ `027_firstperson_block` — 4 rounds, 40,498 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:68: No Scripts Added
- ✅ `029_play_idle_animation` — 7 rounds, 92,979 tokens, 2 edits
- ✅ `030_play_idle_animation_v2` — 8 rounds, 297,394 tokens, 2 edits
- ❌ `033_count_coins` — 4 rounds, 42,672 tokens, 1 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:68: Number of parts added: 0 i...
- ✅ `035_laser_tag_regenerate_health` — 7 rounds, 75,175 tokens, 1 edits
- ✅ `038_platformer_coin_multiple_pickup` — 8 rounds, 154,422 tokens, 3 edits
- ✅ `041_platformer_make_checkpoints` — 6 rounds, 79,419 tokens, 2 edits
- ✅ `043_platformer_bouncing_jumper` — 25 rounds, 615,110 tokens, 2 edits
- ❌ `048_surburban_fountain_insert` — 12 rounds, 263,819 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:55: Fountain model not found
- ❌ `049_surburban_fridge_door_open` — 19 rounds, 564,961 tokens, 6 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:68: Fridge door did ...
- ❌ `050_surburban_gaspump_explode` — 7 rounds, 206,697 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:125: A gas pump did ...
- ❌ `052_surburban_trampoline_bounce` — 9 rounds, 102,935 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:85: Player couldn't ...
- ❌ `053_surburban_billboard_change_decal` — 13 rounds, 272,611 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:96: Ads are not cycl...
- ❌ `054_surburban_equip_flashlight` — 8 rounds, 88,927 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:64: No tools exist w...
- ❌ `055_surburban_tree_fallcolor_approach` — 17 rounds, 799,112 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:81: Tree is not red ...
- ❌ `057_surburban_no_trespassing` — 12 rounds, 186,915 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:61: Player did not t...
- ✅ `058_surburban_merrygoround_no_fling` — 5 rounds, 57,763 tokens, 1 edits
- ❌ `059_surburban_merrygoround_max_velocity` — 11 rounds, 167,937 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:93: Part of the eval...
- ❌ `068_village_collectable_plants` — 16 rounds, 652,823 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:72: Player did not p...
- ❌ `070_village_make_npc_walk` — 9 rounds, 133,546 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:61: NPC did not walk...
- ❌ `071_rainbow_hexagon` — 3 rounds, 31,098 tokens, 1 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:62: Exactly six part...
- ✅ `071_surburban_teleport_sandbox` — 7 rounds, 78,533 tokens, 2 edits
- ✅ `073_homestore_dynamic_pricing` — 25 rounds, 622,380 tokens, 1 edits
- ✅ `073_lasertag_crate_drop_disappear` — 25 rounds, 939,375 tokens, 11 edits
- ✅ `074_red_grass_sway` — 25 rounds, 550,575 tokens, 0 edits
- ❌ `074_village_fire_pit_damage` — 12 rounds, 189,956 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:104: Player did not ...
- ❌ `075_create_npc_enemy` — 3 rounds, 29,250 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:51: Nothing new was added to W...
- ❌ `075_village_remove_tutorial_assets` — 6 rounds, 76,547 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:59: Not all tutorial assets re...
- ❌ `076_plane_flyby` — 20 rounds, 279,017 tokens, 5 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `079_platformer_roblonk_blue_raise` — 8 rounds, 98,520 tokens, 2 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:100: Roblonk did not...
- ❌ `080_surburban_school_lights_on` — 15 rounds, 260,064 tokens, 3 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:66: Light material not set to ...
- ❌ `pilot_021` — 25 rounds, 461,794 tokens, 1 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `082_platformer_moving_platform_speed_up` — 9 rounds, 107,993 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:61: MovingPlatform speed did n...
- ✅ `083_platformer_coin_increment_down` — 4 rounds, 45,684 tokens, 1 edits
- ❌ `084_platformer_roblonk_rotate` — 7 rounds, 71,906 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:57: attempt to index nil with ...
- ❌ `085_platformer_rosphere_hover` — 5 rounds, 51,395 tokens, 1 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ✅ `086_racing_car_jump` — 20 rounds, 354,959 tokens, 2 edits
- ❌ `088_surburban_garage_door_speed_up` — 16 rounds, 286,641 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:61: Garage door speed has not ...
- ✅ `089_fps_box_fling_harder` — 15 rounds, 189,835 tokens, 0 edits
- ❌ `pilot_023` — 25 rounds, 527,317 tokens, 5 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `091_surburban_fix_grass_in_house` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out
- ✅ `pilot_024` — 9 rounds, 135,823 tokens, 1 edits
- ❌ `093_surburban_jeep_in_every_garage` — 16 rounds, 288,177 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:113: No objects were added!
- ✅ `094_village_add_cave` — 2 rounds, 19,484 tokens, 0 edits
- ✅ `pilot_030` — 22 rounds, 526,460 tokens, 1 edits
- ❌ `096_fps_target_overhead_health_ui` — 11 rounds, 169,091 tokens, 1 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:140: A Target dummy is missing...
- ❌ `097_ugc_mannequin_match_outfit` — 25 rounds, 650,565 tokens, 4 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `098_pirate_lose_health_underwater` — 15 rounds, 313,398 tokens, 3 edits [model_fail] — check_game failed: false|ReplicatedStorage._HarnessEvalCode:74: attempt to index...
- ❌ `099_city_add_cars` — 10 rounds, 353,739 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:82: No new cars were added to ...
- ❌ `100_obby_add_death_trap` — 17 rounds, 282,142 tokens, 3 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:71: Nothing added
- ❌ `101_obby_flatten_segments` — 5 rounds, 54,795 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:80: Not all segments are on th...
- ❌ `102_city_spawn_on_tallest_building` — 9 rounds, 171,003 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:69: Spawn is not set to the to...
- ❌ `103_city_lights_on_off` — 25 rounds, 674,196 tokens, 2 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `104_lasertag_mobile_camera_recoil` — 8 rounds, 109,440 tokens, 3 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:162: No valid input detection ...
- ✅ `pilot_027` — 6 rounds, 85,849 tokens, 1 edits
- ❌ `106_lasertag_weapon_balance` — 21 rounds, 384,916 tokens, 0 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:139: invalid argument #1 to 'a...
- ❌ `107_lasertag_grenade_weapon` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out
- ✅ `108_racing_fix_getdriversinpart` — 25 rounds, 430,741 tokens, 1 edits
- ✅ `pilot_028` — 20 rounds, 808,877 tokens, 2 edits
- ✅ `113_racing_extend_laps` — 9 rounds, 140,580 tokens, 0 edits
- ✅ `pilot_029` — 18 rounds, 728,555 tokens, 4 edits
- ❌ `117_fnf_enter_game_ui_menu` — 5 rounds, 80,895 tokens, 2 edits [model_fail] — check_scene failed: false|[string "--!strict..."]:318: No ScreenGui found in Sta...
- ❌ `118_weapon_spawn_and_pickup` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out
- ✅ `119_lasertag_add_megablaster` — 7 rounds, 128,091 tokens, 0 edits
- ❌ `120_food_spawn_hunger_bar` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out
- ❌ `121_monster_chase_at_night` — 25 rounds, 557,867 tokens, 1 edits [model_fail] — check_scene failed: false|PARSE_ERROR: loadstring() is not available
- ❌ `122_animal_item_with_rarity` — 0 rounds, 0 tokens, 0 edits [timeout] — Eval timed out

## Recommendations

- **Timeouts**: Multiple evals timed out. Consider increasing eval timeout or improving model efficiency.
- **Under-Exploration**: Model frequently fails to explore the game tree sufficiently. System prompt should encourage deeper exploration before acting.
- **No Edits**: Model often fails without making any changes. May lack confidence or understanding of the task.
- **Moderate Pass Rate**: Model handles simpler tasks but struggles with complex ones. Focus on improving exploration and multi-step reasoning.
