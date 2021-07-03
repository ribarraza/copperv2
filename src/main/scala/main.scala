
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

object Copperv2Driver extends App {
  val verilog_args = Array("--target-dir", "work/chisel") ++ args
  (new ChiselStage).emitVerilog(new copperv2.copperv2, verilog_args)
  (new ChiselStage).emitVerilog(new copperv2.ControlUnit, verilog_args)
}

