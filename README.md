# Rome2 DEI Initial Deployment

Makes supporting armies and fleets from the same faction available during initial
deployment in **Total War: Rome II** with **Divide et Impera**.

## Features

- Initial deployment for both sides in normal land and naval battles.
- Attacker-only expansion in settlement assaults; defending external armies
  arrive as reinforcements.
- Reinforcement arrival-capacity bypass.
- Automatic DLL loading from the pack, with no manual DLL installation.

## Requirements

- [Total War: Rome II](https://store.steampowered.com/app/214950/Total_War_ROME_II__Emperor_Edition/) on Windows.
- [Divide et Impera](https://divideetimperamod.com/).
- Single-player campaign battles involving a human faction.

See [compatibility](docs/compatibility.md) for supported battles, campaigns and
engine version information. Supporting forces from other factions are not merged
into initial deployment.

## Install

1. Close the game.
2. Copy `rdp_v07_singlepack_mc01_naval_test01.pack` into the game's `data` folder
   and enable it in your mod manager.
3. Set its load priority above DEI so its campaign scripts take precedence.

The pack automatically creates `rdp_v07sp01_93470fef577ebff5.dll` in the game folder
when a campaign loads. The original `empire.retail.dll` stays unchanged.

## Remove

Close the game and disable or remove the pack. You may also remove
`rdp_v07sp01_93470fef577ebff5.dll` from the game folder.

## Source and development

Native C and campaign Lua sources are in `src/native/` and `src/lua/`.
Building the pack requires your own matching DEI campaign scripts.

- [Build and test](docs/build.md)
- [Patch implementation](docs/patch-notes.md)
- [Changelog](CHANGELOG.md)

## Author and license

By [oio3993](https://github.com/oio3993) (Steam / GitHub / Discord).

Copyright (c) 2026 oio3993. [MIT License](LICENSE).
Game and DEI assets remain subject to their own terms.
