# Part 2: "8GB poisoned RIR record explained" (external group restatement, relayed by Andy, 2026-10)

Verbatim text archived in `external-fuse-intel2-poisoned-rir-verbatim.md`. This is a cleaner
rewrite (attributed to "Clanker's explanation" being confusing) of the RIR redirect mechanism.
**All numbers python-verified against our own dump (verify_poison, Oct 3):**

- Record 0x0923: address part = 0x248 = 584, exactly 3 address bits blown ✓
- Last two record bits = 11 → can only force 1s, cannot unburn ✓
- **Address bit 3 blown → the forced bit-within-row can never be < 8 → bits[7:0] of any
  target row (the chainId, per our anchor-verified layout) are IMMUTABLE.** (New constraint,
  consistent with our decode: chain can't be changed, only offset bits [15:6].)
- Two other blown row bits (1, 4 of the 9-bit row field) → reachable targets = supersets of
  row 18 → 128 of 512 rows = exactly **1 in 4** ✓
- Target 9193 = 0x23E9: nine-bit row field 0x11F → row 287 ✓; five-bit field 01001 → forces
  bit 9 of row 287 ✓ (they call the bit-within-row the "offset in the fuse row" — under our
  layout, bit 9 sits in the offset field: 39 → 47, orphaning (2,39); row 288 owns (2,47))
- **"Five more fuse bits have been blown"** → 0x0923 → 0x8FA7 requires exactly 5 new bits =
  **[2,7,9,10,15] — their restatement now AGREES with our published erratum** and contradicts
  their own earlier 6-bit list [2,6,7,10,12,13]. Independent confirmation of the correction.
