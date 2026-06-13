# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a ZMK firmware config for the **Cornix** split keyboard (Corne-inspired, 3×6 + 3-key thumb cluster per half, nRF52840). It also supports separate dongle boards. See `AGENTS.md` for the contributor guide (structure, style, commit conventions) — this file focuses on build mechanics and architecture not obvious from a single file.

## Build & dev environment

All toolchain (`west`, `just`, `yq`, Zephyr SDK, keymap-drawer) comes from the Nix flake. Enter it first:

```
nix develop
```

`just` is the task runner (wraps `west build`). Common commands:

- `just init` — one-time `west init -l config && west update` to fetch ZMK + modules into the workspace.
- `just list` — list firmware targets parsed from `build.yaml`.
- `just build all` — build every target; `just build cornix_left` — build targets matching the expr (matched against board/shield/snippet/artifact-name). Artifacts are copied to `firmware/<artifact-name>.uf2`.
- `just draw cornix` — render a keymap SVG via keymap-drawer (needs a `draw/config-<kb>.yaml`).
- `just test <testpath>` — run a ZMK native_posix snapshot test; the dir must contain `events.patterns` + `keycode_events.snapshot`. Flags: `--no-build`, `--verbose`, `--auto-accept` (updates the snapshot).
- `just clean` / `just clean-all` — remove build artifacts / also `.west` and `zmk`.

Local `just` builds require **`ZMK_LIB_PREFIX`** pointing at the parent dir that contains `zmk/app` (the `west` workspace). Never set `ZEPHYR_BASE` — `west` manages it (the flake's shellHook sets `Zephyr_DIR` instead).

> **Gotcha:** the `Justfile` hardcodes `config := absolute_path('config2')`, but the checked-in config lives in `config/`. To build the in-repo config locally, change that line (or symlink) so the config path resolves to `config/`. GitHub Actions builds from `build.yaml` directly and is unaffected.

CI: `.github/workflows/build.yml` builds the `build.yaml` matrix on push; `release_with_tag.yml` builds on `v*.*` tags.

## Architecture

**Two firmware shapes share one config tree (`config/`):**
- **Board-based split** (`cornix_left`, `cornix_right`, `cornix_ph_left`): the keyboard itself is a custom Zephyr *board* under `boards/arm/cornix/`. These build with no shield.
- **Dongle**: a generic board (`nice_nano_v2`, `seeeduino_xiao_ble`) + a *shield* from `boards/shields/` (`cornix_dongle_adapter` provides the split-central glue; `cornix_dongle_eyelash`, `dongle_display`, `dongle_screen` add a display). `cornix_ph_left` is the "peripheral" left half used **with** a dongle (vs. `cornix_left` which is central itself).

**Board definitions** (`boards/arm/cornix/`):
- `cornix.dtsi` — shared DTS (kscan matrix, sensors, RGB, BLE radio via `nrf_e73.dtsi`) included by left/right/dongle `.dts` files. The dongle uses `cornix_dongle_common.dtsi` instead and must **not** include `cornix.dtsi`.
- `cornix-layouts.dtsi` — `zmk,matrix-transform` (14 cols × 4 rows) mapping physical switches to keymap positions; selected via `chosen { zmk,physical-layout }`.
- `cornix-pinctrl.dtsi` — GPIO/pin assignments. `Kconfig.defconfig` sets split central/peripheral roles per board (`cornix_left`/`cornix_dongle` are central).
- `*_defconfig` files set per-board Kconfig; `cornix.conf` is shared runtime config.

**Snippets** decouple radio/flash variants: `nrf52840-nosd` builds without the SoftDevice (this is the default flash layout — see README's bootloader-recovery warnings before changing flash partitions); `studio-rpc-usb-uart` enables ZMK Studio over USB.

**Keymap** (`config/cornix.keymap`, plus `cornix42` variant): 5 layers — `BASE`(0) `NUM`(1) `SYM`(2) `MOUSE`(3) `BT`(4). Heavy use of home-row mods (custom `hold-tap` behaviors per hand, separate thumb triggers), Japanese IME macros (`LANG1`/`LANG2`), and pointing/scroll. It depends on **`urob/zmk-helpers`** (`#include "zmk-helpers/helper.h"`) and the local `config/includes/cornix54.h` for position aliases (`LT0..RB5`, `LH0..RH2`). When editing combos, `just build` runs `_parse_combos` which auto-tunes `CONFIG_ZMK_COMBO_MAX_*` in the `.conf` from `combos.dtsi`.

**Dependencies** (`config/west.yml`): ZMK pinned to `v0.3.0`; modules `zmk-helpers` (urob), `zmk-rgbled-widget` + `zmk-dongle-display` (hitsmaxft fork), `zmk-dongle-screen` (janpfischer). `zephyr/module.yml` makes this repo itself a ZMK module so its boards/shields are discovered.
