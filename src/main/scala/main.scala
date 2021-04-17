package gcd

import chisel3.stage.ChiselStage

object GCDDriver extends App {
  (new ChiselStage).emitVerilog(new GCD)
}
