/* Rome II DEI initial deployment. Runtime patch only; no logs or observers.
 * Lua 5.1 C functions return zero Lua values. No CRT or battle-script callbacks.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef void* H;
#define W __attribute__((stdcall))
#define API(ret,name,args) typedef ret (W *T##name) args; extern T##name p##name
API(H,GetModuleHandleA,(const char*));
API(u32,GetModuleFileNameA,(H,char*,u32));
API(H,GetCurrentProcess,(void));
API(int,ReadProcessMemory,(H,const void*,void*,u32,u32*));
API(H,CreateFileA,(const char*,u32,u32,void*,u32,u32,H));
API(int,ReadFile,(H,void*,u32,u32*,void*));
API(int,CloseHandle,(H));
API(int,VirtualProtect,(void*,u32,u32,u32*));
API(H,VirtualAlloc,(void*,u32,u32,u32));
API(int,FlushInstructionCache,(H,const void*,u32));
API(int,GetModuleHandleExA,(u32,const char*,H*));
API(int,BCryptOpenAlgorithmProvider,(H*,const u16*,const u16*,u32));
API(int,BCryptGetProperty,(H,const u16*,u8*,u32,u32*,u32));
API(int,BCryptCreateHash,(H,H*,u8*,u32,u8*,u32,u32));
API(int,BCryptHashData,(H,u8*,u32,u32));
API(int,BCryptFinishHash,(H,u8*,u32,u32));
API(int,BCryptDestroyHash,(H));
API(int,BCryptCloseAlgorithmProvider,(H,u32));


#ifndef RDP_HOST_FIXTURE
typedef char pointer_must_be_32bit[sizeof(void*)==4?1:-1];
#endif
#include "patch_bytes.h"
static u32 base;
static u8* stub;
static u8 installed_classify[13],installed_limit[6];
static int patch_active,patch_mode;
int rdp_install(void* lua);

static int same(const u8* a,const u8* b,u32 n) {
    u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;
}
static int read(u32 a,void* p,u32 n) {
    u32 got=0;
    return a && pReadProcessMemory(pGetCurrentProcess(),(const void*)a,p,n,&got) && got==n;
}

static __attribute__((noinline)) int engine_hash(H engine) {
    static const u8 expected[32]={
      0x07,0xcb,0x22,0x15,0xb8,0x05,0x91,0x22,0x4a,0x5f,0x88,0x89,0x96,0x33,0x44,0xd5,
      0x60,0x49,0x2f,0x09,0xc4,0xd2,0x26,0x96,0xc9,0x88,0xb9,0x57,0xca,0x49,0xb2,0xb7};
    static const u16 sha[]={83,72,65,50,53,54,0};
    static const u16 obj[]={79,98,106,101,99,116,76,101,110,103,116,104,0};
    char path[1024];u8 object[1024],block[1024],digest[32];
    H f=0,alg=0,hash=0;u32 n,size=0,got=0;int ok=0;
    n=pGetModuleFileNameA(engine,path,sizeof(path));if(!n || n>=sizeof(path))return 0;
    f=pCreateFileA(path,0x80000000,7,0,3,0x80,0);if(f==(H)-1)return 0;
    if(pBCryptOpenAlgorithmProvider(&alg,sha,0,0)<0)goto done;
    if(pBCryptGetProperty(alg,obj,(u8*)&size,4,&got,0)<0 || size>sizeof(object) || !size)goto done;
    if(pBCryptCreateHash(alg,&hash,object,size,0,0,0)<0)goto done;
    for(;;) {
        if(!pReadFile(f,block,sizeof(block),&n,0))goto done;
        if(!n)break;
        if(pBCryptHashData(hash,block,n,0)<0)goto done;
    }
    if(pBCryptFinishHash(hash,digest,32,0)<0)goto done;
    ok=same(digest,expected,32);
done:
    if(hash)pBCryptDestroyHash(hash);
    if(alg)pBCryptCloseAlgorithmProvider(alg,0);
    pCloseHandle(f);return ok;
}
static int validate(H engine) {
    static const u8 sig1[]={0x56,0x8b,0x74,0x24,0x08,0x57,0x8b,0x79,0x14};
    static const u8 sig2[]={0x83,0xec,0x28,0x8b,0xc1,0x8d,0x4c,0x24,0x34};
    static const u8 sig3[]={0x83,0xec,0x40,0x8b,0x44,0x24,0x44,0x53,0x55};
    static const u8 role_sig[]={0xff,0x50,0x78,0x80,0x78,0x65,0x00,0x75,0x0a};
    static const u8 arrival_sig[]={0x8b,0xcb,0xe8,0x49,0xdf,0x00,0x00,0x84,0xc0,0x0f,0x85,0x47,0x02,0x00,0x00};
    u8 data[16];
    if(!engine_hash(engine))return 0;
    if(!read(base+0x1b3310,data,9)||!same(data,sig1,9))return 0;
    if(!read(base+0x2e99d0,data,9)||!same(data,sig2,9))return 0;
    if(!read(base+0x139910,data,9)||!same(data,sig3,9))return 0;
    if(!read(base+0x16a41b,data,9)||!same(data,role_sig,9))return 0;
    if(!read(base+0x2f65d0,data,15)||!same(data,arrival_sig,15))return 0;
    return 1;
}
static int match_at(u32 address,const u8* expected,u32 size) {
    u8 actual[16];return size<=sizeof(actual) && read(address,actual,size) && same(actual,expected,size);
}
static void copy_to(u32 address,const u8* data,u32 size) {
    volatile u8* target=(volatile u8*)address;u32 i;for(i=0;i<size;i++)target[i]=data[i];
}
/* Both guarded sites are in one page. Called only from campaign Lua before
 * battle construction or after its completion, never from a battle callback.
 * Return -1 if original permissions/cache could not be confirmed after rollback.
 */
