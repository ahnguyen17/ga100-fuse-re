#!/usr/bin/env python3
"""RIR-macro + fuse-array dump via /dev/mem BAR0 — READ-ONLY with safe writes.

Purpose (2026-09-23 fuse-bypass intel verification):
  1. Dump the 8-row RIR macro (16 x 16-bit substitution records) on both 170HX cards.
  2. Read main-array fuse rows 0..511 via the FUSE controller command interface.
  3. Verify the external group's claims: live RIR slot 15 == 0x0923, other 15 slots 0xFFFF,
     FF pool at rows 222..331, and decode FF pool (chain_id, offset, data) tuples.

Registers written (ALL are read-safe commands — this script cannot burn a fuse):
  FUSEADDR   0x820004  <- row select (0..511 main array; mod 8 when RWL=1)
  FUSECTRL   0x820000  <- cmd bits[1:0]=1 (CMD_READ); state bits[20:16]==4 = done
  DEBUGCTRL  0x820060  <- bit1 RWL=1 routes to RIR macro (read gate), then restored 0

NO FUSEWDATA WRITE, NO CMD_WRITE, no other registers touched. DEBUGCTRL is cleared and
read-back-verified at the end of each card pass (leaving RWL set can wedge the die).

Run:  echo '<pw>' | sudo -S python3 tools/fuse_rir_dump.py 2>/dev/null
"""
import mmap, os, sys, json

# FUSE controller regs (BAR0 offsets, external-group intel + GA100 fuse block layout)
FUSE_CTRL   = 0x820000
FUSE_ADDR   = 0x820004
FUSE_RDATA  = 0x820008
DEBUG_CTRL  = 0x820060
CMD_READ    = 1
STATE_MASK  = 0x001F0000   # bits [20:16]
STATE_DONE  = 4 << 16

CARDS = [
    ("GPU2", "0000:81:00.0", "Hynix 8GB (0x20c2) -> 64GB"),
    ("GPU3", "0000:82:00.0", "Samsung 10GB (0x2082) -> 40GB"),
]

def bar0_base(pci):
    with open(f"/sys/bus/pci/devices/{pci}/resource") as f:
        for line in f:
            p = line.split()
            if len(p) >= 3 and int(p[1], 16) > int(p[0], 16):
                return int(p[0], 16)
    raise RuntimeError(f"no BAR0 for {pci}")

class Bar0:
    def __init__(self, pci):
        self.base = bar0_base(pci)
        # BAR0 size from the resource file (end - start + 1), page-aligned up
        size = 0
        with open(f"/sys/bus/pci/devices/{pci}/resource") as f:
            for line in f:
                p = line.split()
                if len(p) >= 3 and int(p[1], 16) > int(p[0], 16):
                    size = int(p[1], 16) - int(p[0], 16) + 1
                    break
        self.virt = self.base & ~0xFFF                      # page-aligned map base
        self.maplen = min((size + 0xFFF) & ~0xFFF, 0x1000000)  # ≤16 MB covers FUSE block @0x820000
        self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)  # O_RDWR needed so MMIO writes stick
        self.mm = mmap.mmap(self.fd, self.maplen, mmap.MAP_SHARED,
                            mmap.ACCESS_WRITE, offset=self.virt)
    def _idx(self, off): return self.base - self.virt + off   # BAR0-relative off -> map index
    def rd(self, off):
        i = self._idx(off); return int.from_bytes(self.mm[i:i+4], "little")
    def wr(self, off, val):
        i = self._idx(off); self.mm[i:i+4] = val.to_bytes(4, "little")
    def close(self):
        self.mm.close(); os.close(self.fd)

def fuse_cmd_read(bar, addr_val):
    """Issue CMD_READ at FUSEADDR=addr_val, poll state==done, return FUSERDATA."""
    bar.wr(FUSE_ADDR, addr_val)
    bar.wr(FUSE_CTRL, (bar.rd(FUSE_CTRL) & ~0x3) | CMD_READ)
    for _ in range(20000):
        st = bar.rd(FUSE_CTRL)
        if (st & STATE_MASK) == STATE_DONE:
            return bar.rd(FUSE_RDATA)
    raise RuntimeError(f"fuse read timeout: addr=0x{addr_val:x} ctrl=0x{st:08x}")

