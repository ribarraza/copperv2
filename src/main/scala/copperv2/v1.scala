package copperv2

import chisel3._

class idecoder extends BlackBox {
  val io = IO(new Bundle {
    val inst = Input(UInt(32.W))
    val imm = Output(UInt(32.W))
    val inst_type = Output(UInt(4.W))
    val rd = Output(UInt(5.W))
    val rs1 = Output(UInt(5.W))
    val rs2 = Output(UInt(5.W))
    val funct = Output(UInt(5.W))
  })
}

class register_file extends BlackBox {
  val io = IO(new Bundle {
    val clk = Input(Clock())
    val rst = Input(Reset())
    val rd_en = Input(Bool())
    val rs1_en = Input(Bool())
    val rs2_en = Input(Bool())
    val rd = Input(UInt(5.W))
    val rs1 = Input(UInt(5.W))
    val rs2 = Input(UInt(5.W))
    val rd_din = Input(UInt(32.W))
    val rs1_dout = Output(UInt(32.W))
    val rs2_dout = Output(UInt(32.W))
  })
}

class arith_logic_unit extends BlackBox {
  val io = IO(new Bundle {
    val alu_din1 = Input(UInt(32.W))
    val alu_din2 = Input(UInt(32.W))
    val alu_op = Input(UInt(4.W))
    val alu_dout = Output(UInt(32.W))
    val alu_comp = Output(UInt(3.W))
  })
}

class control_unit extends BlackBox {
  val io = IO(new Bundle {
    val clk = Input(Clock())
    val rst = Input(Reset())
    val inst_type = Input(UInt(4.W))
    val inst_valid = Input(Bool())
    val alu_comp = Input(UInt(3.W))
    val funct = Input(UInt(5.W))
    val data_valid = Input(Bool())
    val inst_fetch = Output(Bool())
    val load_data = Output(Bool())
    val store_data = Output(Bool())
    val rd_en = Output(Bool())
    val rs1_en = Output(Bool())
    val rs2_en = Output(Bool())
    val rd_din_sel = Output(UInt(2.W))
    val pc_next_sel = Output(UInt(2.W))
    val alu_din1_sel = Output(UInt(2.W))
    val alu_din2_sel = Output(UInt(2.W))
    val alu_op = Output(UInt(4.W))
  })
}