# Changelog

## Unreleased

### Source publication preparation

- Arrange the existing NavalNormal Test01 sources under `src/native/` and
  `src/lua/`, with the local DEI bootstrap in `integration/`.
- Adapt native/pack builders and release verification to the public layout.
  Generate the payload from the built DLL and obtain full campaign entries from
  matching local DEI inputs rather than publishing their original scripts here.
- Adapt standalone loader/campaign tests, add packaging/input checks, and keep
  generated files outside the tracked source tree.
- Reproduce the baseline DLL from C with GCC `13.2.0-23ubuntu4` and binutils
  `2.42-4ubuntu2`; verify PE/ABI, 103 linked operands and ASLR fixups.
- Add a Windows launcher for the separately prepared portable GNU environment.
- Reproduce the existing NavalNormal Test01 pack byte for byte with full native
  and payload verification.
- Document installation, compatibility, build steps and patch behavior.
- Apply the MIT License, copyright 2026 oio3993.

These publication changes retain the baseline runtime C/Lua bytes, DLL and pack.
No new gameplay behavior or new game test is claimed by this entry.

## NavalNormal Test01 baseline

- Add `naval_normal` to the existing campaign battle-type allowlist and use the
  general deployment mode for that case.
- Retain the existing land/settlement policy, nine campaign entry points,
  automatic DLL loader, native patch bytes and engine identity checks.
- Record the author's subsequent report that the naval trial worked. This is not
  an exhaustive validation of naval subtypes or campaign combinations.

This source baseline excludes the later Profile Test01 diagnostics and the
separate reinforcement-cap-only variant.
