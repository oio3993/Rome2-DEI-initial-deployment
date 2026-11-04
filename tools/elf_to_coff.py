"""Translate this freestanding i386 object's allocated sections and relocations.
Rejects unsupported input. Used because host objcopy does not translate ELF
relocation numbering/symbol indices into valid i386 COFF relocations.
"""
from pathlib import Path
import struct

def convert(src,dst):
    d=Path(src).read_bytes()
    assert d[:5]==b'\x7fELF\x01' and d[5]==1 and struct.unpack_from('<H',d,18)[0]==3
    shoff=struct.unpack_from('<I',d,32)[0]
    shsize,shnum,shstr=struct.unpack_from('<HHH',d,46)
    sh=[struct.unpack_from('<10I',d,shoff+i*shsize) for i in range(shnum)]
    ns=d[sh[shstr][4]:sh[shstr][4]+sh[shstr][5]]
    def cstr(data,offset):return data[offset:data.index(b'\0',offset)].decode()
    selected=[];secmap={};rd=0
    for i,s in enumerate(sh):
        if s[2]&2:
            name=cstr(ns,s[0])
            if name.startswith('.rodata'):name='.rdata$'+str(rd);rd+=1
            assert len(name)<=8
            raw=bytearray(d[s[4]:s[4]+s[5]]) if s[1]!=8 else bytearray()
            flags=(0x60000020 if s[2]&4 else 0xc0000080 if s[1]==8 else 0xc0000040 if s[2]&1 else 0x40000040)
            align=max(1,s[8]);power=align.bit_length()
            flags|=min(power,14)<<20
            secmap[i]=len(selected)+1
            selected.append(dict(name=name,size=s[5],raw=raw,flags=flags,rel=[]))
    symsec=next(s for s in sh if s[1]==2)
    st=d[sh[symsec[6]][4]:sh[symsec[6]][4]+sh[symsec[6]][5]]
    symmap={};symbols=[]
    for i in range(symsec[5]//16):
        name,value,size,info,other,section=struct.unpack_from('<IIIBBH',d,symsec[4]+i*16)
        typ=info&15;binding=info>>4
        if typ==4 or (section not in secmap and section not in [0,0xfff1]):continue
        if typ==3:
            if section not in secmap:continue
            name=selected[secmap[section]-1]['name']
        else:
            if not name:continue
            name='_'+cstr(st,name)
        symmap[i]=len(symbols)
        symbols.append((name,value,secmap.get(section,-1 if section==0xfff1 else 0),0x20 if typ==2 else 0,2 if binding else 3))
    for s in sh:
        if s[1]!=9 or s[7] not in secmap:continue
        target=selected[secmap[s[7]]-1]
        for i in range(s[5]//8):
            offset,info=struct.unpack_from('<II',d,s[4]+i*8)
            typ=info&255;symbol=info>>8
            assert typ in [1,2] and symbol in symmap,(typ,symbol)
            if typ==2:
                value=struct.unpack_from('<I',target['raw'],offset)[0]
                struct.pack_into('<I',target['raw'],offset,(value+4)&0xffffffff)
            target['rel'].append((offset,symmap[symbol],6 if typ==1 else 0x14))
    strings=bytearray(b'\0'*4);syms=bytearray()
    for name,value,sec,typ,storage in symbols:
        name=name.encode()
        if len(name)>8:
            field=struct.pack('<II',0,len(strings));strings.extend(name+b'\0')
        else:field=name.ljust(8,b'\0')
        syms.extend(struct.pack('<8sIhHBB',field,value,sec,typ,storage,0))
    struct.pack_into('<I',strings,0,len(strings))
    headers=[];body=bytearray();offset=20+len(selected)*40
    for s in selected:
        ro=offset if s['raw'] else 0
        body.extend(s['raw']);offset+=len(s['raw'])
        reloff=offset if s['rel'] else 0
        for r in s['rel']:body.extend(struct.pack('<IIH',*r));offset+=10
        headers.append(struct.pack('<8s6I2HI',s['name'].encode(),0,0,s['size'],ro,reloff,0,len(s['rel']),0,s['flags']))
    header=struct.pack('<HHIIIHH',0x14c,len(selected),0,offset,len(symbols),0,0)
    Path(dst).write_bytes(header+b''.join(headers)+body+syms+strings)
