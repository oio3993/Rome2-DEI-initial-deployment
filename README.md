# Rome2 DEI Initial Deployment

Initial deployment expansion for **Total War: Rome II** with **Divide et Impera**,
maintained by **oio3993**. The public source baseline is **v07 NavalNormal Test01**.

The mod makes eligible supporting forces from the same faction available during
initial deployment. Campaign Lua selects the battle mode, and an embedded x86
DLL temporarily patches the supported engine in memory.

## Features

- General land battles and normal naval battles use the general deployment mode
  for both sides.
- Settlement assaults use an attacker-only expansion. Defending external armies
  keep their separate reinforcement entry; the existing garrison path is retained.
- An arrival-capacity check bypass is included in the native patch.
- The pack contains its DLL as generated Lua byte data. The loader extracts or
  reuses the exact DLL automatically.
- Campaign callbacks request restoration before selecting a new pending battle
  and after battle completion. No custom battlefield script is registered.

This does not add initial deployment for other-faction allies. The internal merge
limit of 512 is a patch parameter, not a verified promise of 512 usable units or
cards. See [compatibility and limits](docs/compatibility.md).

## Requirements

- [Total War: Rome II](https://store.steampowered.com/app/214950/Total_War_ROME_II__Emperor_Edition/)
  on Windows, using the supported x86 engine identified below.
- [Divide et Impera](https://divideetimperamod.com/), with campaign scripts matching
  the recorded input baseline. Compatibility is identified by hashes rather than
  a claim to support every DEI release.
- A single-player campaign battle with a human faction on either side. Both
  attacker and defender must exist.
- The normal game working directory containing `Rome2.exe`, with permission to
  create the mod's DLL when it is not already present.

Required `empire.retail.dll` SHA-256:

```text
07cb2215b80591224a5f8889963344d560492f09c4d22696c988b957ca49b2b7
```

The native code checks this engine hash and the expected instructions before
installation. Engine updates require a compatibility review; this release does
not locate new patch addresses automatically.

## Install

Use the player pack supplied with this version, or create it with the
[build instructions](docs/build.md). A source checkout alone is not an installed mod.

1. Fully exit the game.
2. Disable previous initial-deployment, combined, and reinforcement-cap-only packs.
3. Place `rdp_v07_singlepack_mc01_naval_test01.pack` in the game's `data` directory
   and enable it in the mod manager.
4. Give this pack's campaign `scripting.lua` entries priority over the DEI originals.
   Another mod replacing the same entry can prevent this mod from loading.
5. Load the campaign and test a newly generated manual battle. Restarting a battle
   that was already constructed is not an installation check.

The loader creates `rdp_v07sp01_93470fef577ebff5.dll` beside `Rome2.exe` in the
working directory. An identical existing file is reused; a different or unreadable
existing file is left untouched and loading fails. The original engine file stays
unchanged. Neither the source directories nor a standalone DLL need to be copied
into `data`.

## Remove

Fully exit the game, then disable or remove the pack. The generated DLL can remain
unused, or you can remove the exact mod DLL named above and its `.rdp-tmp` staging
file while the game is closed. Keep the original `empire.retail.dll`.

## Support and verification

The campaign policy accepts `land_normal`, `naval_normal`, `settlement_standard`,
`settlement_unfortified`, and `town_normal`. A contested-garrison `land_normal`
battle selects settlement mode. Other battle types, multiplayer, AI-only battles,
and standalone custom battles are outside this release's supported integration.

The author reported successful initial deployment in a combined army/fleet attack
on a port settlement and later reported that the normal-naval trial worked.
These reports do not establish every naval subtype, campaign, or force size.

The native DLL has been recompiled from C with byte-for-byte identity to the
baseline. PE/ABI, 103 linked operands and ASLR fixups passed verification. The
recreated pack also matches the baseline exactly. Lua host checks use a separate
Lua 5.4 library and mocked native exports; they do not substitute for Rome II's
embedded Lua or an actual battle test. Details are in the linked documents.

## Source and development

| Location | Purpose |
| --- | --- |
| `src/native/` | Freestanding x86 C patch, instruction builders, export definition |
| `src/lua/` | Campaign policy and automatic DLL loader |
| `integration/` | The small bootstrap appended to local DEI campaign inputs |
| `tools/` | Native compilation, payload/pack generation and verification |
| `tests/` | Standalone Lua host and loader, campaign and packaging checks |

- [Build and test](docs/build.md)
- [Continuous integration](docs/build.md#continuous-integration)
- [Compatibility, battle policy and known limits](docs/compatibility.md)
- [Patch addresses and implementation](docs/patch-notes.md)
- [Changelog](CHANGELOG.md)

Original engine binaries and full DEI campaign entry scripts are not included in
this source repository. Pack generation requires your own matching local DEI
inputs. Generated DLLs, payloads, packs and reports belong under ignored build
output directories.

## Author and license

Steam / GitHub / Discord: **oio3993** ([GitHub](https://github.com/oio3993)).

Copyright (c) 2026 oio3993. This project's code and documentation are available
under the [MIT License](LICENSE). Game and DEI assets, and external build tools,
remain subject to their own terms. This is an independent mod project.
