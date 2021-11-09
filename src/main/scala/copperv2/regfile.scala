
package copperv2

import chisel3._

class RegFile(addr_width: Int = 5, data_width: Int = 32) extends Module {
  val io = IO(new Bundle {
    val rd_en = Input(Bool())
    val rs1_en = Input(Bool())
    val rs2_en = Input(Bool())
    val rd = Input(UInt(addr_width.W))
    val rs1 = Input(UInt(addr_width.W))
    val rs2 = Input(UInt(addr_width.W))
    val rd_din = Input(UInt(data_width.W))
    val rs1_dout = Output(UInt(data_width.W))
    val rs2_dout = Output(UInt(data_width.W))
  })
  val mem_depth = scala.math.pow(2, addr_width).toInt
  val mem = SyncReadMem(mem_depth, UInt(data_width.W))
  io.rs1_dout := WireDefault(0.U)
  io.rs2_dout := WireDefault(0.U)
  val rs1_dout_int = WireDefault(0.U)
  val rs2_dout_int = WireDefault(0.U)
  val en1 = WireDefault(0.B)
  val en2 = WireDefault(0.B)
  when (io.rd_en) {
    mem.write(io.rd, io.rd_din)
  }
  rs1_dout_int := mem.read(io.rs1,io.rs1_en & en1)
  when (io.rs1 =/= 0.U) {
    en1 := 1.B
    io.rs1_dout := rs1_dout_int
  }
  rs2_dout_int := mem.read(io.rs2,io.rs2_en & en2)
  when (io.rs2 =/= 0.U) {
    en2 := 1.B
    io.rs2_dout := rs2_dout_int
  }
  io.elements foreach {case (name, port: Data) => 
      dontTouch(port.asUInt() | 0.U).suggestName(name)
    }
}
