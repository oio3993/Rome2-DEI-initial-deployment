"""Check the NavalNormal baseline policy with explicit expected native calls."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from project import ROOT, check_sources, write_report
from lua_host import run, HOST_RUNTIME

check_sources()
source = (ROOT/'src/lua/rdp_v07sp01_campaign.lua').read_text(encoding='utf-8')
setup = r'''
local calls,events,removed,loads={},{},{},{}
local prepared=0
local cfg={typ='land_normal',mp=false,ah=true,dh=false,att=true,def=true,contested=false,active=false}
local loader={prepare=function()prepared=prepared+1;return not cfg.prepare_fail end,
load=function(symbol)
    assert(symbol=='rdp_install' or symbol=='rdp_install_settlement' or symbol=='rdp_disable')
    loads[symbol]=(loads[symbol] or 0)+1
    if cfg.load_throw then error('loader failure')end
    if cfg.load_nil then return nil end
    return function()calls[#calls+1]=symbol end
end}
local pb={is_active=function()return cfg.active end,
battle_type=function()if cfg.pb_throw then error('pending unavailable')end;return cfg.typ end,
has_attacker=function()return cfg.att end,has_defender=function()return cfg.def end,
has_contested_garrison=function()return cfg.contested end,
attacker=function()assert(cfg.att);return {faction=function()return {is_human=function()return cfg.ah end}end}end,
defender=function()assert(cfg.def);return {faction=function()return {is_human=function()return cfg.dh end}end}end}
local model={is_multiplayer=function()return cfg.mp end,pending_battle=function()return pb end}
local scripting={game_interface={model=function()return model end,
remove_custom_battlefield=function(self,key)removed[key]=true;if cfg.cleanup_throw then error('cleanup failed')end end},
AddEventCallBack=function(name,fn)assert(not events[name]);events[name]=fn end}
require=function(name)
    if name=='lua_scripts.EpisodicScripting' then return scripting end
    assert(name=='lua_scripts.rdp_v07sp01_loader');return loader
end
'''
cases = []


def case(name, before, action, expected):
    code = setup + '\n' + before + '\nassert((function()\n' + source + '\nend)())\n'
    code += "assert(prepared==1);local n=0;for _ in pairs(events)do n=n+1 end;assert(n==3)\n"
    code += action + '\nassert(table.concat(calls,",")==' + json.dumps(expected) + ')\n'
    code += "assert(removed.rdp_v03_native_observe and removed.rdp_v04_native_merge and removed.rdp_v05_native_merge)\n"
    code += 'for _,count in pairs(loads)do assert(count==1)end\n'
    run(name, code)
    cases.append(name)


pending = 'events.PendingBattle({pending_battle=function()return pb end})'
for typ, mode in [('land_normal', 'rdp_install'), ('naval_normal', 'rdp_install'),
                  ('settlement_standard', 'rdp_install_settlement'),
                  ('settlement_unfortified', 'rdp_install_settlement'), ('town_normal', 'rdp_install_settlement')]:
    for human in ('attacker', 'defender'):
        before = "cfg.typ='" + typ + "';cfg.ah=" + str(human=='attacker').lower() + ';cfg.dh=' + str(human=='defender').lower()
        case(typ+'_'+human, before, pending, 'rdp_disable,'+mode)
case('contested_field', 'cfg.contested=true', pending, 'rdp_disable,rdp_install_settlement')
case('naval_contested_keeps_normal', "cfg.typ='naval_normal';cfg.contested=true", pending, 'rdp_disable,rdp_install')
for name, before in [('multiplayer', 'cfg.mp=true'), ('ai_only', 'cfg.ah=false'),
                     ('missing_attacker', 'cfg.att=false'), ('missing_defender', 'cfg.def=false')]:
    case(name, before, pending, 'rdp_disable')
for typ in ('naval_blockade','naval_breakout','port_assault','coastal_battle','settlement_sally','settlement_relief','fort_standard'):
    case('excluded_'+typ, "cfg.typ='"+typ+"'", pending, 'rdp_disable')
case('ui_without_pending', '', 'events.UICreated()', 'rdp_disable')
case('ui_active_naval', "cfg.typ='naval_normal';cfg.active=true", 'events.UICreated()', 'rdp_disable,rdp_disable,rdp_install')
case('ui_active_settlement', "cfg.typ='settlement_standard';cfg.active=true", 'events.UICreated()', 'rdp_disable,rdp_disable,rdp_install_settlement')
case('battle_completed', '', 'events.BattleCompleted()', 'rdp_disable')
case('cleanup_failure_contained', 'cfg.cleanup_throw=true', pending, 'rdp_disable,rdp_install')
case('pending_api_failure_contained', 'cfg.pb_throw=true', pending, 'rdp_disable')
for field in ('load_nil', 'load_throw'):
    case(field, 'cfg.'+field+'=true', pending, '')
case('prepare_failure_retried_by_calls', 'cfg.prepare_fail=true', pending, 'rdp_disable,rdp_install')
case('callback_sequence_and_cached_exports', '', pending+';events.UICreated();cfg.active=true;events.UICreated();events.BattleCompleted()',
     'rdp_disable,rdp_install,rdp_disable,rdp_disable,rdp_disable,rdp_install,rdp_disable')
result = dict(passed=True, test_count=len(cases), tests=cases, baseline='NavalNormal Test01',
              old_campaign_reference_required=False, native_exports_mocked=True,
              host_runtime=HOST_RUNTIME, game_runtime_executed=False)
write_report('campaign_tests.json', result)
print(json.dumps({key:value for key,value in result.items() if key!='tests'}, indent=2))
