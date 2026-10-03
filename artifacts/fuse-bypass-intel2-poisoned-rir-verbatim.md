# Verbatim: "8GB poisoned RIR record explained" (external group, relayed by Andy, 2026-10)

Clanker's  explanation of the poisoned RIR record is difficult to follow, as comrade clanker mixes up decimal and hexadecimal notations and also the whole RIR row and the 14-bit address part.

The original RIR record is 0x0923. The 14-bit address part is 0x248 or 00 0010 0100 1000. Only three of the fourteen bits are blown. The last two bits of the the RIR are 11, so it cannot be used to unburn any fuses.

The "trick"  is to spoil a row in the FF part of the fuse array, and make it meaningless. Because bit 3 of the address bit is set, it cannot target any of the first eight bits of a fuse array row. These eight bits contain the chainId, so it can not be changed. The next eight bits are part of the offset in the chain id, and can be modified.

The two other blown bits restrict the potential modifications to one in four of the fuse rows. Address 9193 is 0x23E9 or 10 0011 1110 1001. Five more fuse bits have been blown. The nine first bits 1 0001 1111 or 0x11F specify the row 287.  The last five bits 0 1001 specify the offset 9 in the fuse row.
