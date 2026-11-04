"""Paths and fingerprints for the unchanged NavalNormal Test01 release."""
from pathlib import Path
import hashlib
import json
import re

if not __debug__:
    raise RuntimeError('Run the verification tools without Python -O.')

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
REPORTS = BUILD / 'reports'
GENERATED = BUILD / 'generated'
DIST = ROOT / 'dist'
DLL = BUILD / 'rdp_native_merge_v07.dll'
PAYLOAD = GENERATED / 'rdp_v07sp01_payload.lua'
PACK_NAME = 'rdp_v07_singlepack_mc01_naval_test01.pack'
DLL_SHA = '93470fef577ebff54d34b16dfbbf0833ed8454857f11680cbc7095f5f9b81b81'
DLL_SIZE = 10092
PACK_SHA = '8aa310977f98120e05facf623f871d44cf7a2f95e1168463c563843dcf466da5'
BOOTSTRAP = b'\n-- V07 single-pack runtime\nrequire "lua_scripts.rdp_v07sp01_campaign";\n'
SOURCE_SHA = {
    'src/native/patch.c': '90158b0887590b0d6b47103bde2b935121008c64ee9ae3f475dcbd404a5db4dd',
    'src/native/patch_bytes.h': '82e94c9fb44c6c02efd80bd63f0a3e3bd3c2146773dc00946dc227df78e9732d',
    'src/native/patch.def': 'f72635851de4842ef1b83af4cc52400c1cf36351569121728c3af2d250954aa5',
    'src/lua/rdp_v07sp01_campaign.lua': 'c6e7d820a93a5fae0ebcd1a4ea372e08892e62f8d681079b2e35e63abf52a99a',
    'src/lua/rdp_v07sp01_loader.lua': 'caeea13c54d384ef01cce8ea4bafe6f624cda475659177993ccd8bf0ea415d3b',
}
CAMPAIGN_SHA = {
    'main_3c': '0841007a67acda50fc265be2282432bbe526dffc6021ab7faeda48f3b7a3b9be',
    'main_emperor': '83e7c6760f0e91783ce31a65defe9236b79b3f700f9e666e4d49c1744074fdb0',
    'main_gaul': 'a8a9a4b1fb1eb947694141b3a7125e67b76783d965212ab98dad22934a7b3255',
    'main_greek': '2a267b4213516e2e59f95d07a78c5b37d51c64d96a93ff3d355afd6cbaa2beca',
    'main_invasion': '2050de995a7a77038ecd74c584c8ff25a7d2ccaa5c60d3959043071cb13a5cb3',
    'main_punic': '4d2716a2a2dba02e9dd5620aa17782aab819a21c1e52792cafde48c1eb4756fd',
    'main_rome': '1c2d47bc57c0d261a172266a5c1d5805f2925799163bcfee9bf2537a525c5911',
    'prologue_01': 'b94785440b0e3476ba648a624adde6342188bac70ba2ebdebead914462b9062e',
    'prologue_02': 'a027dc0c6f6a1c687fee9a586b8ef58fd27157571453562426c67ad5786ed770',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_report(name, report):
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')


def check_sources():
    for name, digest in SOURCE_SHA.items():
        require(sha((ROOT / name).read_bytes()) == digest,
                'Baseline source differs: ' + name + '. Review a version change explicitly.')
    require((ROOT / 'integration/dei_bootstrap.lua').read_bytes() == BOOTSTRAP,
            'Bootstrap differs from the supported release.')


def check_dll(raw):
    require(len(raw) == DLL_SIZE and sha(raw) == DLL_SHA,
            'DLL does not match NavalNormal Test01. Do not update the loader silently.')
    return raw


def make_payload(raw):
    check_dll(raw)
    chunks = ['    "' + ''.join('\\' + f'{byte:03d}' for byte in raw[i:i+128]) + '"'
              for i in range(0, len(raw), 128)]
    return ('-- Generated DLL bytes, not encryption. SHA256: ' + DLL_SHA +
            '\nreturn table.concat({\n' + ',\n'.join(chunks) + '\n})\n').encode('ascii')


def decode_payload(raw):
    numbers = re.findall(rb'\\([0-9]{3})', raw)
    require(all(int(value) <= 255 for value in numbers), 'Invalid payload byte.')
    native = check_dll(bytes(int(value) for value in numbers))
    require(raw == make_payload(native), 'Payload is not the exact generated module.')
    return native
