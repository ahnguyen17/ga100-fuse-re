# GA100 VRAM sweep — offline verdict and capacity erratum

Scope: existing captures only. No MMIO, fuse-controller operations, driver edits, resets, or changes under `~/cmpunlocker`. Reproduce arithmetic and enumeration with `python3 /home/f0ol/ga100-ff-analysis/vram_sweep.py`; machine-readable output: `vram_sweep_results.json`.

## 1. Corrected capacity model

| Card/state | FBP disable | Defective | Active FBP | Active FBPA | GiB/FBPA | GiB |
|---|---|---|---:|---:|---:|---:|
| Hynix observed | 0x852 | 0x840 | 8 | 16 | 4 | 64 |
| Hynix hypothetical disable-only revival | 0x840 | 0x840 | 10 | 20 | 4 | **80** |
| Samsung observed | 0x024 | 0x024 | 10 | 20 | 2 | 40 |

FBP 1 and 4 are two **half-stack partition groups**, not two full stacks: two FBP × two FBPA/FBP × four GiB/FBPA = **16 GiB extra**, not 32. In the supplied topology (FBP pairs per stack), the Hynix moves from two full + four half stacks to four full + two half stacks. Six fully enabled 16-GiB stacks would give 96 GiB, requiring the defective-marked FBP 6 and 11 as well. That is not what the append changes. A defective fuse is a factory classification, not direct microscopy proving every associated cell dead; nonetheless these are not safe revival candidates.

20 FBPA × 4 GiB is physically coherent with eight-high 16-Gb-class HBM: a full stack has four such FBPA groups and 16 GiB. Samsung's 8-Gb-class model gives 8 GiB/full stack and 2 GiB/FBPA. **The fuse dumps validate topology, not die density.** In particular gpcprobe's capacity-per-die inference divides reported capacity by active partitions; it is not an independent density measurement. Samsung's real retained-pattern folding evidence supports the operational 40-GiB ceiling; neither these fuses nor vendor identity alone prove the physical mechanism is a missing/laser-fused RA[14].

### Newly exposed caveat: the published single append is not yet a complete revival recipe

`0x420004C1` correctly changes chain1/off19 data from 0x4290 to 0x4200 and its anchored FBP field from 0x852 to 0x840. However, a packed-chain scan finds **three separate 24-bit copies of the expanded partition mask**, all reproducing BOTH cards:

| Chain1 starting bit | Offset:bit | Hynix | Samsung |
|---:|---|---|---|
| 83 | 5:3 | 0xc0330c | 0x000c30 |
| 107 | 6:11 | 0xc0330c | 0x000c30 |
| 319 | 19:15 | 0xc0330c | 0x000c30 |

These equal the two-FBPA-per-FBP expansion of 0x852 and 0x024. Plausible consumers include FBPA, FBIO and L2 floorsweep masks, but consumer identities/independence are **not yet anchored**. The single append leaves all three copies unchanged. Thus it is proven to clear the FBP field in the software decode; it is **not proven sufficient to enable four additional FBPAs**. A schema or effective FBP/FBPA/FBIO shadow trace after a controlled change on someone else's sacrificial card must resolve whether these are independent gates or redundant/derived configuration. Do not promote the record to a validated 80-GiB recipe.

## 2. CFG1 and LMR: semantics are better constrained than two triples alone

Existing local reference `~/cmp170hx-wiki/docs/unlock/memory-geometry.md`, lines 67–138, supplies the field interpretation and measured A100 controls. The archived JRex table independently contains A100 PCIe 80-GiB geometry and floorsweep data.

* CFG1 `0x009a0204` encodes **per-partition address geometry**, not active partition count or total capacity. The duplicated tier nibbles 0x66 and 0x77 correspond to the observed 14-row-bit / 2-GiB and 15-row-bit / 4-GiB FBPA addressing depths; stock 0x44 corresponds to 12 row bits / 512 MiB. The reference calls ROWA bits[19:16], with row-count offset eight. Exact duplication/subpartition semantics still merit an authoritative header rather than extrapolation. COL remains 9 and BANK remains 2 for these HBM values. A capacity decode does not establish that the physical DRAM implements the requested rows.
* LMR `0x00100ce0` is **Local Memory Range**, the MMU's total-size declaration. Working encoding: `MiB = ((LMR >> 4) & 0x3f) << (LMR & 0xf)`. MAG field upper width remains unresolved in the archived reference, immaterial to these values. For these configurations MAG = twice active FBPA count; this is the chosen representation of total capacity, not proof of a separate hardware count field.