static int change_deployment_sites(int enable) {
    u32 old=0,ignored=0;int flushed,protected_ok,verified;
    const u8* a=enable?installed_classify:original_classify;
    const u8* b=enable?installed_limit:original_limit;
    const u8* before_a=enable?original_classify:installed_classify;
    const u8* before_b=enable?original_limit:installed_limit;
    if(!match_at(base+CLASSIFY_RVA,before_a,13)||!match_at(base+LIMIT_RVA,before_b,6))return 0;
    if(!pVirtualProtect((void*)(base+CLASSIFY_RVA),0x2a,0x40,&old))return 0;
    copy_to(base+LIMIT_RVA,b,6);copy_to(base+CLASSIFY_RVA,a,13);
    flushed=pFlushInstructionCache(pGetCurrentProcess(),(void*)(base+CLASSIFY_RVA),0x2a);
    verified=match_at(base+CLASSIFY_RVA,a,13)&&match_at(base+LIMIT_RVA,b,6);
    if(flushed && verified) {
        protected_ok=pVirtualProtect((void*)(base+CLASSIFY_RVA),0x2a,old,&ignored);
        if(protected_ok)return 1;
    }
    /* A failed protection restore leaves the page writable. Roll back before
     * returning, then attempt both cache flush and protection restore again. */
    copy_to(base+LIMIT_RVA,before_b,6);copy_to(base+CLASSIFY_RVA,before_a,13);
    flushed=pFlushInstructionCache(pGetCurrentProcess(),(void*)(base+CLASSIFY_RVA),0x2a);
    protected_ok=pVirtualProtect((void*)(base+CLASSIFY_RVA),0x2a,old,&ignored);
    if(!flushed || !protected_ok || !match_at(base+CLASSIFY_RVA,before_a,13)||
       !match_at(base+LIMIT_RVA,before_b,6))return -1;
    return 0;
}
/* This third site is on a different page. Each page restores its permissions.
 * Preflight all sites and roll deployment back if the arrival update fails.
 */
