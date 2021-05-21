package copperv2

import chisel3._
import chisel3.util.{Decoupled,MuxLookup}

class Cuv2Config {
  var pc_init = 0
}

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
    val clk = Input(Bool())
    val rst = Input(Bool())
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

class ReadChannel(addr_width: Int, data_width: Int) extends Bundle {
  // Output
  val addr = Decoupled(UInt(addr_width.W))
  // Input
  val data = Flipped(Decoupled(UInt(data_width.W)))
}

class WriteChannel(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  // Output
  val req = Decoupled(new Bundle {
    val strobe_width = data_width / 4
    val data = UInt(data_width.W)
    val addr = UInt(addr_width.W)
    val strobe = UInt(strobe_width.W)
  })
  // Input
  val resp = Flipped(Decoupled(UInt(resp_width.W)))
}

class CoppervBus(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  val ir = new ReadChannel(addr_width=addr_width,data_width=addr_width)
  val dr = new ReadChannel(addr_width=addr_width,data_width=addr_width)
  val dw = new WriteChannel(addr_width=addr_width,data_width=addr_width,resp_width=resp_width)
}

object CoppervCore {
  val DATA_WIDTH: Int = 32
  val ADDR_WIDTH: Int = 32
  val RESP_WIDTH: Int = 1
}

class Copperv2Core(config: Cuv2Config = new Cuv2Config()) extends MultiIOModule with RequireSyncReset {
  val bus = new CoppervBus(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH,resp_width=CoppervCore.RESP_WIDTH)
  val ir = IO(bus.ir)
  val dr = IO(bus.dr)
  val dw = IO(bus.dw)
  ir.addr.valid := 0.U
  ir.addr.bits := 0.U
  ir.data.ready := 0.U
  dr.addr.valid := 0.U
  dr.addr.bits := 0.U
  dr.data.ready := 0.U
  dw.req.valid := 0.U
  dw.req.bits.data := 0.U
  dw.req.bits.addr := 0.U
  dw.req.bits.strobe := 0.U
  dw.resp.ready := 0.U
  val control = Module(new control_unit)
  val idec = Module(new idecoder)
  val regfile = Module(new register_file)
  val alu = Module(new arith_logic_unit)
  val instruction = Reg(UInt())
  val inst_fetch = Wire(UInt())
  val pc = RegInit(config.pc_init.U)
  val pc_en = MuxLookup(control.io.pc_next_sel,true.B,Array(0.U -> false.B))
  val pc_next = MuxLookup(control.io.pc_next_sel,0.U,Array(
    1.U -> (pc + 4.U),
    2.U -> (pc + idec.io.imm),
    3.U -> (regfile.io.rs1_dout + idec.io.imm),
  ))
  when (pc_en) {
    pc := pc_next
  }
  when (ir.addr.ready) {
    ir.addr.bits := pc
  }
  when (ir.data.fire()) {
    instruction := ir.data.bits
  }
  ir.addr.valid := inst_fetch
  idec.io.inst := instruction
  inst_fetch := control.io.inst_fetch
  control.io.clk := clock
  control.io.rst := ~reset.asBool()
}

class copperv2 extends RawModule {
  val config = new Cuv2Config
  val clk = IO(Input(Clock()))
  val rst = IO(Input(Bool()))
  val ir_data_valid = IO(Input(Bool()))
  val ir_addr_ready = IO(Input(Bool()))
  val ir_data = IO(Input(UInt(CoppervCore.DATA_WIDTH.W)))
  val dr_data_valid = IO(Input(Bool()))
  val dr_addr_ready = IO(Input(Bool()))
  val dw_data_addr_ready = IO(Input(Bool()))
  val dw_resp_valid = IO(Input(Bool()))
  val dr_data = IO(Input(UInt(CoppervCore.DATA_WIDTH.W)))
  val dw_resp = IO(Input(UInt(CoppervCore.RESP_WIDTH.W)))
  val ir_data_ready = IO(Output(Bool())) 
  val ir_addr_valid = IO(Output(Bool()))
  val ir_addr = IO(Output(UInt(CoppervCore.ADDR_WIDTH.W)))
  val dr_data_ready = IO(Output(Bool()))
  val dr_addr_valid = IO(Output(Bool()))
  val dw_data_addr_valid = IO(Output(Bool()))
  val dw_resp_ready = IO(Output(Bool()))
  val dr_addr = IO(Output(UInt(CoppervCore.ADDR_WIDTH.W)))
  val dw_data = IO(Output(UInt(CoppervCore.DATA_WIDTH.W)))
  val dw_addr = IO(Output(UInt(CoppervCore.ADDR_WIDTH.W)))
  val dw_strobe = IO(Output(UInt((CoppervCore.DATA_WIDTH / 4).W)))
  withClockAndReset(clk,~rst.asBool) {
    val copperv2_core = Module(new Copperv2Core(config))
    copperv2_core.ir.addr.ready := ir_addr_ready
    ir_addr_valid               := copperv2_core.ir.addr.valid
    ir_addr                     := copperv2_core.ir.addr.bits
    ir_data_ready               := copperv2_core.ir.data.ready
    copperv2_core.ir.data.valid := ir_data_valid
    copperv2_core.ir.data.bits  := ir_data
    copperv2_core.dr.addr.ready := dr_addr_ready
    dr_addr_valid               := copperv2_core.dr.addr.valid
    dr_addr                     := copperv2_core.dr.addr.bits
    dr_data_ready               := copperv2_core.dr.data.ready
    copperv2_core.dr.data.valid := dr_data_valid
    copperv2_core.dr.data.bits  := dr_data
    copperv2_core.dw.req.ready  := dw_data_addr_ready
    dw_data_addr_valid          := copperv2_core.dw.req.valid
    dw_data                     := copperv2_core.dw.req.bits.data
    dw_addr                     := copperv2_core.dw.req.bits.addr
    dw_strobe                   := copperv2_core.dw.req.bits.strobe
    dw_resp_ready               := copperv2_core.dw.resp.ready
    copperv2_core.dw.resp.valid := dw_resp_valid
    copperv2_core.dw.resp.bits  := dw_resp
  }
}