| LMR | MAG | SCALE | Total |
|---|---:|---:|---:|
| 0x208 | 32 | 8 | 8 GiB |
| 0x288 | 40 | 8 | 10 GiB |
| 0x20B | 32 | 11 | 64 GiB |
| 0x28A | 40 | 10 | 40 GiB |
| 0x28B | 40 | 11 | 80 GiB |

**Best coherent hypothetical Hynix 20-FBPA configuration: retain CFG1=0x02779000; change LMR from 0x20B to 0x28B**, with consistent driver/GSP/PMA memory descriptions (`targetFbBytes=0x1400000000`) and actual trained/enabled 20-FBPA topology. This is also the archived A100 PCIe 80-GiB pair, not an invented new geometry tier. It does not mean a lone LMR write revives partitions. No increase in per-FBPA address depth is wanted; no CFG1 tier change is predicted.

The Samsung 0x28B attempt advertises the same 80-GiB aperture but aliases on this card. Correct MMU/CFG1 arithmetic is necessary, not sufficient for backed storage. Historical notes asserting that both geometry values are unknown for Hynix 80 GiB are too pessimistic: the candidate pair is known; channel enablement/training is unvalidated.

### Chain2 offsets37–47

Hynix present records: 37=0x4184, 38=0x4184, 39=0x0782, 46=0xa000, 47=0x0059. Offsets40–45 are absent FF records, **not established zero-valued hardware fields**. Samsung differs here only at37=0x4104. Neither complete halfwords nor bytes are literal 0x10/0x14/0x18 counts. Arbitrarily sliding a five-bit window produces 16/24 inside DEVID words and even 20 at off46 bit11 on BOTH cards; these are false-positive-prone coincidences, not count fields. Off37/38 already encode IDs; off38/39/46/47 equality across different topology/density cards argues against assigning them a simple differing count. No FBPA-count/row-count field identified here.

## 3. Volatile-path sweep

**No demonstrated, actionable software route survives for additional usable VRAM on either existing card. This is not a proof that every undocumented preboot mechanism is impossible.**

### FF semantics / shadow cache

FF records are physically in the fuse array. The reported model consumes them in ascending order to populate configuration latches at fuse load/boot; last-writer-wins applies to logical destination fields. A shadow exists conceptually, but that does not make it a host-writable RAM cache. These two dumps contain no duplicate destination keys, so they do not independently prove overwrite precedence, absent-block defaults, or reset timing. Hardware state machine versus BootROM implementation is not established by the captures. No host FF-row staging/cache injection contract is demonstrated. SW-IFF/CTRL override routes require the unavailable software-override facility; issuing a read command or writing a data staging register is not substituting boot fuse contents.

### Unknown chains

Corrected histogram: Hynix has **only chains1/2** (16/55 records); no unknown-chain traces in this dump. Samsung has chain6/off291=0x8000, off292=0x001c and chain23/off66=0x0310 in addition to chains1/2. Repair/configuration is a reasonable hypothesis, not a decoded memory-geometry override. They could relate to memory, but even identifying such a field would reveal a fuse destination, not establish a volatile write route. The external 103-record histogram is not our Hynix data.

### IFF pointer / skip at0x820050

The only local claim of a volatile START skip is an **AI-generated external restatement with omitted primary citations**, internally mixing raw IFF pointer manipulation and SW-IFF injection. Neither START writability/retention nor a usable host-before-IFF timing window is established. A runtime START edit cannot undo a pre-firmware instruction already executed; a reset may erase the edit before consuming it. SW-IFF is separately blocked by EN_SW_OVERRIDE=0.

