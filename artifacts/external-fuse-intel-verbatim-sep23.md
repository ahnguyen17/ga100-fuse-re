I will start sharing information on the fuses. Two weeks ago I asked a robot operating on a private server to explain how the fuses work on Nvidia cards. I will share the responses after anonymizing them.

First question:
> List all the different ways of bypassing limitations and nerfs imposed by fuses.


Based on the project logs, specifically the `MODSpath.md` analysis and recent register experiments, there are four distinct mechanisms for bypassing the fuse-imposed limitations on the GA100 CMP cards. These range from volatile runtime overrides to permanent physical modifications.

**1. Volatile Software Override (XVE_FUSE_OVERRIDE)**
The driver can arm a volatile override plane via the `XVE_FUSE_OVERRIDE` register at `0x8872C`. This allows the software to spoof the values of specific "BOOT" fuses (like `opt_pcie_boot_gen23_disable`) without touching the physical fuse array. This is currently used to unlock Gen2 by forcing the boot disable bits to 0. However, this mechanism is limited; it does not reach all fuses. Specifically, `opt_disable_gen3_speed` (the hard gate for Gen3) has no entry in this override plane, so this method cannot unlock Gen3 or other features gated by non-BOOT fuses [1][2].

**2. IFF Record Manipulation (Volatile/Per-Boot)**
The Initial Fuse Fuses (IFF) records are executed at the earliest point in boot, before firmware. By modifying the `IFF_RECORD` pointer (e.g., changing `START` in `0x820050`), you can skip specific IFF instructions that set restrictive values in registers like `NV_XP_PL_CYA_0` [3]. Alternatively, if `EN_SW_OVERRIDE` is enabled, you can use the "SW IFF" mechanism to write volatile values into the fuse row space, effectively acting as a general fuse-value editor for that boot session [4]. This is useful for testing or bypassing IFF-sourced nerfs (like the second Gen3 disable in `CYA_0`), but it is not persistent across power cycles [5].

**3. Fuseless Fuse (FF) Record Appending (Permanent)**


