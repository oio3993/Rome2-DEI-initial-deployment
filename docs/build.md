# Build and test

The target is a Windows x86 DLL. Native compilation uses GCC on Linux or WSL to
produce i386 ELF objects, the Python ELF-to-COFF converter, and GNU ld with
`i386pe` emulation. Run the commands below from the repository root.

## Dependencies

- Python 3.10 or newer.
- GCC with `-m32` support and GNU ld with `i386pe` support.
- A Lua 5.4 shared library for tests. Linux defaults to `liblua5.4.so.0`; on
  Windows, set `RDP_LUA_LIBRARY` to a Lua 5.4 DLL matching Python's architecture.
- Matching local DEI campaign scripts for building the final pack.

Tests use a standalone Lua 5.4 host with mocked native exports. The original game
engine DLL is not a build dependency.

## Recompile the DLL

The reproducible toolchain versions are:

- GCC `13.2.0-23ubuntu4` (13.2.0)
- GNU binutils `2.42-4ubuntu2`
- Python 3.12.3 in the pinned Ubuntu environment

```sh
python3 tools/build_native.py
python3 tools/verify_native.py
```

Use `--cc /path/to/gcc --ld /path/to/ld` to select the tools explicitly. The build
records versions and flags in `build/reports/native_build.json`. Native
verification checks the PE imports/exports, entry-point ABI, linked COFF operands
and ASLR fixups, using the corresponding `build/patch.obj`.

The resulting DLL must be 10,092 bytes with SHA-256:

```text
93470fef577ebff54d34b16dfbbf0833ed8454857f11680cbc7095f5f9b81b81
```

A build with different bytes is rejected. A changed native build requires an
explicit version update, including the loader filename/size, payload and expected
hashes. Installing the latest GCC/binutils packages does not pin these versions;
the [CI environment](#continuous-integration) provides the fixed toolchain.

### Optional Windows QEMU wrapper

With a separately prepared portable environment:

```powershell
python tools/build_native_windows.py --env-dir C:\path\to\gnu-build-env
```

The environment directory must contain `base-initramfs.gz`, `vmlinuz` and the
complete extracted QEMU Windows directory at `qemu/`. The launcher checks their
pinned fingerprints, compiles in the guest, then verifies the returned DLL and
objects on Windows. These environment images and executables are not included
in the repository or provisioned by the launcher. For a new build environment,
use the Linux setup under [continuous integration](#continuous-integration).

Reports are written to `build/reports/`, including `windows_gnu_build.json` and
the guest serial log `windows_gnu_serial.log`.

## Generate payload and run Lua tests

```sh
python3 tools/build_pack.py --payload-only
python3 tests/test_loader.py
python3 tests/test_campaign.py
python3 tests/test_build_tools.py
```

The packaging tests use synthetic campaign/pack fixtures and require no DEI
originals or released pack. For the Lua tests on Windows, set the shared library:

```powershell
$env:RDP_LUA_LIBRARY = 'C:\path\to\lua54.dll'
```

## Supply local campaign inputs and build the pack

Extract the matching original DEI scripts with a pack editor, preserving this
layout. Pass the **campaigns directory itself** as `--campaign-dir`:

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
python3 tools/verify_release.py
```

Input files are read only. The builder checks all nine hashes in
`tools/project.py`, rejects an existing bootstrap, and appends
`integration/dei_bootstrap.lua`. Keep local inputs outside `dist/`. Full DEI
scripts are not included in the repository; changed inputs require a compatibility
review.

The resulting pack must have SHA-256:

```text
8aa310977f98120e05facf623f871d44cf7a2f95e1168463c563843dcf466da5
```

Release verification checks all 12 entries, original script prefixes, bootstrap
insertion, runtime source identity, Lua syntax, the interpreted payload and native
linked objects. It writes `dist/SHA256SUMS.txt` after success.

## Recover the DLL from an existing pack

For a pack-only rebuild without a GNU compiler:

```sh
python3 tools/build_native.py --reference-pack /path/to/rdp_v07_singlepack_mc01_naval_test01.pack
python3 tools/verify_native.py --pe-only
```

This extracts the known DLL rather than compiling C. The report records
`native_compiled=false`. After rebuilding the pack, use
`python3 tools/verify_release.py --pe-only`; that mode omits linked-object checks.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes, pull requests and manual dispatch.
It prepares a pinned Ubuntu build root using
`.github/ci/ubuntu-24.04.json`: Ubuntu Base and 64 packages, including the fixed
GCC/binutils versions and a Lua 5.4.6 shared library. Downloads are checked against
their SHA-256 hashes before extraction. The workflow pins GitHub actions to
commit hashes and uses read-only repository permissions.

The pipeline compiles and verifies the DLL, generates the payload, and runs
loader, campaign and packaging tests. On a Linux host with the required GNU tools
and Lua library already installed, run it directly:

```sh
python3 tools/run_ci.py
```

To reproduce the isolated environment on an x86_64 Linux host with `tar` and
`dpkg-deb`, use a new, nonexistent root directory:

```sh
python3 tools/prepare_ci_environment.py --root /tmp/rdp-ci-root
sudo mknod -m 666 /tmp/rdp-ci-root/dev/null c 1 3
sudo chroot /tmp/rdp-ci-root /usr/bin/env LC_ALL=C.UTF-8 /usr/bin/python3 /work/repo/tools/run_ci.py
```

The bootstrap copies `src/`, `tools/`, `tests/` and `integration/` into that root.
Outputs are under `/tmp/rdp-ci-root/work/repo/build/`. GitHub collects the DLL and
JSON reports as a 14-day artifact, available from the repository's Actions tab.

CI does not require DEI inputs or generate a player pack. Final pack verification
uses the local DEI input commands above. Pipeline results are recorded in
`build/reports/ci_validation.json`.

## Outputs

```text
build/
  patch.o, patch.obj, imports.obj
  rdp_native_merge_v07.dll
  generated/rdp_v07sp01_payload.lua
  reports/*.json
dist/
  rdp_v07_singlepack_mc01_naval_test01.pack
  SHA256SUMS.txt
```

`build/`, `dist/`, local inputs and Python caches are ignored by Git. Generated
payload stays under `build/generated/`. `.gitattributes` enforces LF for the source
files whose bytes are checked, including Windows checkouts.