Offline raw dumps have identical rows488–507 on both cards. Row490=0x008c2c3c is consistent with an address-bearing instruction for CYA_0=0x008c2c0 (low bits treated as opcode); neighboring words are 0xff7fdffb and0x00802004. This is only an opcode hypothesis, **not a validated IFF disassembly**. No local schema makes the other tail words into verified geometry/floorsweep writes. In particular row496=0x009a4000 must not be called a memory-register target merely because its value resembles an FB address: it may be instruction data.

CYA_0 concerns PCIe link configuration, not adding FBPA capacity. A genuinely relevant IFF instruction would need to establish an FBPA/FBIO disable mask, CFG1/row geometry, memory-write security/lock, or memory-init selection. None is identified. Identical tails do not exclude a common nerf, but offer no explanation for differing FBPA counts. Skipping IFF does not inherently skip chain1 FF floorsweep decode. IFF therefore remains a **low-evidence research question**, not a surviving unlock recipe or a tested negative.

### Specific register families / what was and was not refuted

| Register(s) | Plausible role | Disposition |
|---|---|---|
| OPT_FBP 0x820364, FBPA0x820368, FBIO0x82036c; corresponding STATUS0x820d38/0x820c18/0x820c14 | Effective floorsweep | Readouts do not imply writable shadows. No documented independent writable bypass. |
| CTRL_FBP0x820938, CTRL_FBPA0x820818, CTRL_FBIO0x820814 | Explicit override plane | Closed by EN_SW_OVERRIDE0x820040=0 / DIS_SW_OVR0x820084=1. Do not retry. |
| FUSE_FB_CONFIG0x820328; CTRL0x820834; STATUS0x820c34 | Memory configuration | Same override-family gate; no validated alternate write path. |
| HALF_FBPA0x82049c; CTRL0x820800; STATUS0x820c00 | Half-capacity mode | Archived reference reads zero, not an unused extra capacity tier; same override gate. |
| MEM_LOCKED0x820340; FBPA_MEM_WR_SEC0x820618 | Lock / secure memory writes | Fuse readouts, not demonstrated unlock switches. Boot exploit opens geometry PLMs already; does not establish floorsweep override. |
| FEAT_OVR_DIS0x8203f0, FEAT_PLM0x823804, FEAT_ROW_REMAP0x823824 | Privileged feature plane / remap | Feature plane is distinct from CTRL; not blanket-disabled, but no FBP-enable field established. Rowspan/remap geometry trials already failed to add backed Samsung memory. |
| CFG1 0x9a0204; LMR0x100ce0; row-span0x9a020c | Address depth / total aperture | Runtime rewrite route refuted; boot geometry writes are already demonstrated. Neither creates enabled channels or physical rows. |
| FUSECTRL0x820000, FUSEADDR0x820004, RDATA0x820008, WDATA0x82000c, DEBUGCTRL0x820060 | Fuse-controller transactions | Staging/read plumbing is not effective-mask override; programming is irreversible and unvalidated. |
| IFF_RECORD0x820050 | Claimed boot instruction pointer | Not covered by FBPA-port value-gating measurement; nevertheless unproven timing/transport and no VRAM instruction. |

No complete per-address write history exists for this table, so do not assert that every register was personally write-tested. The Aug16 FBPA value-gating observation does **not logically prove** every0x820xxx fuse-controller register rejects writes. Those paths fail on their own gate/semantics/evidence, not by incorrectly universalizing one port experiment. The stipulated runtime CFG1/LMR/CTRL failures are not proposed again. HS FB-Falcon/fuse-shadow work remains an unachieved capability, not an available solution.

## 4. RIR monotonicity — qualify the argument, then enumerate

**For the Hynix spent slot0x0923, forced data=1 is immutable.** It cannot directly clear a physical disable bit. But physical OTP monotonicity does not imply logical FF-output monotonicity: forcing an address bit can orphan or retarget a record, potentially making a logical value disappear. The Gen3 off39→47 example uses exactly that distinction.