def dump_card(name, pci, desc):
    print(f"\n===== {name} {pci} — {desc} — BAR0 @ phys 0x{bar0_base(pci):x} =====")
    bar = Bar0(pci)
    out = {"card": name, "pci": pci, "desc": desc, "rir_rows": {}, "main_rows": {}}
    dbg0 = 0
    try:
        ctrl0 = bar.rd(FUSE_CTRL); addr0 = bar.rd(FUSE_ADDR); dbg0 = bar.rd(DEBUG_CTRL)
        print(f"[boot state] FUSECTRL=0x{ctrl0:08x} FUSEADDR=0x{addr0:08x} DEBUGCTRL=0x{dbg0:08x}")
        if dbg0 & 0x2:
            print("!! DEBUGCTRL.RWL already set at boot — unexpected; clearing first")
            bar.wr(DEBUG_CTRL, dbg0 & ~0x2)

        # --- Pass 1: RIR macro (RWL=1) — 8 rows, 2x16-bit records each ---
        bar.wr(DEBUG_CTRL, dbg0 | 0x2)          # route to RIR domain (read gate)
        if not (bar.rd(DEBUG_CTRL) & 0x2):
            print("!! could not set RWL — RIR dump unavailable on this card"); rir = None
        else:
            rir = {}
            for a in range(8):
                rir[a] = fuse_cmd_read(bar, a)  # FUSEADDR taken mod 8 by hw
            out["rir_rows"] = rir
            bar.wr(DEBUG_CTRL, dbg0 & ~0x2)     # restore
            for label, v in (("RIR", rir),):
                print(f"--- {label} macro (8 rows x 32b = 16 records) ---")
                for a in sorted(v):
                    w = v[a]
                    lo, hi = w & 0xFFFF, w >> 16
                    print(f"  row {a}: 0x{w:08x}  lo=0x{lo:04x} ({lo:016b})  hi=0x{hi:04x} ({hi:016b})")
            # decode per the claimed 14-bit layout: [15:2]=addr, bit1=data, bit0=enable
            print("--- RIR decode (claimed layout) ---")
            for a in sorted(rir):
                for half, rec in (("lo", rir[a] & 0xFFFF), ("hi", rir[a] >> 16)):
                    if rec in (0x0000,):
                        tag = "blank"
                    elif rec == 0xFFFF:
                        tag = "ALL-BL0WN (spent)"
                    else:
                        addr = rec >> 2; data = (rec >> 1) & 1; en = rec & 1
                        tag = f"addr={addr} (row {addr//32} bit {addr%32}) data={data} en={en}"
                    print(f"  row {a} {half}: 0x{rec:04x} -> {tag}")

        # --- Pass 2: main array rows 0..511 (RWL=0) ---
        main = {}
        for a in range(512):
            main[a] = fuse_cmd_read(bar, a)
        out["main_rows"] = main
        bar.wr(DEBUG_CTRL, dbg0 & ~0x2)
        nz = [a for a in main if main[a] not in (0, 0xFFFFFFFF)]
        print(f"--- main array: {len(nz)} non-trivial rows of 512 ---")
        print("    nonzero rows:", " ".join(f"{a}:{main[a]&0xFFFFFFFF:08x}" for a in nz[:40]))
        if len(nz) > 40: print(f"    ... and {len(nz)-40} more (full dump in JSON)")

        # --- FF pool decode attempt (rows 222..331, external claim) ---
        print("--- FF pool decode (rows 222..331), heuristic [27:20]=chain [19:16]=? [15:0]=data ---")
        ff = []
        for a in range(222, 332):
            w = main.get(a, 0)
            if w == 0 or w == 0xFFFFFFFF: continue
            ff.append((a, w))
        chains = {}
        for a, w in ff:
            for chain_shift, off_shift in ((20, 16), (27, 22)):
                ch = (w >> chain_shift) & 0xFF
                off = (w >> (chain_shift - 4)) & 0xF
                chains.setdefault(chain_shift, {}).setdefault(ch, 0)
                chains[chain_shift][ch] += 1
        for cs in sorted(chains):
            print(f"  assume chain@bit{cs}: " + " ".join(f"ch{c}={n}" for c, n in sorted(chains[cs].items())))
    finally:
        # hard guarantee: DEBUGCTRL back to boot value with RWL clear, verified
        try:
            bar.wr(DEBUG_CTRL, dbg0 & ~0x2)
            rb = bar.rd(DEBUG_CTRL)
            print(f"[exit] DEBUGCTRL readback = 0x{rb:08x} ({'OK — RWL clear' if not rb & 2 else '!!! RWL STILL SET — DO NOT ISSUE FURTHER FUSE CMDS'})")
        except Exception as e:
            print(f"[exit] DEBUGCTRL restore FAILED: {e}")
        bar.close()
    return out

if __name__ == "__main__":
    results = []
    for name, pci, desc in CARDS:
        try:
            results.append(dump_card(name, pci, desc))
        except Exception as e:
            print(f"!!! {name} ({pci}) FAILED: {e}", file=sys.stderr)
            results.append({"card": name, "pci": pci, "error": str(e)})
    with open(os.path.expanduser("~/fuse_dump_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("\nsaved -> ~/fuse_dump_results.json")
