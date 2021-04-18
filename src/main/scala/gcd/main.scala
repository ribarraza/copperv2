package gcd

import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

object GCDDriver extends App {
  (new ChiselStage).emitVerilog(new DecoupledGcd(4), args)
  (new ChiselStage).emitVerilog(new GCD, args)
}
