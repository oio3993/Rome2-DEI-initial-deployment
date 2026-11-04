"""Emit small COFF import-address-table objects for the no-CRT snapshot DLL.
Uses documented IMAGE_REL_I386_DIR32NB relocations; no import libraries needed.
"""
import struct,sys
from pathlib import Path
APIS={
 'KERNEL32.dll':['GetModuleHandleA','GetModuleFileNameA','GetCurrentProcess','ReadProcessMemory',
                 'CreateFileA','ReadFile','CloseHandle','VirtualProtect','VirtualAlloc','FlushInstructionCache','GetModuleHandleExA'],
 'bcrypt.dll':['BCryptOpenAlgorithmProvider','BCryptGetProperty','BCryptCreateHash',
               'BCryptHashData','BCryptFinishHash','BCryptDestroyHash','BCryptCloseAlgorithmProvider']}

def emit(path):
    # 2 = descriptors; 4 = ILT; 5 = IAT; 6 = hints/names; 7 = DLL names.
    sections=[bytearray() for _ in range(5)]
    relocs=[[] for _ in sections]
    symbols=[('.idata$'+str(k),0,i+1,3) for i,k in enumerate([2,4,5,6,7])]
    for dll,apis in APIS.items():
        desc=len(sections[0]);ilt=len(sections[1]);iat=len(sections[2]);dn=len(sections[4])
        sections[4].extend(dll.encode()+b'\0')
        sections[0].extend(struct.pack('<5I',ilt,0,0,dn,iat))
        relocs[0].extend([(desc,1),(desc+12,4),(desc+16,2)])
        for api in apis:
            if len(sections[3])%2:sections[3].append(0)
            hint=len(sections[3]);sections[3].extend(b'\0\0'+api.encode()+b'\0')
            symbols.append(('_p'+api,len(sections[2]),3,2))
            for j in [1,2]:
                off=len(sections[j]);sections[j].extend(struct.pack('<I',hint));relocs[j].append((off,3))
        sections[1].extend(b'\0'*4);sections[2].extend(b'\0'*4)
    strings=bytearray(b'\0'*4)
    symdata=bytearray()
    for name,value,sec,cls in symbols:
        raw=name.encode()
        if len(raw)>8:
            field=struct.pack('<II',0,len(strings));strings.extend(raw+b'\0')
        else:field=raw.ljust(8,b'\0')
        symdata.extend(struct.pack('<8sIhHBB',field,value,sec,0,cls,0))
    struct.pack_into('<I',strings,0,len(strings))
    offset=20+5*40;headers=[];body=bytearray()
    for i,raw in enumerate(sections):
        rawoff=offset;body.extend(raw);offset+=len(raw)
        reloff=offset if relocs[i] else 0
        for a,s in relocs[i]:body.extend(struct.pack('<IIH',a,s,7));offset+=10
        headers.append(struct.pack('<8s6I2HI',symbols[i][0].encode(),0,0,len(raw),rawoff,reloff,0,len(relocs[i]),0,0xc0300040))
    header=struct.pack('<HHIIIHH',0x14c,5,0,offset,len(symbols),0,0)
    Path(path).write_bytes(header+b''.join(headers)+body+symdata+strings)

if __name__=='__main__':emit(sys.argv[1])