For fuses stored in the "fuseless" region (rows 222–303 on this card), you can bypass the 0→1 OTP limitation by appending a new record. The hardware uses the *last* record at a specific `chainId`/`offset` location. By writing a new record with the desired value (e.g., clearing `opt_disable_gen3_speed`), you effectively change the fuse value without erasing the original bit. This is a permanent, irreversible change (you can't un-write it, but you can append a "restore" record if you know the original value). This is the primary route for unlocking Gen3, as `opt_disable_gen3_speed` is likely a fuseless fuse on GA100 [2][1].

**4. Redundant In-Row (RIR) Fuse Writing (Permanent)**
For hard OTP fuses (rows 0–221), you can use the RIR mechanism to write a new value to a redundant fuse location. This requires enabling `DEBUGCTRL.RWL` (bit 1) before writing to `FUSEWDATA` and `FUSEADDR`, then disabling it after. This is how `DISABLE_SW_OVERRIDE` was cleared on some cards, allowing the software override plane to be armed [4][2]. This is the most powerful but also the most dangerous method, as a wrong address can permanently brick the card by "repairing" the wrong fuse [2].

**Summary of Bypass Capabilities:**
* **Gen2:** Bypassed via XVE override (volatile) or IFF skip (volatile).
* **Gen3:** Requires FF record append (permanent) for `opt_disable_gen3_speed` AND IFF skip/XVE override for `CYA_0` bits.
* **SW Override Enable:** Requires RIR write to clear `DISABLE_SW_OVERRIDE` (permanent) on cards where it is fused.
* **Other Nerfs (GPC, NVLink, etc.):** Likely require FF record appends if they are in the fuseless region, or RIR if they are hard fuses. The `MODSpath.md` document suggests that many segmentation fuses moved to fuseless storage on Ampere, making FF appends the preferred method for most unlocks [2].

Sources:



My follow-up question:
> What are the requirements for using each of these methods? Do any of them depend on each other? Are there other limitations?

The four mechanisms form a strict dependency chain, and each has distinct prerequisites that the project logs make explicit.

**1. Volatile Software Override (XVE_FUSE_OVERRIDE @ 0x8872C)**
* **Requirements:** Requires the `XVE_FUSE_OVERRIDE` register to be writable. On stock CMP cards, this register is often gated by a PLM (Privilege Level Mask) or the `DISABLE_SW_OVERRIDE` fuse. If `DISABLE_SW_OVERRIDE_STATUS=1` (as seen on PG199), the stock MODS path aborts, and direct host writes may be rejected unless the PLM is opened [1]. It does *not* require a fuse burn, but it *does* require that the specific fuse bits you want to override are actually covered by the override plane. As noted in the logs, `opt_disable_gen3_speed` is **not** covered by this plane, so this method alone cannot unlock Gen3 [2].
* **Dependencies:** None. It is the lowest-level, most volatile method. It is re-applied every boot and lost on power cycle.

**2. FF (Fuseless-Fuse) Records (Chain 2)**
* **Requirements:** Requires the ability to write to the FF chain rows (rows 222–331). This is a **permanent** OTP burn. The critical requirement is that the target card must be one where FF writes actually land (i.e., the FF pool is not disabled or the die is not defective in that region). The PG199 tests showed that while the digital controller accepts the write command and enters the program state, the actual analog burn of FF-pool row 487 failed under all tested conditions, suggesting that on *that specific card*, FF writes may not be effective for all rows [3]. However, the FPF (Firmware Protection) rows did burn successfully [3].

* **Dependencies:** **Depends on Method 1?** No, but it is often used *in conjunction* with Method 1. For example, to unlock Gen3, you need to burn the FF record for `DISABLE_GEN3_SPEED` (Method 2) **AND** set the `XVE_FUSE_OVERRIDE` bits for the BOOT fuses (Method 1) [2]. The FF record handles the hard gate that the volatile override cannot reach.
* **Limitations:** Irreversible. If you burn a record that defines a 16-bit block, you can only *clear* bits (1→0) by appending a new record that overrides the block with a value where those bits are 0. You cannot "unburn" the original record. Also, FF records only affect "fuseless" (RAM-repair) fuses, not the main physical column fuses [4].

**3. IFF (Initial Fuse File) / Software IFF Transport**
* **Requirements:** Requires the `EN_SW_OVERRIDE` bit to be set and the `IFF_SW_FUSING` mechanism to be active. This path is used to load a stream of register writes that are executed pre-firmware. The stock MODS path checks `Fuse.IsSwFusingAllowed`, which is true only if `disable_sw_override == 0`. On PG199, `DISABLE_SW_OVERRIDE_STATUS=1`, so this path is blocked by default [3]. To use it, you would need to either burn the `disable_sw_override` fuse to 0 (which is a main-array fuse, not an FF fuse, so it requires a direct host burn) or find a way to bypass the check.
* **Dependencies:** **Depends on Method 2?** Potentially. If `disable_sw_override` is a main-array fuse, you cannot use FF records to clear it. You would need a direct host burn (Method 4) or a secure rework. However, if the IFF stream itself is used to *set* the `XVE_FUSE_OVERRIDE` register, then it depends on the IFF transport being functional.


* **Limitations:** The IFF stream is executed pre-firmware, so it can only write to registers that are accessible at that stage. It cannot burn fuses. It is a volatile mechanism (the register writes are lost on reset unless the IFF stream is re-executed).

**4. Direct Host Fuse Burn (CMD_WRITE)**
* **Requirements:** Requires opening the `FUSEWDATA_PLM` and `FUSECTRL_PLM` to L0 write access. This is typically done via a secure-bootloader exploit or a patched driver that opens the PLMs. The PG199 runner used a patched `cmpunlocker` module to open these PLMs [3]. It also requires that the target fuse row is blank (0) and that the requested delta is only 0→1 bits.
* **Dependencies:** **Depends on Method 1/2/3?** No, it is the most fundamental method. It can burn any fuse, including the main-array fuses that FF records cannot touch. However, it is the most dangerous and irreversible.
* **Limitations:** Irreversible. Requires precise control over the fuse programming voltage and timing. The PG199 tests showed that while the digital controller accepts the write, the analog burn may fail if the voltage/current is not sufficient. The "no-retry" rule applies: if a partial burn occurs, you should not retry, as it may cause a short or damage the cell [3].

**Summary of Dependencies:**
* **Gen3 Unlock:** Requires **Method 2** (FF record for `DISABLE_GEN3_SPEED`) + **Method 1** (XVE_FUSE_OVERRIDE for BOOT fuses).
* **Gen4 Unlock:** Requires **Method 2** (FF record for `DISABLE_GEN4_SPEED`) + **Method 1** (XVE_FUSE_OVERRIDE for BOOT fuses) + **Method 3** (IFF stream to set `XVE_FUSE_OVERRIDE` if needed) + **Method 4** (Direct host burn if `disable_sw_override` is set and needs to be cleared).

*Continued, with sources omitted:*

- **Secure Rework:** Requires **Method 4** (Direct host burn) to burn the `disable_sw_override` fuse, or a signed secure rework image (**Method 5**, not fully detailed in the logs but mentioned as a separate path).

The key limitation is that **Method 1** cannot reach all fuses, **Method 2** cannot reach main-array fuses, **Method 3** is blocked if `disable_sw_override` is set, and **Method 4** is the only method that can reach all fuses but is the most dangerous.


Next question:
> Explain the fuse chainIds and their offsets? How are these mapped to the physical fuse rows?


The "chain" concept in the FF pool is a logical grouping, not a direct physical row mapping. Each 32-bit fuse row in the FF pool is decoded into an instruction with a `chain_id`, a type (e.g., FS for floorsweep), an offset, and data [1][2]. The chain_id tells you which logical domain the instruction affects (e.g., Chain 1 is TOP_FS, Chain 2 is CHIPLET_LOGIC, and higher IDs are RAMREPAIR) [1][2]. The offset is the specific field index within that chain, and the data is the 16-bit value written to that field. The physical mapping is that the FF pool occupies a contiguous block of rows in the 512-row fuse array, located between the RIR macro and the IFF region [1][2]. The exact start and end rows are detected by `detect_ff_pool` based on non-zero content and the IFF start boundary [1][2].

The physical fuse rows themselves are just 32-bit OTP cells. The "chain" and "offset" are software abstractions defined by the FF encoder (Maxwell FF encoder in this case). The hardware boot ROM reads the FF pool rows, decodes each 32-bit word into (chain, offset, data) tuples, and then applies the data to the corresponding shadow registers or logic blocks. The "last-writer-wins" rule means that if multiple rows in the FF pool target the same (chain, offset) pair, the one with the higher row number takes precedence [1][2]. So, to map a logical chain/offset to a physical row, you look at the FF pool dump: each row in that region corresponds to one instruction, and the decoded fields tell you which chain and offset it affects. The physical row number is just the index in the fuse array, and the logical mapping is derived from the bitfields within that 32-bit word.


Next question:
> Do we have a list of the different chain_ids used in the cards we have a fuse read output from? Which of these IDs are known to us and which ones are unknown?

I am sharing this data, as it is explicitly stated that it is from empirical observations and not from some hypothetical Nvidia sources.

*Sources, i.e. names of contributors omitted:*

Looking at the actual fuse read output from the GA100 card at 0000:02:00.0, the FF pool (rows 222–331) decodes into the following chain IDs [1]:

Known/identified:
- Chain 1 — TOP_FS (16 instructions) [1]
- Chain 2 — CHIPLET_LOGIC (53 instructions) [1]
- Chain 10 — RAMREPAIR (2 instructions) [1]
- Chain 25 — RAMREPAIR (1 instruction) [1]
- Chain 26 — RAMREPAIR (2 instructions) [1]

Unknown (no name in our code or the dump):
- Chain 6 — 6 instructions [1]
- Chain 7 — 1 instruction [1]
- Chain 13 — 2 instructions [1]
- Chain 14 — 1 instruction [1]
- Chain 16 — 3 instructions [1]
- Chain 19 — 2 instructions [1]
- Chain 20 — 1 instruction [1]
- Chain 27 — 9 instructions [1]
- Chain 28 — 4 instructions [1]

So out of the 14 distinct chain IDs present on this card, only 5 are identified (1, 2, 10, 25, 26). The remaining 9 (6, 7, 13, 14, 16, 19, 20, 27, 28) are unlabelled. Note that chains 17 and 22 from the RAMREPAIR_CHAINS set in `fuse_read_v5.py` [2][3] do not appear in this particular card's FF pool — they're defined as known RAM repair chains but simply aren't programmed here.

The dump also notes the chain names for 1 and 2 are marked "UNVERIFIED — empirically corroborated" [1], meaning we've cross-validated them against shadow registers but don't have a definitive NVIDIA source for the naming. The unknown chains could potentially be identified by correlating their offset/data patterns against known register maps or by comparing across multiple cards with different SKU configurations, but we don't have that analysis done yet.


**Next question:**
> Please explain what each of the TOP_FS, CHIPLET_LOGIC, and RAMREPAIR chains do.

The short answer is: we don't have authoritative documentation for any of them. The names `TOP_FS` and `CHIPLET_LOGIC` are empirical labels we assigned based on correlating the decoded 16-bit field values against the `OPT_*` shadow registers in the fuse register space, and they are explicitly marked **UNVERIFIED** in the design doc [1]. The real per-chip field maps live in an encrypted `ga100_f.json` that isn't in the tree, so we can't say with certainty what each chain is *supposed* to configure [1].

What we can infer from the data:

**Chain 1 (TOP_FS, 16 instructions):** The decoded 16-bit words map cleanly onto the per-GPC TPC enable/disable masks and a handful of top-level feature bits (FBIO, FBPA, GPC count, NVDEC, PES, FBP, ROP_L2) [2]. The `fuse_annotate_1.py` script uses these chain-1 values as the "disable" source for TPC classification because the `OPT_TPC_GPCn_DISABLE` registers read 0 — the actual per-GPC TPC masks only exist in this FF chain [3]. So functionally it's the **top-level floorsweep configuration**: which GPCs/TPCs are enabled, which memory controllers are active, and a few global feature toggles. The name "TOP_FS" presumably stands for "Top-level FloorSweep."

**Chain 2 (CHIPLET_LOGIC, 53 instructions):** This is the largest chain and the decoded fields include `DEVIDA`/`DEVIDB` (both 0x20C2, matching the CMP 170HX device ID) and `GPC_CP` (0x23) [2]. Given the size and the presence of device-identity and chiplet-level configuration fields, this is almost certainly the **chiplet-level logic configuration**: device ID, SKU identity, per-chiplet feature enablement, and possibly inter-chiplet routing or power domain settings. The name "CHIPLET_LOGIC" is our best guess for what this domain covers. We don't have a complete field map for all 53 instructions, so there may be other fields we haven't identified.


**RAMREPAIR (Chains 10, 25, 26):** These are explicitly labelled "do not modify" in the chain table [2]. They contain the **RIR (Repair-In-Row) macro records** — the data that the on-die repair engine uses to remap defective SRAM/DRAM rows at boot. Chain 25 has one record (`0x35B=0x0108`) and chain 26 has two (`0x139=0xE000`, `0x13A=0x0007`) [2]. The single live RIR record on this die is a no-op (forces a bit that's already 1), so there's no actual rework history [1]. The "do not modify" warning is because corrupting these records would break the repair engine's ability to remap rows, potentially bricking the card or causing silent memory corruption.

The other 12 chains (6, 7, 13, 14, 16, 19, 20, 27, 28) have no names and no known field maps. They could be additional floorsweep domains (e.g., per-engine microcode version floors, security configuration, PCIe lane configuration, or power management), but without the encrypted `ga100_f.json` we can't say [1]. If you want to identify them, the approach would be to decode each chain's 16-bit words and look for correlations with `OPT_*` or `FEATURE_*` registers that we haven't already mapped to chains 1 or 2.


I had to consult the resident expert:
> Are the RIR records part of the 512-row fuse array? If so, what row are they located on?

No, the RIR records are not part of the 512-row main fuse array; they reside in a separate 8-row RIR macro. The main array is 512 rows of 32 bits, while the RIR macro is a distinct 8-row structure where each row holds two 16-bit substitution records (16 records total) [1]. The RIR macro is accessed by routing the fuse controller to the RIR domain via `DEBUGCTRL` bit 1 (RWL = 1), and the specific RIR row is selected by taking the `FUSEADDR` modulo 8 . Because they are physically separate from the main array, RIR records do not occupy any row in the 512-row main fuse array; instead, they use their own 8-row address space to override individual bits in the main array or specific registers like `DIS_PROGRAM` .


> How can you read the value of the RIR records from the host?

To read the RIR records from the host, you need to route the fuse controller into the RIR domain and then issue read commands for each of the 8 rows. The key is setting bit 1 (RWL) of `DEBUGCTRL` (`0x820060`) to 1, which gates both reads and writes to the RIR macro instead of the main array [1]. Because the RIR macro is only 8 rows deep, the `FUSEADDR` (`0x820004`) is taken modulo 8, so you can simply iterate `FUSEADDR` from 0 to 7 to read all 8 rows [1]. For each address, write 1 to the command field (bits [1:0]) of `FUSECTRL` (`0x820000`) to trigger a `CMD_READ`, wait for the state machine to reach state 4 (done) in bits [20:16], and then read the 32-bit result from `FUSERDATA` (`0x820008`) [1]. Each 32-bit word contains two 16-bit RIR records: the lower 16 bits are the first record and the upper 16 bits are the second [1]. You can decode each 16-bit half using the confirmed 14-bit layout: bits [15:2] are the main-array bit address, bit 1 is the forced data value, and bit 0 is the enable flag [1]. A critical safety note: you must clear `DEBUGCTRL` back to 0 immediately after reading the RIR rows and verify it reads back as 0 before issuing any other fuse commands, as leaving RWL set can wedge the die by causing it to skip the main array and repeatedly re-read the RIR macro [2].

Question:
> Present the one live RIR slot in binary format. How many of the 16 fuse bits are blown?
> Do we know of any other record in the fuse array the RIR record could be redirected to by re-fusing?

The one live RIR record on the 8GB Hynix (0x20c2) cards is in slot 15 (row 7, lower half) and reads 0x0923 [1]. In binary, that is:

```0000 1001 0010 0011```

Counting the set bits, there are **5** of the 16 fuse bits blown: bits 0, 1, 5, 8, and 11 [1]. The other 15 slots are `0xFFFF` (all 16 bits blown), which is why they are permanently spent and unusable [1].

Regarding redirection, the monotonic nature of OTP fuses means you can only add bits to the existing `0x0923` pattern; you cannot clear any of the 5 already-set bits [1]. This severely restricts where the record can be redirected. The address field is bits 15:2, and the current address is 584 (row 18, bit 8) [1]. Any new address must be a bitwise superset of 584. The only known successful redirection is to **row 287, bit 9** (address 9193), which requires burning bits 2, 6, 7, 10, 12, and 13 in the record word [1]. This specific target works because it displaces the FF record offset from 39 to 47, effectively orphaning the original block and clearing `OPT_DISABLE_GEN3_SPEED` [1]. Other potential targets exist mathematically (any address where addr & 584 == 584), but they are generally unsafe because they would overwrite other critical FF records or land on blocks not masked by a later "last-writer-wins" row [1]. The bit-9 divert is the only one proven safe across all 42 measured dies because the destination block is always owned by a subsequent row [1].

