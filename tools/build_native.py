"""Compile the unchanged freestanding x86 DLL, or explicitly recover the reference binary."""
import argparse
import json
import shutil
import subprocess
from project import ROOT, BUILD, DLL, DLL_SHA, check_dll, check_sources, decode_payload, sha, write_report
from build_imports import emit
from elf_to_coff import convert
from pack_io import read_pack


def run(args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='gcc', help='GNU compiler emitting i386 ELF objects')
    parser.add_argument('--ld', default='ld', help='GNU linker with i386pe emulation')
    parser.add_argument('--reference-pack', type=str,
                        help='Recover the exact known DLL from a local release pack; NOT recompilation')
    args = parser.parse_args()
    check_sources()
    BUILD.mkdir(exist_ok=True)
    if args.reference_pack:
        from pathlib import Path
        source = Path(args.reference_pack).resolve()
        if source == DLL.resolve() or (DLL.exists() and source.samefile(DLL)):
            parser.error('Reference pack cannot be the output DLL.')
        raw = source.read_bytes()
        entries = read_pack(raw)
        native = decode_payload(entries['lua_scripts\\rdp_v07sp01_payload.lua'])
        check_dll(native)
        DLL.write_bytes(native)
        report = dict(mode='reference_extraction', native_compiled=False,
                      reference_pack_sha256=sha(raw), sha256=sha(native), size=len(native),
                      game_executed=False, native_dll_executed=False)
    else:
        cc, ld = shutil.which(args.cc), shutil.which(args.ld)
        if not cc or not ld:
            parser.error('GNU gcc/ld are required. See docs/build.md; WSL/Linux is the supported compile host.')
        versions = {name: subprocess.check_output([exe, '--version'], text=True).splitlines()[0]
                    for name, exe in (('cc', cc), ('ld', ld))}
        flags = ['-m32','-Os','-ffreestanding','-fno-pic','-fno-pie','-fno-stack-protector',
                 '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-ident','-fno-builtin',
                 '-mno-sse','-mno-sse2','-mincoming-stack-boundary=2','-mpreferred-stack-boundary=2',
                 '-Wall','-Wextra','-Werror']
        run([cc, *flags, '-c', ROOT/'src/native/patch.c', '-o', BUILD/'patch.o'])
        convert(BUILD/'patch.o', BUILD/'patch.obj')
        emit(BUILD/'imports.obj')
        stage = BUILD/'native-stage'
        stage.mkdir(exist_ok=True)
        candidate = stage/DLL.name
        run([ld,'-mi386pe','--dll','--entry','_DllMain','--image-base','0x62000000',
             '--dynamicbase','--nxcompat','--no-insert-timestamp','--subsystem','windows',
             '-o',candidate,BUILD/'patch.obj',BUILD/'imports.obj',ROOT/'src/native/patch.def'])
        native = check_dll(candidate.read_bytes())
        DLL.write_bytes(native)
        report = dict(mode='compiled', native_compiled=True, tool_versions=versions,
                      compiler_flags=flags, sha256=sha(native), size=len(native),
                      game_executed=False, native_dll_executed=False)
    assert sha(DLL.read_bytes()) == DLL_SHA
    write_report('native_build.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
