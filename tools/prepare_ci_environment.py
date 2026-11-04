"""Prepare the pinned Ubuntu amd64 build root used by CI; no game inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

from project import ROOT, BUILD, require, sha, write_report


def download(record, cache):
    path = cache/record['file']
    if not path.exists():
        request = urllib.request.Request(record['url'], headers={'User-Agent': 'Rome2-CI/1.0'})
        temporary = path.with_suffix(path.suffix+'.part')
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as out:
            shutil.copyfileobj(response, out)
        require(sha(temporary.read_bytes()) == record['sha256'], 'Download hash differs: '+path.name)
        temporary.replace(path)
    require(sha(path.read_bytes()) == record['sha256'], 'Cached input hash differs: '+path.name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='New, nonexistent build-root directory')
    parser.add_argument('--cache', type=Path, default=BUILD/'ci-downloads')
    args = parser.parse_args()
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64',
            'CI bootstrap requires an x86_64 Linux host with tar and dpkg-deb.')
    root = args.root.resolve()
    require(not root.exists() and not ROOT.is_relative_to(root),
            'Build root must be a new directory and cannot contain the source checkout.')
    manifest = json.loads((ROOT/'.github/ci/ubuntu-24.04.json').read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    inputs = [manifest['ubuntu_base'], *manifest['packages'].values()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(lambda record: download(record, args.cache), inputs))
    root.mkdir(parents=True)
    subprocess.run(['tar','--extract','--gzip','--file',str(archives[0]),
                    '--directory',str(root),'--no-same-owner'], check=True)
    for archive in archives[1:]:
        subprocess.run(['dpkg-deb','--extract',str(archive),str(root)], check=True)
    gcc = root/'usr/bin/gcc'
    require(not gcc.exists() and not gcc.is_symlink(), 'Unexpected default compiler in build root.')
    gcc.symlink_to('gcc-13')
    destination = root/'work/repo'
    destination.mkdir(parents=True)
    for name in ('src','tools','tests','integration'):
        shutil.copytree(ROOT/name, destination/name, ignore=shutil.ignore_patterns('__pycache__'))
    write_report('ci_environment.json', dict(
        passed=True, ubuntu_base_sha256=manifest['ubuntu_base']['sha256'],
        package_count=len(manifest['packages']),
        package_versions={name:item['version'] for name,item in manifest['packages'].items()},
        all_download_hashes_verified=True, game_inputs_used=False))
    print('Prepared pinned GNU/Lua build root with '+str(len(manifest['packages']))+' verified packages.')


if __name__ == '__main__':
    main()
