# Repository Guidelines

## Project Structure & Module Organization

This repository contains Cornix keyboard support for ZMK. Board definitions are in `boards/arm/cornix/`, including DTS, Kconfig, CMake, pinctrl, layout metadata, and the default board keymap. Optional shields are in `boards/shields/`, grouped by shield name such as `cornix_indicator`. User-facing config files are in `config/`, with keymaps in `config/*.keymap`, metadata in `config/*.json`, and shared includes in `config/includes/`. Build matrix entries are in `build.yaml`; workflows are in `.github/workflows/`. Recovery firmware is under `bootloader/`; stock RMK firmware archives are under `rmkfw/`.

## Build, Test, and Development Commands

- `nix develop`: enter the Zephyr/ZMK shell with `west`, `just`, `yq`, and keymap drawing tools.
- `west init -l config && west update --fetch-opt=--filter=blob:none && west zephyr-export`: initialize ZMK dependencies from `config/west.yml`.
- `just list`: list firmware targets derived from `build.yaml`.
- `just build all`: build all targets and copy artifacts into `firmware/`.
- `just build cornix_left`: build matching targets only.
- `just draw cornix`: render a keymap SVG when the matching draw config exists.
- `just clean`: remove `.build/` and `firmware/` artifacts.

Local `just` builds require `ZMK_LIB_PREFIX` to point at the parent directory containing `zmk/app`. If building the checked-in config, ensure the `Justfile` config path matches `config/`.

## Coding Style & Naming Conventions

Follow existing ZMK and Zephyr style. Use 4-space indentation in `.keymap`, `.dtsi`, `.overlay`, Kconfig, CMake, and C files unless aligning keymap columns. Keep devicetree node labels and shield names lowercase with underscores, for example `cornix_dongle_adapter`. Use descriptive artifact names in `build.yaml`, such as `cornix_right_nosd`. Preserve SPDX headers in copied ZMK source files.

## Testing Guidelines

There is no checked-in unit test suite. Validate changes by building affected matrix entries locally or through GitHub Actions. For keymap behavior tests, `just test <testpath>` expects a ZMK native test config directory containing `events.patterns` and `keycode_events.snapshot`.

## Commit & Pull Request Guidelines

Recent commits use short, imperative, sentence-case subjects, for example `Add Bluetooth clear key`. Keep commits focused on one board, shield, keymap, or workflow change. Pull requests should describe the hardware/config affected, list tested build targets, link issues when relevant, and include generated SVGs for layout changes. Use `v*.*` tags for release workflow builds.

## Security & Configuration Tips

Do not commit `.env`, `.direnv`, `.zmk/`, `.build/`, `firmware/`, or generated toolchain output. Be careful when changing flash layout or `nrf52840-nosd` snippets; document recovery impact in the PR.
