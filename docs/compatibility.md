# Compatibility

[README](../README.md) · [Build](build.md) · [Patch implementation](patch-notes.md)

## Requirements

Windows with Total War: Rome II and Divide et Impera. The mod applies to
single-player campaign battles involving a human faction on either side.

The native patch supports the x86 `empire.retail.dll` with this SHA-256:

```text
07cb2215b80591224a5f8889963344d560492f09c4d22696c988b957ca49b2b7
```

The DLL checks the engine and patch locations before applying changes. A game
update that changes the engine requires a corresponding mod update.

## Battle types

| Battle | Initial deployment expansion |
| --- | --- |
| Normal land battle (`land_normal`) | Both sides |
| Normal land battle (`land_normal`) with a contested garrison | Attackers only |
| Normal naval battle (`naval_normal`) | Both sides |
| Settlement sally (`settlement_sally`) | Both sides |
| Coastal battle (`coastal_battle`) | Both sides |
| Naval breakout (`naval_breakout`) | Both sides |
| Fort assault (`fort_standard`) | Attackers only |
| Settlement assault (`settlement_standard`) | Attackers only |
| Unfortified settlement assault (`settlement_unfortified`) | Attackers only |
| Town battle (`town_normal`) | Attackers only |

In settlement and fort assaults, only the attackers receive expanded initial
deployment. Defending external armies keep their reinforcement entry, and
existing garrison deployment is preserved. Supporting forces from other factions
are not merged into initial deployment.

Other battle-type values, including `naval_blockade`, `port_assault` and
`settlement_relief`, are not included. These entries refer to the internal
battle-type value; the visible battle situation alone does not determine that
value. Multiplayer, AI-only battles and standalone
custom battles are outside the campaign integration.

## Campaigns

The pack includes these campaign entry points:

```text
main_3c          main_emperor     main_gaul
main_greek       main_invasion    main_punic
main_rome        prologue_01      prologue_02
```

Other campaign folders require their own integration. The pack uses the recorded
DEI campaign scripts; source builds check their hashes as described in the
[build guide](build.md#supply-local-campaign-inputs-and-build-the-pack).

## Mod conflicts

This pack's campaign `scripting.lua` entries must take priority over DEI's entries.
Another mod replacing the same campaign scripts needs a combined integration.
Mods patching the same engine functions can also conflict; the affected locations
are listed in the [patch implementation](patch-notes.md).

## Loading problems

- The game must use its normal working directory containing `Rome2.exe`.
- The loader needs permission to create its mod DLL in that directory. An
  identical existing DLL is reused.
- A different or unreadable file named `rdp_v07sp01_93470fef577ebff5.dll` prevents
  loading. Close the game and check that specific mod file if loading fails.
- This version does not produce a runtime log.

If the mod has no effect, check that the pack is enabled, its campaign scripts
have priority, and the battle and engine version are supported. When reporting
an issue, include the campaign, battle situation and other active mods.
