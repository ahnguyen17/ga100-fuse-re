# Fuse-Bypass Intel (external researcher, shared by Andy, 2026-09-23) — verbatim + analysis

**Provenance:** Andy relayed Q&A output from another researcher's private-server AI assistant
("robot operating on a private server"), based on that group's MODSpath.md project logs and
register experiments. Anonymized. Part 1 of a series — more expected.

## Their four bypass mechanisms (their taxonomy)

1. **Volatile Software Override — XVE_FUSE_OVERRIDE @ BAR0 0x8872C.** Spoofs BOOT fuses only
   (opt_pcie_boot_gen23_disable etc.). Does NOT cover opt_disable_gen3_speed → cannot unlock
   Gen3 alone. Re-applied every boot, lost on power cycle.
2. **IFF record manipulation (volatile/per-boot).** IFF records execute pre-firmware; skip
   restrictive instructions (e.g. NV_XP_PL_CYA_0 Gen3-disable bits) by editing the IFF_RECORD
   pointer (START in 0x820050), or use "SW IFF" volatile fuse-row writes — requires
   EN_SW_OVERRIDE.
3. **FF ("fuseless fuse") record append (PERMANENT).** FF pool = rows 222–331 on this card.
   Boot ROM decodes each 32-bit row into (chain_id, type, offset, data); **last-writer-wins** —
   appending a new record at the same chainId/offset overrides the original block without
   un-burning it. Claimed primary route for Gen3 (opt_disable_gen3_speed is "likely fuseless").
4. **RIR (Redundant In-Row) fuse writing (PERMANENT, most dangerous).** For hard OTP rows 0–221.
   Enable DEBUGCTRL(0x820060) bit 1 (RWL) → write FUSEWDATA/FUSEADDR. Claimed used to clear
   DISABLE_SW_OVERRIDE on some cards.

## Their fuse-architecture data (GA100, card at 0000:02:00.0)

- **512-row × 32-bit main OTP array**; FF pool detected between RIR macro and IFF region
  (rows 222–331 observed; detect via non-zero content + IFF start boundary).
- **RIR macro: separate 8-row structure**, 2×16-bit records/row = 16 slots. Accessed by
  DEBUGCTRL bit1 RWL=1; FUSEADDR taken **mod 8**. Read: FUSECTRL(0x820000) cmd=1, poll state
  bits [20:16]==4, read FUSERDATA(0x820008). **Must clear DEBUGCTRL to 0 and verify readback
  after — leaving RWL set can wedge the die.**
- **RIR record layout (14-bit decode, "confirmed"):** bits [15:2] = main-array bit address,
  bit 1 = forced data value, bit 0 = enable.
- **Chain IDs observed in FF pool:** known/labelled (UNVERIFIED names, empirically corroborated):
  1=TOP_FS (16 instr), 2=CHIPLET_LOGIC (53 instr, contains DEVIDA/DEVIDB=0x20C2, GPC_CP=0x23),
  10/25/26=RAMREPAIR ("do not modify" — RIR repair records). Unknown: 6,7,13,14,16,19,20,27,28.
- **Chain 1 TOP_FS = top-level floorsweep**: per-GPC TPC enable masks + FBIO/FBPA/GPC/NVDEC/
  PES/FBP/ROP_L2 bits. **OPT_TPC_GPCn_DISABLE registers read 0 — the real per-GPC TPC masks
  exist ONLY in FF chain 1.**
- **Live RIR record (8GB Hynix 0x20c2):** slot 15 (row 7 lower half) = 0x0923
  (0000 1001 0010 0011, 5 bits blown: 0,1,5,8,11). Address field 584 = row 18, bit 8.
  Other 15 slots = 0xFFFF (spent). The external source calls the live record a no-op;
  do not treat that as established on our die. Oct 2 reads show row 18 differs from
  its row-19 twin at bit 8; loss of the old row-18 substitution needs independent
  functional validation before redirecting it.
- **THE GEN3 RECIPE (their claim):** redirect slot 15 to row 287 bit 9 (address 9193) by
  burning bits "2, 6, 7, 10, 12, 13". This displaces an FF record's offset 39→47, orphaning
  the original block, **effectively clearing OPT_DISABLE_GEN3_SPEED**. Claimed "proven safe
  across all 42 measured dies" (destination block always owned by a later last-writer-wins
  row). OTP monotonicity restricts targets to addresses where `addr & 584 == 584`.
- **Gen3 full unlock = FF/RIR permanent fix + XVE_FUSE_OVERRIDE 0xA for BOOT bits + IFF/CYA_0
  second disable handling.** Gen4 adds more.
