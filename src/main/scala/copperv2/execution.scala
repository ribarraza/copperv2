package copperv2

import chisel3._
import chisel3.util._

class Alu extends Module with RequireSyncReset {
  val io = IO(new Bundle {
    val din1 = Input(UInt(32.W))
    val din2 = Input(UInt(32.W))
    val op = Input(AluOp())
    val dout = Output(UInt(32.W))
    val comp = Output(new AluComp())
  })
  val in1 = Wire(UInt())
  val in2 = Wire(UInt())
  in1 := io.din1
  in2 := io.din2
  io.dout := MuxLookup(io.op.asUInt,0.U,Array(
    AluOp.NOP.asUInt  -> 0.U,
    AluOp.ADD.asUInt  -> (in1 + in2), 
    AluOp.SUB.asUInt  -> (in1 - in2),
    AluOp.AND.asUInt  -> (in1 & in2),
    AluOp.SLL.asUInt  -> (in1 << in2(4,0)),
    AluOp.SRL.asUInt  -> (in1 >> in2(4,0)),
    AluOp.SRA.asUInt  -> (in1.asSInt >> in2(4,0)).asUInt,
    AluOp.XOR.asUInt  -> (in1 ^ in2),
    AluOp.OR.asUInt   -> (in1 | in2),
    AluOp.SLT.asUInt  -> io.comp.LT.asUInt,
    AluOp.SLTU.asUInt -> io.comp.LTU.asUInt,
  ))
  io.comp.EQ := in1 === in2
  io.comp.LT := in1.asSInt < in2.asSInt
  io.comp.LTU := in1 < in2
}

