"""Run public-source checks without an engine, DEI inputs, or a released pack."""
import json
import subprocess
import sys

from project import ROOT, DLL, PAYLOAD, check_sources, check_dll, make_payload, require, write_report

STEPS = (
    'tools/build_native.py',
    'tools/verify_native.py',
    'tools/build_pack.py --payload-only',
    'tests/test_loader.py',
    'tests/test_campaign.py',
    'tests/test_build_tools.py',
)


def main():
    check_sources()
    completed = []
    for step in STEPS:
        print('CI: '+step, flush=True)
        result = subprocess.run([sys.executable, *step.split()], cwd=ROOT)
        completed.append(dict(command=step, exit_code=result.returncode))
        if result.returncode:
            write_report('ci_validation.json', dict(passed=False, steps=completed,
                         release_pack_verified=False, game_executed=False))
            raise SystemExit(result.returncode)
    reports = {name:json.loads((ROOT/'build/reports'/name).read_text()) for name in (
        'native_build.json','native_validation.json','loader_tests.json',
        'campaign_tests.json','build_tools_tests.json')}
    require(reports['native_build.json']['native_compiled'] is True, 'CI must compile from C.')
    require(reports['native_validation.json']['linked_operands_checked'] is True,
            'CI must perform full linked-object verification.')
    require(all(report['passed'] is True for name,report in reports.items() if name != 'native_build.json'),
            'A verification report failed.')
    check_sources()
    native = check_dll(DLL.read_bytes())
    require(PAYLOAD.read_bytes() == make_payload(native), 'Generated payload is stale.')
    report = dict(passed=True, steps=completed,
        native_compiled=True, native_sha256=reports['native_build.json']['sha256'],
        native_size=len(native), tool_versions=reports['native_build.json']['tool_versions'],
        linked_operand_checks=reports['native_validation.json']['linked_operand_checks'],
        loader_tests=reports['loader_tests.json']['test_count'],
        campaign_tests=reports['campaign_tests.json']['test_count'],
        packaging_tests=reports['build_tools_tests.json']['test_count'],
        game_inputs_used=False, release_pack_verified=False,
        game_executed=False, mod_dll_executed=False)
    write_report('ci_validation.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
