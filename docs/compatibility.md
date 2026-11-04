# Compatibility and known limits

[README](../README.md) · [Build](build.md) · [Patch notes](patch-notes.md)

## Supported engine

| Property | Required value |
| --- | --- |
| Platform | Windows, PE32 / x86 engine |
| Module | `empire.retail.dll` |
| Engine SHA-256 | `07cb2215b80591224a5f8889963344d560492f09c4d22696c988b957ca49b2b7` |
| Analysis image base | `0x10000000` |

The native installer hashes the engine file associated with the loaded module,
checks instruction signatures, and checks the original bytes at all three write
sites. A failed preflight prevents installation. Runtime addresses use the loaded
module base plus RVA, so an ASLR base change is different from an engine update.

This baseline uses fixed RVAs with strict identity checks. It does not include
signature scanning, automatic engine-version migration, or the later Profile
Test01 status/diagnostic implementation.

## Campaign policy

All accepted cases require single-player, an attacker, a defender, and a human
faction on at least one side. A human defender is accepted when the attacker is AI.

| Pending battle type | Native mode requested |
| --- | --- |
| `land_normal`, without a contested garrison | General: both sides |
| `land_normal`, with a contested garrison | Settlement: attacker-only expansion |
| `naval_normal` | General: both sides |
| `settlement_standard` | Settlement: attacker-only expansion |
| `settlement_unfortified` | Settlement: attacker-only expansion |
| `town_normal` | Settlement: attacker-only expansion |
| Any other type | No installation request |

The naval branch does not select settlement mode merely because a garrison is
contested. `naval_blockade`, `naval_breakout`, `port_assault`, `coastal_battle`,
`settlement_sally`, `settlement_relief`, and `fort_standard` are outside the
allowlist. A port location alone does not determine which string the game reports.

Other-faction allied initial deployment, multiplayer, AI-only battles, and
frontend/custom-battle integration are not provided by this campaign module.
Autoresolve behavior is not a validated feature of the initial-deployment patch.

## Campaign entry points and DEI inputs

The pack connects the shared campaign module from these nine entry points:

```text
main_3c          main_emperor     main_gaul
main_greek       main_invasion    main_punic
main_rome        prologue_01      prologue_02
```

Inclusion of an entry is a packaging fact, not proof of gameplay testing in that
campaign. Unlisted campaign folders are not connected by this pack.

The source repository includes only the project's bootstrap fragment. The pack
builder reads nine local original `scripting.lua` files, requires their hashes to
match `tools/project.py`, and appends the fragment without changing their original
prefixes. A different DEI release or edited input is rejected for review. No DEI
version number is inferred from these input hashes.

The finished pack contains complete campaign entry overrides. It must take
priority over the matching DEI entries. Another submod overriding one of those
same paths needs an explicit integration; enabling both is not enough. Do not
combine this pack with previous initial-deployment, combined, or cap-only variants,
or with another patch that changes these engine sites.

## Loader and native limitations

- The loader supports the normal working directory containing `Rome2.exe`.
  It does not search alternate installation paths.
- It extracts the exact 10,092-byte DLL to
  `rdp_v07sp01_93470fef577ebff5.dll`. It requires write access when this file is
  missing, uses `.rdp-tmp` staging, and reuses an identical existing DLL.
- A mismatching or unreadable existing final DLL is left in place and causes
  failure. Concurrent game instances are outside this loader's supported use.
- Runtime errors are contained silently. This baseline writes no installation
  log or status file.
- The three native exports return **zero Lua values**. A successful Lua `pcall`
  means the function call did not raise an error; it does not confirm installation
  or restoration. The DLL's existence also does not confirm an active patch.
- Restoration is requested on the next pending-battle evaluation and on
  `BattleCompleted`, with another reset/re-evaluation on `UICreated`. This source
  baseline does not expose a status result proving that restoration succeeded.
- The merge value `512` changes one internal bound. UI card capacity, pathfinding,
  placement, stability, performance, and arbitrary force sizes are not guaranteed
  by that number. Other reinforcement arrival conditions remain in effect.

If the mod has no visible effect, first check the enabled pack, campaign entry
priority, accepted battle type, engine hash, and loader directory/file conditions.
Preserve a mismatching DLL for inspection before deciding to remove that specific
mod file. There are no baseline runtime logs to collect. Reports should identify
the pack hash, campaign, reported battle type if known, participating forces, and
what was present at initial deployment versus what arrived later.

## What has been verified

| Evidence | Result and scope |
| --- | --- |
| Author's game reports | Long-running campaign playtesting confirmed intended behavior in most situations encountered. This extends the earlier successful combined army/fleet port attack and normal-naval trial reports. |
| Native rebuild, 2026-11-04 | GCC `13.2.0-23ubuntu4` / binutils `2.42-4ubuntu2` reproduced the baseline DLL exactly. |
| Native static verification | PE32 x86, imports/exports, DllMain stdcall return, all 103 linked operands, and required ASLR fixups passed. The mod DLL was not loaded by these checks. |
| Standalone Lua tests | 41 loader cases and 33 campaign cases passed on a separate Lua 5.4 Windows host. Native exports were mocked. |
| Pack/input tests | 19 synthetic and tamper cases passed without DEI inputs or a released pack. The earlier 14-case run is historical. |
| Local CI rehearsal, 2026-11-04 | The pinned Ubuntu build-root bootstrap, fresh native rebuild, 41 loader cases, 33 campaign cases and all 19 packaging cases passed on Linux. GitHub-hosted workflow execution is a separate result after pushing. |
| Full rebuilt release | All 12 pack entries, nine original DEI prefixes, runtime source identity, 12 Lua syntax checks and all 10,092 interpreted payload bytes passed. Pack bytes match the baseline. |

Gameplay validation comes from the author's long-running campaign playtesting.
Automated checks separately validate source, binary and packaging consistency;
they do not execute Rome II or its embedded Lua 5.1.
