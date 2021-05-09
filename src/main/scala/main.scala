
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

object Copperv2Driver extends App {
  val verilog_args = args
  //(new ChiselStage).emitVerilog(new DecoupledGcd(4), verilog_args)
  //(new ChiselStage).emitVerilog(new GCD, verilog_args)
  (new ChiselStage).emitVerilog(new copperv2.copperv2, verilog_args)
}
