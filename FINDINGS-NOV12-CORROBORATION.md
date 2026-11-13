# FINDINGS — 12 November 2026: independent corroboration, glitch tooling, and status change

Single-rig field note (same two cards as the October report). Everything below is
sourced; nothing new was burned by us. Read-only work only, as before.

## 1. Our FF-pool decode is independently corroborated by third-party burn evidence

On 2026-11-12 Kate published a voltage-fault-injection unlock of the 8 GB CMP 170HX
([blog](https://blog.kate.land/posts/using-voltage-glitching-to-unlock-the-a100/),
[code](https://github.com/kate-land/ga100vfi)). Her published FF location table maps
`NV_FUSE_OPT_FBP_DISABLE` to **chain 1, bits 307–318 (blocks 19–20)** — the same
chain/offset-19 anchor we derived and published here on 2026-10-02
(`FINDINGS.md` §1), from different evidence (differential decode of both SKUs'
occupied FF space vs OPT-shadow readbacks).

Her executed burn reduces the 8 GB FBP disable mask `0x852 → 0x840`, i.e. data
`0x840 << 3 = 0x4200` positioned at bit 3 of the block — **exactly the data word of
our derived append record `0x420004C1`** (chain 1 / offset 19 / data `0x4200`).
Two independent derivations, one executed on real silicon, agree.

Consequence: the `rir-burn-readiness-gates.md` requirement for "primary same-macro
analog-write evidence" is now satisfied by third-party execution (her burns landed,
read back, survived power cycles, and unlocked 80 GiB on 9 of 10 cards). Our
standing verdict "NO-GO on a working card until FF/RIR analog-write evidence exists"
is accordingly **superseded**: the evidence exists; the remaining risk is
executional, not evidentiary. Addendum 2's INCOMPLETE flag on the append recipe
(three redundant expanded FBP masks untouched) still stands — the FBP record revives
partitions 1 and 4 only; a full A100-80G configuration additionally wants the
FBPA/FBIO/ROP_L2/GPC/TPC records enumerated from the per-die dump.

## 2. Our cards' floorsweep re-audited read-only (gpcprobe, driver bound)

`gpcprobe` (matstatman, 2026-09-18 + per-stack view) on 2026-11-12, dump archived at
the rig. Both cards, values raw:

| Option word | 8 GB (10de:20c2, Hynix) | 10 GB (10de:2082, Samsung) |
|---|---|---|
| OPT_GPC_DISABLE | `0x23` (GPC 0,1,5 gated) | `0x23` |
| OPT_GPC_DEFECTIVE | `0x0` (**zero** defective GPCs) | `0x0` |
| OPT_FBP_DISABLE | `0x852` | `0x24` |
| OPT_FBP_DEFECTIVE | `0x840` | `0x24` (disable == defective) |
| OPT_FBPA/FBIO/ROP_L2_DISABLE | `0x00c0330c` | `0x00c0300c`→`0x0c30` (see dump) |
| OPT_NVLINK_DISABLE | `0x7` (gated, not defective) | `0x7` |
| OPT_GEN23 / OPT_DISABLE_GEN3_SPEED | set / set | set / set |

- The 8 GB card has **80 GiB latent** (20 healthy FBPAs × 4 GiB; FBPs 1,4 gated-not-dead;
  6,11 dead). Our October "96 GiB" correction is reconfirmed; 96 is impossible, 80 is real.
- The 10 GB card's memory disable == defective everywhere: **40 GiB is final** for VRAM
  (consistent with our R14 row-path analysis), but its GPC 0,1,5 are gated with **zero
  defective** — the compute (~1.7×) and Gen3 unlocks apply fully.

## 3. The 8 GB RIR situation is unchanged and still dead

Community re-derivation (cmp.wiki, 2026-09/10, multiple reporters) matches ours:
15 of 16 RIR slots factory-burned, the 16th a live poison record; no viable RIR
route on 8 GB. The 8 GB path to FF appends is now voltage glitching (below).

## 4. Glitch tooling exists in two open forms (no 0402 removal needed)

- [dalzyu/pico-ga100vfi](https://github.com/dalzyu/pico-ga100vfi): RP2350 (Pico 2)
  port, **I2C-only actuation** — PMBus `VOUT_COMMAND` dips on the MP2888B timed off
  the `PEX_RST` release edge. Three wires (GND, I2CC SDA/SCL, PEX_RST), no PWMVID
  intercept, no resistor removal. Published telemetry: 14% Goldilocks rate, median
  <1 s, 95% by ~20 shots, 100/100 PCIe link recovery. Handles the glitch step only
  (DSOV=0, open PLMs); the re-arm + FF-append executor is not yet public.
- [JosiahWhite/rp2040-glitch-tool](https://github.com/JosiahWhite/rp2040-glitch-tool):
  generic RP2040 I2C/pulse/trigger toolkit (staged programs, PIO/DMA timing).
- [kate-land/ga100vfi](https://github.com/kate-land/ga100vfi): the original STM32G431
  PWMVID-intercept design, firmware + KiCad + host CLI + GA100 register capture
  engine. Requires the PWMVID tap + one 0402 0Ω removal.

The concurrent 8 GB write-up by `mellojello_` (credited in the pico repo) proved the
I2C + `PEX_RST` path first.

## 5. 10 GB card: community-proven RIR gate burn (separate route, not ours)

For the **10 GB only** (ships with 16 blank RIR slots), `lixiangwuxian/170hx-rir-tool`
burns a two-record pair clearing `disable_sw_override`; reproduced by multiple
parties, survives cold power-off. After the gate is clear, Gen3 and full 128 SM are
**volatile software overrides** (re-applied each boot). Note the wiki's value
`0x00950015` vs the linear-layout pair `0x00150095` byte-order discussion — use the
tool's README, not hand-written words.

This is unrelated to our October 8 GB RIR erratum (the `[2,6,7,10,12,13]`-vs-`[2,7,9,10,15]`
correction concerned a redirect record on the 8 GB card's spent macro). Our erratum
stands as written for 8 GB; it does not apply to the 10 GB gate burn.

## 6. Status of this rig

- 8 GB: staged — Pico 2 + pico-ga100vfi campaign planned; FF append records to be
  computed from our archived 512-row dump per Addendum 2's open items.
- 10 GB: proceeding with the community-proven gate burn after read-only preflight
  (`--dump-rir` blank-slot verification) on this specific card.

No fuses were written by us in producing this document.
