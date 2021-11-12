
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

object Copperv2Driver extends App {
  val verilog_args = Array("--target-dir", "work/rtl") ++ args
  (new ChiselStage).emitVerilog(new copperv2.copperv2, verilog_args ++ Array("-o","copperv2_rtl.v"))
  (new ChiselStage).execute(verilog_args ++ Array("--emit-modules", "verilog"),Seq(ChiselGeneratorAnnotation(() => new copperv2.copperv2)))
}

