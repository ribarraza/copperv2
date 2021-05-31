package copperv2

import chisel3._
import chisel3.util.{Decoupled,MuxLookup,Cat}

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

class ReadChannel(addr_width: Int, data_width: Int) extends Bundle {
  // Output
  val addr = Decoupled(UInt(addr_width.W))
  // Input
  val data = Flipped(Decoupled(UInt(data_width.W)))
}

class WriteChannel(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  // Output
  val req = Decoupled(new Bundle {
    val strobe_width = data_width / 8
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
  val bus = IO(new CoppervBus(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH,resp_width=CoppervCore.RESP_WIDTH))
  val control = Module(new control_unit)
  val idec = Module(new idecoder)
  val regfile = Module(new register_file)
  val alu = Module(new arith_logic_unit)
  val inst = Reg(UInt())
  val inst_valid = RegInit(0.B)
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
  bus.ir.addr.bits := 0.U
  when (bus.ir.addr.ready) {
    bus.ir.addr.bits := pc
  }
  when (bus.ir.data.fire()) {
    inst := bus.ir.data.bits
    inst_valid := 1.B
  } .otherwise {
    inst_valid := 0.B
  }
  bus.ir.addr.valid := inst_fetch
  idec.io.inst := inst
  bus.ir.data.ready := 1.B;
  control.io.clk := clock
  control.io.rst := ~reset.asBool()
  control.io.inst_type := idec.io.inst_type
  control.io.inst_valid := inst_valid
  control.io.alu_comp := alu.io.alu_comp
  control.io.funct := idec.io.funct
  inst_fetch := control.io.inst_fetch
  regfile.io.clk := clock
  regfile.io.rst := ~reset.asBool()
  regfile.io.rd_en := control.io.rd_en
  regfile.io.rs1_en := control.io.rs1_en
  regfile.io.rs2_en := control.io.rs2_en
  regfile.io.rd := idec.io.rd
  regfile.io.rs1 := idec.io.rs1
  regfile.io.rs2 := idec.io.rs2
  val write_valid = RegInit(0.B)
  val write_addr = alu.io.alu_dout
  val write_offset = write_addr(1,0)
  val write_strobe = WireDefault(0.U(4.W))
  val write_data = WireDefault(0.U)
  when (idec.io.funct === 9.U) {
    write_strobe := "b0001".U << write_offset
    write_data   := regfile.io.rs2_dout(7,0) << (write_offset << 3.U)
  } .elsewhen(idec.io.funct === 10.U) {
    write_strobe := "b0011".U << write_offset
    write_data   := regfile.io.rs2_dout(15,0) << (write_offset << 3.U)
  } .elsewhen(idec.io.funct === 11.U) {
    write_strobe := "b1111".U
    write_data   := regfile.io.rs2_dout
  } 
  when (bus.dw.resp.fire()) {
    write_valid := bus.dw.resp.bits
  } .otherwise {
    write_valid := 0.B
  }
  val dw_req_fire = control.io.store_data && bus.dw.req.ready
  val dw_addr = RegInit(0.U)
  val dw_data = RegInit(0.U)
  val dw_strobe = RegInit(0.U)
  val dw_req_valid = RegInit(0.B)
  when (dw_req_fire) {
    dw_addr := Cat(write_addr(31,2),0.U(2.W))
    dw_data := write_data
    dw_strobe := write_strobe
    dw_req_valid := 1.B
  } .otherwise {
    dw_req_valid := 0.B
  }
  bus.dw.req.bits.addr := dw_addr
  bus.dw.req.bits.data := dw_data
  bus.dw.req.bits.strobe := dw_strobe
  bus.dw.req.valid := dw_req_valid
  val read_addr = alu.io.alu_dout
  val dr_req_fire = control.io.load_data && bus.dr.addr.ready
  val read_offset = Reg(UInt(2.W))
  val dr_addr = RegInit(0.U)
  val dr_addr_valid = RegInit(0.U)
  when (control.io.load_data) {
    read_offset <= read_addr(1,0)
  }
  when (dr_req_fire) {
    dr_addr := read_addr(31,2) << 2.U
    dr_addr_valid := 1.B
  } .otherwise {
    dr_addr_valid := 0.B
  }
  bus.dr.addr.bits := dr_addr
  bus.dr.addr.valid := dr_addr_valid
  val read_data = RegInit(0.U)
  val read_valid = RegInit(0.B)
  when (bus.dr.data.fire()) {
    read_data := bus.dr.data.bits
    read_valid := 1.B
  } .otherwise {
    read_valid := 0.B
  }
  val read_data_t = read_data >> (read_offset << 3)
  val ext_read_data = MuxLookup(idec.io.funct,0.S(32.W),Array(
    9.U -> read_data_t(7,0).asSInt,
    10.U -> read_data_t(15,0).asSInt,
    11.U -> read_data_t.asSInt,
    12.U -> read_data_t(7,0).zext,
    13.U -> read_data_t(15,0).zext,
  )).asUInt
  regfile.io.rd_din := MuxLookup(control.io.rd_din_sel,0.U,Array(
    0.U -> idec.io.imm,
    1.U -> alu.io.alu_dout,
    2.U -> ext_read_data
  ))
  alu.io.alu_op := control.io.alu_op
  alu.io.alu_din1 := MuxLookup(control.io.alu_din1_sel,0.U,Array(
    1.U -> regfile.io.rs1_dout,
    2.U -> pc,
  ))
  alu.io.alu_din2 := MuxLookup(control.io.alu_din2_sel,0.U,Array(
    1.U -> idec.io.imm,
    2.U -> regfile.io.rs2_dout,
    3.U -> 4.U,
  ))
  val dr_data_ready = RegInit(1.B)
  bus.dr.data.ready := dr_data_ready
  control.io.data_valid := write_valid || read_valid
  val dw_resp_ready = RegInit(1.B)
  bus.dw.resp.ready := dw_resp_ready
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
  val dw_strobe = IO(Output(UInt((CoppervCore.DATA_WIDTH / 8).W)))
  withClockAndReset(clk,~rst.asBool) {
    val core = Module(new Copperv2Core(config))
    core.bus.ir.addr.ready := ir_addr_ready
    ir_addr_valid          := core.bus.ir.addr.valid
    ir_addr                := core.bus.ir.addr.bits
    ir_data_ready          := core.bus.ir.data.ready
    core.bus.ir.data.valid := ir_data_valid
    core.bus.ir.data.bits  := ir_data
    core.bus.dr.addr.ready := dr_addr_ready
    dr_addr_valid          := core.bus.dr.addr.valid
    dr_addr                := core.bus.dr.addr.bits
    dr_data_ready          := core.bus.dr.data.ready
    core.bus.dr.data.valid := dr_data_valid
    core.bus.dr.data.bits  := dr_data
    core.bus.dw.req.ready  := dw_data_addr_ready
    dw_data_addr_valid     := core.bus.dw.req.valid
    dw_data                := core.bus.dw.req.bits.data
    dw_addr                := core.bus.dw.req.bits.addr
    dw_strobe              := core.bus.dw.req.bits.strobe
    dw_resp_ready          := core.bus.dw.resp.ready
    core.bus.dw.resp.valid := dw_resp_valid
    core.bus.dw.resp.bits  := dw_resp
  }
}