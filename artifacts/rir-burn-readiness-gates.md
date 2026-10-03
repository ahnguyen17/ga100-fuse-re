# RIR burn-readiness gates

- Separate target encoding from programmer encoding: 0x0923 -> 0x8FA7 is a verified logical target (delta 0x8684), not a validated FUSEWDATA payload. Establish delta-vs-final-word semantics, upper-half masking, CMD_WRITE encoding, write-register address, programming voltage/timing, and completion/error handling from primary same-macro burn evidence before enabling writes.
- Require cold-power-cycle RIR readback plus effective main-array and OPT-shadow verification; a controller program/done transition cannot establish analog success.
- Do not probe analog programming with same-value writes to spent slots or FPF burns. Same-value writes have no measurable new bit and unproven pulse suppression; FPF protection bits are not disposable and their success does not validate the separate RIR macro.
- Treat each partial intermediate enabled RIR address as potentially active and harmful; never retry a partial or ambiguous burn. Require evidence that the intended multi-bit transition is supported on a preprogrammed record.
- Validate the consequences of removing row-18/bit-8 substitution and of orphaning the whole offset-39 field. Destination offset-47 coverage alone proves neither safe removal nor the resulting OPT shadow.
- Require DEBUGCTRL cleanup and readback before any main-array command or reset. Python finally is best-effort cleanup, not a guarantee against process/host failure; a stuck programming controller requires a validated recovery procedure.
- Gate any 8 GT/s attempt on cold-boot OPT_DISABLE_GEN3_SPEED=0, validated secondary-disable handling, and endpoint/root-port capabilities; advertisement alone is insufficient. Preserve a Gen2 boot path with all experimental retrain automation disabled.
