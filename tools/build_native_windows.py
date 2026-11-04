"""Recompile with a prepared, pinned GNU environment using QEMU on Windows."""
import argparse
import base64
import gzip
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile

from project import ROOT, BUILD, REPORTS, check_sources, check_dll, require, sha, write_report

# Fingerprints of the tested Ubuntu 24.04 environment. These are build-host
# inputs, not game files. Keep the environment outside the source repository.
ENVIRONMENT_FILES = {
    'base-initramfs.gz': 'd166810c048579143dfb7f0b64358306150d55d469245bd6aef95e2e2a46d5a3',
    'vmlinuz': 'cee36e261749483e951c8229eb1aeeb768af6c28f493421a52b3916885ce913f',
    'qemu/qemu-system-x86_64.exe': '47d57a6072e0bb3bd98f87926eb129eb1736dfe818c67b3b81ef7ce4edd0b3cd',
}
OUTPUTS = (
    'build/patch.o', 'build/patch.obj', 'build/imports.obj',
    'build/native-stage/rdp_native_merge_v07.dll',
    'build/rdp_native_merge_v07.dll',
    'build/reports/native_build.json', 'build/reports/native_validation.json',
)


def write_overlay(path):
    entries = {}

    def put(name, data, mode=stat.S_IFREG | 0o644):
        for parent in reversed(PurePosixPath(name).parents):
            if str(parent) != '.':
                entries.setdefault(str(parent), (stat.S_IFDIR | 0o755, b''))
        entries[name] = (mode, data)

    inputs = list((ROOT/'src').rglob('*')) + list((ROOT/'tools').glob('*.py'))
    inputs.append(ROOT/'integration/dei_bootstrap.lua')
    for item in inputs:
        if item.is_file():
            put('work/repo/'+item.relative_to(ROOT).as_posix(), item.read_bytes())
    exporter = ('from pathlib import Path\nimport base64,json\n'
                'root=Path("/work/repo")\n'
                'for name in '+repr(OUTPUTS)+':\n'
                ' p=root/name\n'
                ' if p.is_file():print("RDP_FILE "+json.dumps({"name":name,"base64":'
                'base64.b64encode(p.read_bytes()).decode()}),flush=True)\n')
    put('work/export.py', exporter.encode('ascii'))
    init = '''#!/busybox sh
/busybox mount -t proc proc /proc
/busybox mount -t sysfs sysfs /sys
/busybox mount -t devtmpfs devtmpfs /dev
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=C.UTF-8
cd /work/repo
python3 tools/build_native.py
build_rc=$?
echo RDP_COMPILE_EXIT=$build_rc
if [ "$build_rc" = 0 ]; then
 python3 tools/verify_native.py
 verify_rc=$?
else
 verify_rc=99
fi
echo RDP_VERIFY_EXIT=$verify_rc
python3 /work/export.py
echo RDP_VM_DONE
/busybox poweroff -f
'''
    put('init', init.encode('ascii'), stat.S_IFREG | 0o755)
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as out:
            for index, (name, (mode, data)) in enumerate(
                    sorted(entries.items())+[('TRAILER!!!', (0, b''))], 1):
                filename = name.encode('utf-8')+b'\0'
                fields = [index, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(filename), 0]
                header = b'070701'+''.join(f'{value:08x}' for value in fields).encode('ascii')
                out.write(header+filename+b'\0'*((-(len(header)+len(filename))) % 4))
                out.write(data+b'\0'*((-len(data)) % 4))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-dir', type=Path, required=True,
                        help='Prepared environment directory; see docs/build.md')
    args = parser.parse_args()
    require(os.name == 'nt', 'Use build_native.py directly on Linux.')
    check_sources()
    env_dir = args.env_dir.resolve()
    for name, expected in ENVIRONMENT_FILES.items():
        item = env_dir/name
        require(item.is_file() and sha(item.read_bytes()) == expected,
                'Missing or different pinned environment file: '+name)
    BUILD.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    log_path = REPORTS/'windows_gnu_serial.log'
    with tempfile.TemporaryDirectory(prefix='gnu-vm-', dir=BUILD) as temporary:
        temporary = Path(temporary)
        overlay = temporary/'overlay.gz'
        write_overlay(overlay)
        initrd = temporary/'initrd.gz'
        with initrd.open('wb') as out:
            for source in (env_dir/'base-initramfs.gz', overlay):
                with source.open('rb') as stream:
                    shutil.copyfileobj(stream, out)
        command = [str(env_dir/'qemu/qemu-system-x86_64.exe'),
                   '-machine','q35','-accel','tcg,thread=multi','-cpu','max',
                   '-m','2048','-smp','2','-kernel',str(env_dir/'vmlinuz'),
                   '-initrd',str(initrd),'-append','console=ttyS0 rdinit=/init panic=1 quiet loglevel=0',
                   '-display','none','-serial','stdio','-monitor','none','-nic','none','-no-reboot']
        with log_path.open('wb') as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
    serial = log_path.read_text(encoding='utf-8', errors='replace')
    lines = serial.splitlines()
    require(process.returncode == 0 and all(lines.count(marker) == 1 for marker in
            ('RDP_COMPILE_EXIT=0','RDP_VERIFY_EXIT=0','RDP_VM_DONE')),
            'GNU compilation/verification failed; inspect '+str(log_path))
    recovered = {}
    for line in lines:
        if line.startswith('RDP_FILE '):
            item = json.loads(line[9:])
            name = item['name']
            require(name in OUTPUTS and name not in recovered, 'Invalid guest output name.')
            recovered[name] = base64.b64decode(item['base64'], validate=True)
    require(set(recovered) == set(OUTPUTS), 'Incomplete guest build output.')
    native = check_dll(recovered['build/rdp_native_merge_v07.dll'])
    require(recovered['build/native-stage/rdp_native_merge_v07.dll'] == native,
            'Candidate and accepted DLL differ.')
    report = json.loads(recovered['build/reports/native_build.json'])
    validation = json.loads(recovered['build/reports/native_validation.json'])
    require(report['native_compiled'] is True and validation['passed'] is True and
            validation['linked_operands_checked'] is True, 'Incomplete guest verification.')
    check_sources()
    for name, data in recovered.items():
        destination = ROOT/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    from verify_native import verify
    verification = verify()  # Recheck exported object and DLL together on Windows.
    write_report('native_validation.json', verification)
    write_report('windows_gnu_build.json', dict(
        passed=True, native_compiled=True, environment_sha256=ENVIRONMENT_FILES,
        tool_versions=report['tool_versions'], native_sha256=sha(native),
        native_size=len(native), linked_operand_checks=verification['linked_operand_checks'],
        guest_network_enabled=False, guest_host_disk_mounts=False,
        game_executed=False, native_dll_executed=False))
    print('Compiled from C; exact baseline DLL; '+str(verification['linked_operand_checks'])+
          ' linked operand checks passed. Reports: '+str(REPORTS))


if __name__ == '__main__':
    main()