- **PG199 caution:** digital fuse controller accepts CMD_WRITE and enters program state, but
  the ANALOG burn of FF-pool row 487 failed under all tested conditions on that card (FPF rows
  did burn). A "successful" command ≠ burned bit → post-burn readback verify is mandatory.
  No-retry rule on partial burns.
- Real per-chip field maps live in an encrypted ga100_f.json they don't have.

## Sophia's cross-check against our data (2026-09-23)

**Consistent with our measurements:**
- XVE_FUSE_OVERRIDE 0x8872C, value 0xA, BOOT_GEN23_DIS bits 0/1 + BOOT_GEN3_DIS bits 2/3,
  advertisement-only effect — **exactly matches upstream PR #37 commit 80966db** (our skill).
- OPT_DISABLE_GEN3_SPEED (0x820250) as a separate ceiling — matches PR #37 ba82a70. Note the
  wiki separately lists FUSE_PCIE_GEN3_DIS @ 0x820580=0x1 — possibly fuse-sense vs OPT-shadow
  views of the same/gated path; multi-gate structure plausible.
- Our gpcprobe (Sep 23): FUSE_EN_SW_OVERRIDE(0x820040)=0, FUSE_DIS_SW_OVR=1 on ALL 170HX →
  consistent with their claim that SW-override/IFF paths are blocked on stock cards and that
  clearing DISABLE_SW_OVERRIDE required a permanent RIR burn on "some cards".
- Per-GPC TPC masks living only in FF chain 1 dovetails with our gpcprobe finding that GPC
  0,1,5 are disabled-NOT-defective on both our cards (the 70-SM SKU cut).

**Tension / arithmetic flag (verified in python, 2026-09-23):**
CORRECTION (recomputed against the Oct 2 dump): under the stated 14-bit layout
(addr=bits[15:2], data=bit1, enable=bit0), redirecting 0x0923 → address 9193
requires **{2,7,9,10,15}**, delta **0x8684**, final record **0x8FA7**.
The previous seven-bit calculation here was wrong. Data=0 is NOT reachable from
0x0923 because bit 1 is already burned. The external six-bit list
"2,6,7,10,12,13" produces 0x3DE7, a different redirect. The superset rule (9193 & 584 == 584) does hold, and
0x0923→row-18/bit-8 and 9193→row-287/bit-9 both decode cleanly. So the mechanism is internally
coherent but **the burn-bit list as relayed does not decode — re-derive before anyone burns
anything.** (Or their address encoding differs from the stated layout — also possible.)

**Reclassification of our verdicts:**
- "Gen3 = confirmed silicon wall on stock cards" (PR #37) → correct ONLY as "no *software*
  path". PR #37 never explored permanent OTP re-fuse (FF append / RIR redirect). The wall is
  policy+OTP, not physics — IF their FF-pool mapping holds on our dies.
- "64→96GB CLOSED" (Hynix FBP 1,4 disabled-not-defective) — note their chain-1/TOP_FS
  architecture suggests FBP disable bits are also FF-pool records; a last-writer-wins APPEND
  (no RIR needed, if FF writes land on our die — see PG199 analog-failure caveat) could
  theoretically clear FBP disable masks. Still walled by FUSE_EN_SW_OVERRIDE=0 for volatile
  paths and by unknown FB-Falcon retrain requirements for reviving channels. Not reopened —
  but the closure rationale shifts from "no lever exists" to "no volatile lever; permanent
  levers untested".

**Risk frame for our rig:** RIR redirect = permanent, one-shot (15/16 slots already spent on
THEIR card; OUR slots undumped), irreversible, sacrifices whatever row-18/bit-8 currently
forces, and PR #37 documented off-the-bus/bar-dead failure when forcing 8 GT/s with the fuse
still sensed. Payoff if real: Gen3 x4 ≈ 3.9 GB/s theoretical (~2× our current 1.5 GB/s
Gen2) — model-load latency, not decode throughput.

**Verification we can run READ-ONLY on our cards (needs sudo pw — lost from memory, ask Andy):**
1. RIR macro dump: DEBUGCTRL RWL=1, FUSEADDR 0–7, CMD_READ, FUSERDATA; decode both halves of
   each row; clear+verify DEBUGCTRL. Confirm slot inventory (are 15/16 really 0xFFFF on ours?).
2. FF pool dump rows 222–331 via the fuse read path; decode chain/offset/data; locate the
   offset-39 block and row 287's instruction; check last-writer-wins coverage.
3. Compare 0x20c2 (Hynix) vs 0x2082 (Samsung) — their data is from a 0x20c2.
