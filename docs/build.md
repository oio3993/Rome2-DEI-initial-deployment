# Building NavalNormal Test01

This source tree targets the unchanged **Initial Deployment v07 NavalNormal Test01**
runtime. The C sources and the campaign/loader Lua modules match the successful
baseline pack. The later Profile Test01 diagnostics are not included.

The game target is **Windows x86**. The original native compilation route uses a
**Linux/WSL build host**, GCC emitting i386 ELF, Python 3.10+, and GNU ld with
`i386pe` emulation. It does not use MSVC or a MinGW COFF compiler. The existing
ELF-to-COFF and import-object generators remain part of that route.

## Dependencies

- Python 3.10 or newer, standard library only.
- GCC with `-m32` compilation and GNU ld with `i386pe` support for recompilation.
- A Lua **5.4 shared library** for developer tests (`liblua5.4.so.0` on the original
  Linux host). For a compatible Windows build, set `RDP_LUA_LIBRARY` to a local
  Lua 5.4 DLL matching the architecture of Python. The repository does not bundle
  that test runtime.
- Local, unmodified campaign `scripting.lua` inputs from the recorded DEI baseline
  for the final pack. No game engine DLL is needed for building or these tests.

The test host is standalone Lua 5.4. It does not execute Rome II's embedded Lua 5.1
or load the mod DLL. `package.loadlib` is mocked in the loader tests. File fault
cases are modeled; one additional case performs real host binary file I/O.

## Recompile the DLL

Run commands from the repository root:

```sh
python3 tools/build_native.py
python3 tools/verify_native.py
```

Use `--cc /path/to/gcc --ld /path/to/ld` if needed. Compiler/linker versions and
flags are recorded in `build/reports/native_build.json`. The verifier retains the
original PE imports/exports, entry-point ABI, linked COFF operand and ASLR fixup
checks. It needs `build/patch.obj` from the corresponding native build.

The DLL must be 10,092 bytes and have SHA-256:

```text
93470fef577ebff54d34b16dfbbf0833ed8454857f11680cbc7095f5f9b81b81
```

A compiler/linker combination producing different bytes is rejected. Do not
change the loader filename, expected size, or payload assertions merely to bypass
that check. A different runtime build needs a separately reviewed version.

The current tool port has not established an exact compiler-version pin on a
fresh Linux host. The Windows validation described below used reference extraction,
not recompilation. Full linked-object verification remains available after an
actual GNU build; a PE-only result does not claim those checks ran.

## Explicit reference-binary mode

When a GNU compile host is unavailable, recover the exact known DLL from a local
copy of the released pack:

```sh
python3 tools/build_native.py --reference-pack /path/to/rdp_v07_singlepack_mc01_naval_test01.pack
python3 tools/verify_native.py --pe-only
```

This only decodes and verifies the native bytes. It is **not a source compilation**.
It writes `native_compiled=false` in the build report, and `--pe-only` reports the
linked-object checks as not performed. This mode is useful for testing pack/Lua
tooling while preserving the already released native binary.

## Generate payload and run Lua tests

```sh
python3 tools/build_pack.py --payload-only
python3 tests/test_loader.py
python3 tests/test_campaign.py
```

Both tests import `tests/lua_host.py`. No old `reference/` source tree is required.
Campaign tests use explicit expectations for general land/naval battles, settlement
mode, contested garrisons, exclusions, event order, export caching and loader errors.

On Windows, for example:

```powershell
$env:RDP_LUA_LIBRARY = 'C:\path\to\lua54.dll'
python tools/build_pack.py --payload-only
python tests/test_loader.py
python tests/test_campaign.py
```

## Supply local campaign inputs and build the pack

Extract the original scripts locally using your pack editor, preserving this
layout. Supply the **campaigns directory itself** as `--campaign-dir`:

```text
/path/to/local-dei/campaigns/
  main_3c/scripting.lua
  main_emperor/scripting.lua
  main_gaul/scripting.lua
  main_greek/scripting.lua
  main_invasion/scripting.lua
  main_punic/scripting.lua
  main_rome/scripting.lua
  prologue_01/scripting.lua
  prologue_02/scripting.lua
```

```sh
python3 tools/build_pack.py --campaign-dir /path/to/local-dei/campaigns
python3 tests/test_build_tools.py
python3 tools/verify_release.py
```

For a reference-binary run, replace the last command with:

```sh
python3 tools/verify_release.py --pe-only
```

Keep local inputs outside `dist/`. Input files are read only. The builder requires
all nine scripts and their recorded hashes, refuses an existing bootstrap, and
appends `integration/dei_bootstrap.lua` without changing the original prefix.
The hashes are in `tools/project.py`; full DEI scripts are not in the repository.
Changed DEI versions are rejected as unverified input and need an explicit
compatibility review. This build is not an automatic DEI-version migration tool.

The resulting pack must have SHA-256:

```text
8aa310977f98120e05facf623f871d44cf7a2f95e1168463c563843dcf466da5
```

Release verification checks all 12 entries, exact original script prefixes, one
bootstrap per campaign, runtime source identity, Lua syntax, and all 10,092 bytes
of the interpreted payload. It writes `dist/SHA256SUMS.txt` after success.

## Outputs and validation scope

```text
build/
  patch.o, patch.obj, imports.obj       # GNU compile mode
  rdp_native_merge_v07.dll
  generated/rdp_v07sp01_payload.lua
  reports/*.json
dist/
  rdp_v07_singlepack_mc01_naval_test01.pack
  SHA256SUMS.txt
```

`build/`, `dist/`, local inputs and Python caches are ignored by Git. Generated
payload is never placed in `src/lua/`. `.gitattributes` enforces LF for the source
files whose bytes are checked, including Windows checkouts.

The publication port was tested with the exact reference DLL on Windows, a
separate official Lua 5.4.7 x64 test library, and local recorded campaign inputs.
The recreated pack was byte-for-byte identical to the release. These checks do
not establish a new game test, a native recompilation result, or support for other
engine/DEI versions. The earlier user game-success report remains a baseline report.

These commands do not install the mod, run the game, commit, or push to GitHub.
