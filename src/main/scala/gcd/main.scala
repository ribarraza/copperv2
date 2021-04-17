package gcd

import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

object GCDDriver extends App {
  (new ChiselStage).execute(args,
    Seq(ChiselGeneratorAnnotation(() => new GCD)))
}
