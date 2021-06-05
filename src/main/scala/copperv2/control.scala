package copperv2

import chisel3._
import chisel3.util._

class ControlIO extends Bundle {
  val inst_type = Input(InstType())
  val inst_valid = Input(Bool())
  val alu_comp = Input(UInt(3.W))
  val funct = Input(Funct())
  val data_valid = Input(Bool())
  val inst_fetch = Output(Bool())
  val load_data = Output(Bool())
  val store_data = Output(Bool())
  val rd_en = Output(Bool())
  val rs1_en = Output(Bool())
  val rs2_en = Output(Bool())
  val rd_din_sel = Output(RdDinSel())
  val pc_next_sel = Output(PcNextSel())
  val alu_din1_sel = Output(AluDin1Sel())
  val alu_din2_sel = Output(AluDin2Sel())
  val alu_op = Output(AluOp())
}

class ControlUnit extends Module with RequireSyncReset {
  val io = IO(new ControlIO)
  val state = RegInit(State.RESET) 
  val state_next = WireDefault(State.RESET)
  val take_branch = WireDefault(false.B)
  val state_change_next = state =/= state_next
  val state_change = RegNext(state_change_next)
  io.alu_op := WireDefault(AluOp.NOP)
  io.pc_next_sel := WireDefault(PcNextSel.STALL)
  io.alu_din1_sel := WireDefault(AluDin1Sel.RS1)
  io.alu_din2_sel := WireDefault(AluDin2Sel.IMM)
  io.rd_din_sel := WireDefault(RdDinSel.IMM)
  io.inst_fetch := WireDefault(false.B)
  io.store_data := WireDefault(false.B)
  io.load_data := WireDefault(false.B)
  io.rs1_en := WireDefault(false.B)
  io.rs2_en := WireDefault(false.B)
  io.rd_en := WireDefault(false.B)
  switch (state) {
    is (State.RESET) {
      state_next := State.FETCH
    }
    is (State.FETCH) {
      when (io.inst_valid) {
        val sel = io.inst_type === InstType.JAL
        state_next := Mux(sel, State.EXEC, State.DECODE)
      } .otherwise {
        state_next := State.FETCH
      }
    }
    is (State.DECODE) {
      val sel = io.inst_type === InstType.IMM || io.inst_type === InstType.FENCE
      state_next := Mux(sel, State.FETCH, State.EXEC)
    }
    is (State.EXEC) {
      val sel = io.inst_type === InstType.STORE || io.inst_type === InstType.LOAD
      state_next := Mux(sel, State.MEM, State.FETCH)
    }
    is (State.MEM) {
      state_next := Mux(io.data_valid, State.FETCH, State.MEM)
    }
  }
}