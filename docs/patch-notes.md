# Patch implementation and address notes

[README](../README.md) · [Compatibility](compatibility.md) · [Build](build.md)

The native DLL changes three engine code locations to expand initial deployment
and bypass an arrival-capacity check. The addresses below apply to the supported
engine build.

## Address convention

The supported engine is PE32 x86, SHA-256:

```text
07cb2215b80591224a5f8889963344d560492f09c4d22696c988b957ca49b2b7
```

An **RVA** is relative to the module base. The analysis used Ghidra image base
`0x10000000`, so `Ghidra VA = 0x10000000 + RVA`. At runtime the DLL uses
`loaded empire.retail.dll base + RVA`; that base may differ because of ASLR.
Neither address form is a file offset. A file offset must be mapped through the
PE section containing the RVA.

| Purpose | Engine RVA | Ghidra VA | Treatment |
| --- | --- | --- | --- |
| Initial force classifier | `0x139B72` | `0x10139B72` | 13 overwritten bytes |
| Existing merge path | `0x139B7F` | `0x10139B7F` | Branch destination |
| Existing separate-force path | `0x139D0A` | `0x10139D0A` | Branch destination |
| Merge limit load | `0x139B96` | `0x10139B96` | 6 overwritten bytes |
| Arrival-capacity call | `0x2F65D2` | `0x102F65D2` | 5 overwritten bytes |
| Original capacity predicate | `0x304520` | `0x10304520` | Called by original code; its body is unchanged |

The three write sites total 24 engine bytes. The separately allocated stub page
holds the generated branch code; its address is assigned at runtime.

## Initial deployment classifier

Original bytes at RVA `0x139B72`:

```text
83 BB 74 01 00 00 02 0F 85 8B 01 00 00
```

These compare `[EBX+0x174]` with `2`, then jump to the separate-force path when
unequal. Equal falls through to the existing merge path at RVA `0x139B7F`.
The source refers to this value as a force kind. It is a different field from the
Lua battle-type string; `kind == 1` does not mean `land_normal` or `naval_normal`.

The patch replaces the 13 bytes with `JMP rel32` plus eight NOPs. In general mode,
the generated stub sends kinds `1` and `2` to the existing merge path and all other
values to the existing separate-force path. It reuses engine construction logic
rather than implementing a new unit constructor inside the mod DLL.

In settlement mode, kind `2` keeps the merge path. Kind `1` is redirected there
only when the alliance byte `[EDI+0x65]` is zero; other cases use the separate path.
The implementation uses zero to identify the attacking side and guards the
corresponding role-instruction signature before installation.

## Merge bound

Original bytes at RVA `0x139B96`:

```text
8B 90 24 01 00 00       MOV EDX,[EAX+0x124]
```

General mode substitutes:

```text
BA 00 02 00 00 90       MOV EDX,512; NOP
```

Settlement mode instead installs `JMP rel32; NOP` to a second stub. For the
attacking side, it loads `512`; for defenders it executes the original six-byte
load. Both return to RVA `0x139B9C`. Thus the attacker-only mode does not increase
the defender's merge bound.

The number is an internal merge bound, not a measured maximum supported army,
fleet, card count, or UI capacity.

## Reinforcement arrival check

At RVA `0x2F65D2`, the original five bytes are:

```text
E8 49 DF 00 00          CALL 0x10304520  ; in the Ghidra image
```

The target RVA follows from `0x2F65D2 + 5 + 0xDF49 = 0x304520`. The predicate tests
capacity using the owner's unit count and pending group contribution against a
manager bound; the final comparison is at RVA `0x3046C3` / VA `0x103046C3`.

Immediately after the call, the engine executes `TEST AL,AL` at RVA `0x2F65D7`,
then `JNZ` at RVA `0x2F65D9` to the blocking path at RVA `0x2F6826`. A nonzero
return byte therefore blocks this arrival path on capacity grounds.

The replacement is:

```text
30 C0 90 90 90          XOR AL,AL; NOP; NOP; NOP
```

It skips the call and supplies zero in `AL`. The following test sees zero, so that
capacity-dependent jump is not taken. The predicate function itself is unchanged;
this is a bypass of one call site. Other arrival conditions and the existing batch
processing remain. The bypass is included in both native installation modes;
attacker-only selection applies to the initial-deployment classifier and bound.

## Campaign lifecycle and automatic loading

`rdp_v07sp01_campaign.lua` requests a reset on `PendingBattle`, then applies the
allowlist and human/single-player checks. Normal land/naval battles,
`settlement_sally`, `coastal_battle` and `naval_breakout` request `rdp_install`
for both sides. Settlement and `fort_standard` assaults request
`rdp_install_settlement`, expanding attackers while retaining the original
defender path. Only `land_normal` with a contested garrison is promoted to
settlement mode; the three added types keep general mode when a contested
garrison is present. `UICreated` resets and re-evaluates an active pending battle. `BattleCompleted` requests
`rdp_disable`. It also removes three project-specific legacy battlefield
registrations from existing saves and never registers a new battlefield script.

The loader reads generated `rdp_v07sp01_payload.lua`, checks its size and `MZ`
prefix, and compares extracted/staged DLL files against the entire expected byte
string. The generated byte encoding is serialization, not encryption. The build
tools additionally require the exact native hash.

The fixed on-disk name is `rdp_v07sp01_93470fef577ebff5.dll`; the build output is
`rdp_native_merge_v07.dll`. Both names refer to the same expected bytes. The mod
DLL's preferred image base `0x62000000` is distinct from the engine analysis base.

## Native guards and restoration

The installer checks the engine's SHA-256 and instruction signatures at RVAs
`0x1B3310`, `0x2E99D0`, `0x139910`, `0x16A41B`, and `0x2F65D0`, then checks all
three original write-site byte sequences. The DLL is pinned in the process before
installation, so generated code does not outlive an unloaded mod module.

The source allocates a 4 KiB stub page, writes 159 bytes of generated code, switches
the page to executable/readable, and flushes the instruction cache. Engine pages
are made writable only for the update. The two deployment sites share a page; the
arrival site is handled separately. The code verifies writes, restores page
permissions, flushes caches, and attempts rollback when a step fails. Disable
requires the expected installed bytes before restoring the originals.

The exports return no Lua status values. Campaign `pcall` success cannot prove
native installation or rollback success. See the [known limits](compatibility.md).