Enumerated all2048 addresses reachable by supersets of0x0923, applying each newly forced FF bit to the actual pool and replaying the conditional last-writer-wins decoder: **zero changes and zero orphanings of chain1/off19**. Row280 is unreachable because the inherited address requires row bit1=1, whereas280 has it zero. No reachable later record becomes a replacement for chain1/off19 either. This rules out a single redirect directly reducing the known FBP-disable field in this dump. It does not rule out an unmapped enabling/security field elsewhere; none has been identified. Redirect also removes the current row18/bit8 substitution, whose function remains unknown.

**Do not generalize “RIR forces ones only” to fresh slots.** In the supplied record model bit1 is forced DATA and bit0 ENABLE. A blank Samsung slot can in principle be encoded with DATA=0, substituting a zero without unburning the original physical main-array bit. This is a decoder-level possibility, not analog-programming proof. Samsung has no disable-only FBP to reclaim, so it offers no established extra usable VRAM here. Hard DEFECTIVE gates and actual channel health remain separate constraints.

## 5. Ranked decision table

Rank is practical value for obtaining usable memory; none authorizes hardware changes.

| Rank/path | Feasibility / evidence | One evidence package that would advance it |
|---|---|---|
| 1. Second known-good Hynix card | Existing64-GiB unlock is proven; adds aggregate capacity, not an80-GiB monolithic device. New unit still needs qualification. | Exact unit passes retained-pattern full-capacity, real H2D and teardown tests. |
| 2. FF append / complete floorsweep override | Arithmetic coherent for Hynix80GiB; published word changes only known FBP field. Additional packed masks, analog write, CMD_WRITE contract and training unresolved. **NO-GO.** | Same-macro sacrificial-card end-to-end evidence: validated transaction semantics, cold-cycle physical readback, effective FBP/FBPA/FBIO masks, trained20-FBPA topology and retained80-GiB integrity. Analog success alone removes only the first gate. |
| 3. Privileged boot-time shadow path | Theoretical alternate route; HS FB-Falcon capability not achieved. No retry of already-failed live overrides. | Reproducible volatile pre-init change to effective FBPA/FBIO topology that survives until training on this SKU. |
| 4. IFF skip | Unrefuted as abstract hardware possibility, unsupported as VRAM route. | Validated trace showing an actual memory-limiting IFF instruction plus host-controllable START at its consumption window changes effective memory topology/depth. |
| 5. Unknown-chain discovery | Useful schema work; not itself a transport or unlock. Hynix has no extra chains. | Authoritative mapping/controlled differential trace connecting a field to geometry and an independently writable volatile destination. |
| 6. RIR redirect for VRAM | Hynix direct mask clearing and all reachable one-bit FF retargets fail; generic monotonicity objection alone was insufficient. Blank Samsung slots theoretically permit zero substitution but supply no healthy FBP target. **NO-GO.** | Identified reachable indirect-enable target, with primary effective-shadow evidence; programming gates would still remain. |
| 7. CFG1/LMR-only patched-driver boot | Existing boot writes work, but raising declaration alone does not revive Hynix partitions; coherent Samsung80-GiB geometry already folds. | Independently demonstrated20-active-FBPA Hynix topology (then existing CFG1 +0x28B is coherent); for Samsung, a genuinely discriminating new geometry/physical-row mechanism, not another constants retry. |

## Source/verification limits

Primary local inputs: `fuse_dump_results.json`, `instructions.json`, `gpcprobe/gpc_probe.py` register table, archived field observations. Supporting interpretation: wiki `docs/unlock/memory-geometry.md`; skill references `gist-jrex286-ga100-fuse-table-sep30.md`, `gpcprobe-fuse-map-sep23.md`, and external fuse restatement. Source age and confidence matter: original notes contain the incorrect96-GiB claim, overly strong physical-die conclusions, and unsupported FF-overwrite safety claims. This report supersedes those conclusions analytically; it does not edit or publish the repository's historical artifacts.

Script completed with assertions passing:145 records, both observed capacities,80-GiB corrected target, identical tail region, and exhaustive Hynix redirect result. Raw capture includes no authoritative fuse schema or complete IFF decoder; those limits prevent a literal proof of universal software impossibility.
