"""Preserve the baseline PE/ABI/COFF relocation checks without loading the DLL."""
import argparse
import hashlib
import json
import struct
from build_imports import APIS
from project import ROOT as root, DLL, check_dll, check_sources, write_report, require

def verify(pe_only=False):
    check_sources()
    require(pe_only or (root/'build/patch.obj').is_file(),
            'Linked checks require a compiled build/patch.obj. Use --pe-only explicitly for reference extraction.')
    def get32(d,o):return struct.unpack_from('<I',d,o)[0]
    def name(d,o):return d[o:d.index(b'\0',o)].decode()
    def coff(d,header=0,section_headers=None,base=0):
        nsec=struct.unpack_from('<H',d,header+2)[0]
        symoff,nsyms=struct.unpack_from('<II',d,header+8)
        sh=section_headers if section_headers is not None else header+20
        sections=[]
        for i in range(nsec):
            off=sh+i*40
            sections.append(dict(name=d[off:off+8].split(b'\0')[0].decode(),
                va=base+get32(d,off+12),size=get32(d,off+16),raw=get32(d,off+20),
                rel=get32(d,off+24),nrel=struct.unpack_from('<H',d,off+32)[0]))
        strings=symoff+nsyms*18;symbols={};byname={};i=0
        while i<nsyms:
            o=symoff+i*18;raw=d[o:o+8]
            s=name(d,strings+get32(raw,4)) if raw[:4]==b'\0'*4 else raw.split(b'\0')[0].decode()
            value,sec,typ,storage,aux=struct.unpack_from('<IhHBB',d,o+8)
            v=dict(name=s,value=value,section=sec)
            if sec>0:v['va']=sections[sec-1]['va']+value
            elif sec==-1:v['va']=value
            symbols[i]=v;byname[s]=v;i+=1+aux
        return sections,symbols,byname
    
    p=check_dll(DLL.read_bytes())
    assert p[:2]==b'MZ';nt=get32(p,0x3c);assert p[nt:nt+4]==b'PE\0\0'
    header=nt+4;opt=nt+24;base=get32(p,opt+28)
    assert struct.unpack_from('<H',p,header)[0]==0x14c
    assert struct.unpack_from('<H',p,opt)[0]==0x10b
    assert struct.unpack_from('<H',p,header+18)[0]&0x2000
    assert struct.unpack_from('<H',p,opt+70)[0]&0x140==0x140
    sections,syms,byname=coff(p,header,opt+struct.unpack_from('<H',p,header+16)[0],base)
    def raw(va):
        s=next(s for s in sections if s['va']<=va<s['va']+s['size'])
        return s['raw']+va-s['va']
    def q(va):return get32(p,raw(va))
    def text(va):return name(p,raw(va))
    
    iat={};imports={};o=raw(base+get32(p,opt+104))
    while get32(p,o+12):
        ilt,_,_,dn,thunk=struct.unpack_from('<5I',p,o);dll=text(base+dn);items=[];i=0
        while q(base+ilt+4*i):
            fn=text(base+q(base+ilt+4*i)+2);items.append(fn);iat[fn]=base+thunk+4*i;i+=1
        imports[dll]=items;o+=20
    assert imports==APIS,(imports,APIS)
    for api,va in iat.items():assert byname['_p'+api]['va']==va
    for forbidden in ['WriteProcessMemory','CreateRemoteThread','WriteFile','FlushFileBuffers','GetTickCount','GetCurrentThreadId']:
        assert forbidden not in iat
    
    export=base+get32(p,opt+96);count=q(export+24);fns=q(export+28);names=q(export+32);ords=q(export+36)
    exports={}
    for i in range(count):
        n=text(base+q(base+names+4*i));ix=struct.unpack_from('<H',p,raw(base+ords+2*i))[0]
        exports[n]=base+q(base+fns+4*ix)
    assert set(exports)=={'rdp_install','rdp_install_settlement','rdp_disable'}
    for n,a in exports.items():assert a==byname['_'+n]['va']
    entry=base+get32(p,opt+16)
    assert p[raw(entry):raw(entry)+8]==bytes.fromhex('b8 01 00 00 00 c2 0c 00')
    
    fixups = None
    if not pe_only:
        # Independent arithmetic check of each linked absolute/relative operand.
        obj=(root/'build/patch.obj').read_bytes();osec,osym,_=coff(obj)
        absolute=[];fixups=0
        for s in osec:
            if not s['nrel']:continue
            dest=next(x['va'] for x in sections if x['name']==s['name']) if s['name']=='.text' else byname[s['name']]['va']
            for i in range(s['nrel']):
                offset,si,typ=struct.unpack_from('<IIH',obj,s['rel']+10*i)
                target=byname[osym[si]['name']]['va'];loc=dest+offset
                add=get32(obj,s['raw']+offset)
                if typ==6:expected=(target+add)&0xffffffff;absolute.append(loc-base)
                elif typ==0x14:expected=(target+add-loc-4)&0xffffffff
                else:raise AssertionError(typ)
                assert q(loc)==expected,(s['name'],hex(offset),osym[si]['name'],hex(q(loc)),hex(expected))
                fixups+=1
        reloc=base+get32(p,opt+136);end=reloc+get32(p,opt+140);sites=set()
        while reloc<end:
            page,size=q(reloc),q(reloc+4);assert size>=8
            for o in range(8,size,2):
                item=struct.unpack_from('<H',p,raw(reloc+o))[0]
                if item>>12==3:sites.add(page+(item&4095))
                else:assert item>>12==0
            reloc+=size
        assert set(absolute)<=sites
    report=dict(passed=True,pe32_x86=True,exports=list(exports),imports=imports,linked_operand_checks=fixups,
        linked_operands_checked=not pe_only,all_linked_operands_match=True if not pe_only else None,all_absolute_operands_have_aslr_fixups=True if not pe_only else None,
        dllmain_stdcall_return_verified=True,runtime_code_patching=True,no_log_output_imports=True,
        sha256=hashlib.sha256(p).hexdigest(),windows_loader_executed=False,game_executed=False)
    write_report('native_validation.json', report)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pe-only',action='store_true',help='Explicitly skip linked-object checks for a recovered reference DLL')
    args=parser.parse_args()
    print(json.dumps(verify(args.pe_only),indent=2))

if __name__=='__main__':
    main()