static int change_reinforcement_site(int enable) {
    u32 address=base+REINFORCEMENT_CHECK_RVA,old=0,ignored=0;
    const u8* after=enable?uncapped_reinforcement_check:original_reinforcement_check;
    const u8* before=enable?original_reinforcement_check:uncapped_reinforcement_check;
    int flushed,protected_ok;
    if(!match_at(address,before,5))return 0;
    if(!pVirtualProtect((void*)address,5,0x40,&old))return 0;
    copy_to(address,after,5);
    flushed=pFlushInstructionCache(pGetCurrentProcess(),(void*)address,5);
    if(flushed && match_at(address,after,5)) {
        if(pVirtualProtect((void*)address,5,old,&ignored))return 1;
    }
    copy_to(address,before,5);
    flushed=pFlushInstructionCache(pGetCurrentProcess(),(void*)address,5);
    protected_ok=pVirtualProtect((void*)address,5,old,&ignored);
    if(!flushed || !protected_ok || !match_at(address,before,5))return -1;
    return 0;
}
static int change_sites(int enable) {
    int result,rollback;
    if(!match_at(base+CLASSIFY_RVA,enable?original_classify:installed_classify,13)||
       !match_at(base+LIMIT_RVA,enable?original_limit:installed_limit,6)||
       !match_at(base+REINFORCEMENT_CHECK_RVA,
                 enable?original_reinforcement_check:uncapped_reinforcement_check,5))return 0;
    result=change_deployment_sites(enable);
    if(result!=1)return result;
    result=change_reinforcement_site(enable);
    if(result==1)return 1;
    rollback=change_deployment_sites(!enable);
    if(rollback!=1 || result<0)return -1;
    return 0;
}
/* Install/restore logic uses the V05 payloads unchanged. No file needs to be
 * writable: CreateFileA is used only to open the engine DLL for SHA256 reading.
 */
static int install_patch(int attackers_only) {
    H engine=pGetModuleHandleA("empire.retail.dll"),pinned=0;
    u32 old=0;
    if(patch_active)return patch_mode==attackers_only;
    base=(u32)engine;
    if(!engine || !validate(engine))return 0;
    if(!match_at(base+CLASSIFY_RVA,original_classify,13)||
       !match_at(base+LIMIT_RVA,original_limit,6)||
       !match_at(base+REINFORCEMENT_CHECK_RVA,original_reinforcement_check,5))return 0;
    if(!pGetModuleHandleExA(5,(const char*)rdp_install,&pinned))return 0;
    if(!stub) {
        stub=(u8*)pVirtualAlloc(0,4096,0x3000,4);
        if(!stub)return 0;
        make_all_stubs(stub,base+MERGE_RVA,base+SEPARATE_RVA,base+LIMIT_RVA+6);
        if(!pVirtualProtect(stub,4096,0x20,&old)||
           !pFlushInstructionCache(pGetCurrentProcess(),stub,STUB_BYTES)) {
            stub=0;return 0;
        }
    }
    make_classify(installed_classify,base+CLASSIFY_RVA,
                  (u32)stub+(attackers_only?ATTACKER_CLASSIFY_OFFSET:0));
    if(attackers_only)make_limit_detour(installed_limit,base+LIMIT_RVA,
                                      (u32)stub+ATTACKER_LIMIT_OFFSET);
    else make_limit(installed_limit);
    if(change_sites(1)!=1)return 0;
    patch_active=1;patch_mode=attackers_only;return 1;
}
static int disable_patch(void) {
    if(!patch_active)return 1;
    if(change_sites(0)!=1)return 0;
    patch_active=0;patch_mode=0;return 1;
}
int rdp_install(void* lua) {(void)lua;install_patch(0);return 0;}
int rdp_install_settlement(void* lua) {(void)lua;install_patch(1);return 0;}
int rdp_disable(void* lua) {(void)lua;disable_patch();return 0;}
int W DllMain(H module,u32 reason,void* reserved) {
    (void)module;(void)reason;(void)reserved;return 1;
}
