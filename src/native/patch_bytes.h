/* Pure x86 payload builders. No calls into this DLL from patched engine code. */
#define CLASSIFY_RVA 0x139b72u
#define MERGE_RVA 0x139b7fu
#define SEPARATE_RVA 0x139d0au
#define LIMIT_RVA 0x139b96u
#define MERGE_LIMIT 512u
#define ALLIANCE_DEFENDING_FLAG 0x65u
#define ATTACKER_CLASSIFY_OFFSET 64u
#define ATTACKER_LIMIT_OFFSET 128u
#define STUB_BYTES 159u
#define REINFORCEMENT_CHECK_RVA 0x2f65d2u
/* The arrival loop calls the "at capacity" predicate and blocks if AL != 0.
 * Replace only this call with AL=0. Other arrival conditions and batch size stay.
 */
static const u8 original_reinforcement_check[5]={0xe8,0x49,0xdf,0x00,0x00};
static const u8 uncapped_reinforcement_check[5]={0x30,0xc0,0x90,0x90,0x90};
static const u8 original_classify[13]={0x83,0xbb,0x74,0x01,0,0,2,0x0f,0x85,0x8b,1,0,0};
static const u8 original_limit[6]={0x8b,0x90,0x24,1,0,0};
static void put32(u8* p,u32 v) {u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static void make_stub(u8* p,u32 merge,u32 other) {
    u32 i;
    for(i=0;i<7;i++)p[i]=original_classify[i];
    p[6]=1;
    p[7]=0x0f;p[8]=0x84;put32(p+9,merge-((u32)p+13));
    for(i=0;i<7;i++)p[13+i]=original_classify[i];
    p[20]=0x0f;p[21]=0x84;put32(p+22,merge-((u32)p+26));
    p[26]=0xe9;put32(p+27,other-((u32)p+31));
}
static void make_classify(u8* p,u32 site,u32 stub) {
    u32 i;p[0]=0xe9;put32(p+1,stub-(site+5));for(i=5;i<13;i++)p[i]=0x90;
}
static void make_limit(u8* p) {p[0]=0xba;put32(p+1,MERGE_LIMIT);p[5]=0x90;}
/* EDI is the live alliance. BattleAllianceIsAttacker uses its byte +0x65:
 * zero is the attacking side when the opposing campaign alliance is defending.
 * Kind 2 always follows the engine's original initial-garrison path.
 */
static void make_attacker_stub(u8* p,u32 merge,u32 other) {
    u32 i;
    for(i=0;i<7;i++)p[i]=original_classify[i];
    p[7]=0x0f;p[8]=0x84;put32(p+9,merge-((u32)p+13));
    p[13]=0x80;p[14]=0x7f;p[15]=ALLIANCE_DEFENDING_FLAG;p[16]=0;
    p[17]=0x0f;p[18]=0x85;put32(p+19,other-((u32)p+23));
    for(i=0;i<7;i++)p[23+i]=original_classify[i];
    p[29]=1;
    p[30]=0x0f;p[31]=0x84;put32(p+32,merge-((u32)p+36));
    p[36]=0xe9;put32(p+37,other-((u32)p+41));
}
/* EAX is the engine configuration pointer at LIMIT_RVA. For defenders, execute
 * exactly the original MOV EDX,[EAX+0x124]. No defender cap increase. */
static void make_attacker_limit_stub(u8* p,u32 continuation) {
    u32 i;
    p[0]=0x80;p[1]=0x7f;p[2]=ALLIANCE_DEFENDING_FLAG;p[3]=0;
    p[4]=0x0f;p[5]=0x85;put32(p+6,10);
    p[10]=0xba;put32(p+11,MERGE_LIMIT);
    p[15]=0xe9;put32(p+16,continuation-((u32)p+20));
    for(i=0;i<6;i++)p[20+i]=original_limit[i];
    p[26]=0xe9;put32(p+27,continuation-((u32)p+31));
}
static void make_limit_detour(u8* p,u32 site,u32 target) {
    p[0]=0xe9;put32(p+1,target-(site+5));p[5]=0x90;
}
static void make_all_stubs(u8* p,u32 merge,u32 other,u32 limit_continuation) {
    make_stub(p,merge,other);
    make_attacker_stub(p+ATTACKER_CLASSIFY_OFFSET,merge,other);
    make_attacker_limit_stub(p+ATTACKER_LIMIT_OFFSET,limit_continuation);
}
