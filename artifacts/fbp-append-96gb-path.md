# 64→96 GB Path via FF Append (derived Oct 2 2026, post-decode)

**The lever astra's decode exposed:** Hynix OPT_FBP_DISABLE lives in FF chain 1, offset 19
(row 280, data 0x4290 → mask 0x852 = bits 1,4,6,11). FBP 6,11 are DEFECTIVE (hard rows
26/27, unrevivable), but **bits 1,4 are disable-only** — and FF records are APPENDABLE
(last-writer-wins, rows 222–331, 39 blank rows available above row 280 on our dump).

**Derived append record (python-verified):** `0x420004C1` at any blank row >280
(chain=1, offset=19, data=0x4200) → post-append OPT_FBP_DISABLE shadow = 0x840,
clearing exactly bits 1 and 4. 16→20 active FBPAs (5120-bit, same bus width class as the
Samsung 40GB geometry), theoretical 96 GiB (2 full + 4 half stacks of 16 Gb Hynix dies).

**Three gates before this is real (all currently open):**
1. **FF-pool analog write** — external group's PG199 card: FF row write accepted digitally,
   analog burn FAILED (FPF rows burned fine). No positive FF-pool burn evidence anywhere.
   Same verification problem as the RIR redirect, minus even a spent-slot structure to probe.
2. **96 GB geometry values** — CFG1/LMR for 20-FBPA/16Gb-die config unknown; current unlock
   uses CFG1 0x02779000 (A100-80GB value, 4096-bit). Needs jonpry-class FB-geometry RE or a
   community source. targetFbBytes would be 0x1800000000.
3. **FB-Falcon boot retrain of revived channels** — plausible that boot trains any
   non-disabled channel automatically (mask is consumed at HBM init), but unproven; our Aug
   notes flagged "boot-time channel retrain" as a separate wall. It was written assuming the
   mask could never change — needs re-examination, not assumption either way.

**Ordering vs the Gen3 redirect:** HIGHER payoff (+32 GB permanent VRAM vs transfer speed),
SIMILAR risk class (one-way OTP, unvalidated burn mechanism, could brick the best card),
MORE unknowns (geometry + retrain on top of the burn). Neither is go while the burn
mechanism is unproven.

**Deterministic alternative:** second Hynix 8GB card (~$400-600) → +64 GB with the existing,
proven unlock. Strictly dominates on risk; loses only if 96 GB monolithic capacity (single
context > 64 GB) is the specific need.

Volatile paths all confirmed dead earlier: CTRL_OPT override fused off (FUSE_EN_SW_OVERRIDE=0,
all 170HX), CFG1/LMR runtime writes value-gated at the port (Aug 16 proof).
