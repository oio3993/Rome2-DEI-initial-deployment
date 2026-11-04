"""Verify exact runtime sources, native payload, DEI prefixes and the final PFH4 pack."""
import argparse
import json
from pathlib import Path
import sys
from project import (ROOT, DLL, PAYLOAD, DIST, PACK_NAME, PACK_SHA, DLL_SHA, CAMPAIGN_SHA,
                     BOOTSTRAP, check_sources, check_dll, decode_payload, make_payload,
                     sha, require, write_report)
from pack_io import read_pack
from verify_native import verify as verify_native


def verify_pack(raw, native):
    check_sources()
    check_dll(native)
    entries = read_pack(raw)
    campaign_names = {'campaigns\\'+name+'\\scripting.lua' for name in CAMPAIGN_SHA}
    runtime_names = {'lua_scripts\\'+name for name in
                     ('rdp_v07sp01_campaign.lua','rdp_v07sp01_loader.lua','rdp_v07sp01_payload.lua')}
    require(set(entries) == campaign_names | runtime_names, 'Unexpected pack entries.')
    for name, digest in CAMPAIGN_SHA.items():
        content = entries['campaigns\\'+name+'\\scripting.lua']
        require(content.endswith(BOOTSTRAP), 'Missing bootstrap: '+name)
        original = content[:-len(BOOTSTRAP)]
        require(sha(original) == digest, 'DEI prefix differs: '+name)
        require(b'lua_scripts.rdp_v07sp01_campaign' not in original, 'Duplicate bootstrap: '+name)
    for name in ('rdp_v07sp01_campaign.lua','rdp_v07sp01_loader.lua'):
        require(entries['lua_scripts\\'+name] == (ROOT/'src/lua'/name).read_bytes(), 'Runtime source differs: '+name)
    payload = entries['lua_scripts\\rdp_v07sp01_payload.lua']
    require(payload == make_payload(native), 'Packed payload differs from the DLL.')
    require(decode_payload(payload) == native, 'Payload roundtrip differs.')
    require(sha(raw) == PACK_SHA, 'Pack is not the exact NavalNormal Test01 release.')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=DIST/PACK_NAME)
    parser.add_argument('--pe-only', action='store_true', help='Explicit reference-binary mode; linked-object checks are not performed')
    args = parser.parse_args()
    native_report = verify_native(args.pe_only)
    native = check_dll(DLL.read_bytes())
    require(PAYLOAD.read_bytes() == make_payload(native), 'Generated payload is missing or stale.')
    raw = args.pack.read_bytes()
    entries = verify_pack(raw, native)
    sys.path.insert(0,str(ROOT/'tests'))
    from lua_host import run, HOST_RUNTIME
    for name, data in entries.items():
        run('syntax_'+name, data.decode('utf-8'), syntax_only=True)
    payload = entries['lua_scripts\\rdp_v07sp01_payload.lua'].decode('ascii')
    code = 'local raw=(function()\n'+payload+'\nend)();assert(#raw=='+str(len(native))+')\n'
    code += 'local out={};for i=1,#raw do out[i]=string.format("%02x",string.byte(raw,i))end\n'
    code += 'assert(table.concat(out)=="'+native.hex()+'")\n'
    run('actual_interpreted_payload_roundtrip',code)
    report = dict(passed=True, pack_file=args.pack.name, pack_sha256=sha(raw), entry_count=len(entries),
                  campaign_count=len(CAMPAIGN_SHA), native_sha256=DLL_SHA, native_size=len(native),
                  native_linked_checks_performed=native_report['linked_operands_checked'],
                  generated_and_packed_payload_identical=True, interpreted_payload_roundtrip=True,
                  original_prefixes_and_sources_identical=True, exact_baseline_pack=True,
                  syntax_checked=len(entries), host_runtime=HOST_RUNTIME,
                  game_lua_5_1_executed=False, game_executed=False, mod_dll_executed=False)
    report['checksum_written'] = args.pack.resolve().parent == DIST.resolve()
    if report['checksum_written']:
        checksum = sha(raw)+'  '+args.pack.name+'\n'
        (DIST/'SHA256SUMS.txt').write_text(checksum,encoding='ascii',newline='\n')
    write_report('release_validation.json',report)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
