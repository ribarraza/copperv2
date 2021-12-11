package copperv2

import chisel3._
import chisel3.util._

class ControlIO extends Bundle {
  val inst_type = Input(InstType())
  val inst_valid = Input(Bool())
  val alu_comp = Input(new AluComp)
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
  val alu_load = Output(Bool())
}

class ControlUnit extends Module with RequireSyncReset {
  def take_branch(funct: Funct.Type,alu_comp: AluComp): Bool = {
    MuxLookup(funct.asUInt,false.B,Array(
      Funct.EQ.asUInt   ->  alu_comp.EQ, 
      Funct.NEQ.asUInt  -> !alu_comp.EQ,
      Funct.LT.asUInt   ->  alu_comp.LT,
      Funct.GTE.asUInt  -> !alu_comp.LT,
      Funct.LTU.asUInt  ->  alu_comp.LTU,
      Funct.GTEU.asUInt -> !alu_comp.LTU,
    ))
  }
  def get_int_alu_op(funct: Funct.Type): AluOp.Type = {
    MuxLookup(funct.asUInt,AluOp.NOP,Array(
      Funct.ADD.asUInt  -> AluOp.ADD,
      Funct.SUB.asUInt  -> AluOp.SUB,
      Funct.SLL.asUInt  -> AluOp.SLL,
      Funct.SLT.asUInt  -> AluOp.SLT,
      Funct.SLTU.asUInt -> AluOp.SLTU,
      Funct.XOR.asUInt  -> AluOp.XOR,
      Funct.SRL.asUInt  -> AluOp.SRL,
      Funct.SRA.asUInt  -> AluOp.SRA,
      Funct.OR.asUInt   -> AluOp.OR,
      Funct.AND.asUInt  -> AluOp.AND,
    ))
  }
  val io = IO(new ControlIO)
  val state = RegInit(State.RESET) 
  val state_next = WireDefault(State.RESET)
  val state_change_next = state =/= state_next
  val state_change = RegNext(state_change_next)
  io.alu_op := WireDefault(AluOp.NOP)
  io.alu_load := WireDefault(false.B)
  io.pc_next_sel := WireDefault(PcNextSel.STALL)
  io.alu_din1_sel := WireDefault(AluDin1Sel.RS1)
  io.alu_din2_sel := WireDefault(AluDin2Sel.IMM)
  io.rd_din_sel := WireDefault(RdDinSel.NONE)
  io.inst_fetch := WireDefault(false.B)
  io.store_data := WireDefault(false.B)
  io.load_data := WireDefault(false.B)
  io.rs1_en := WireDefault(false.B)
  io.rs2_en := WireDefault(false.B)
  io.rd_en := WireDefault(false.B)
  //when (state_change_next) {
  state := state_next
  //}
  switch (state) {
    is (State.RESET) {
      state_next := State.FETCH
    }
    is (State.FETCH) {
      val to_decode = io.inst_valid
      state_next := Mux(to_decode, State.DECODE, State.FETCH)
    }
    is (State.DECODE) {
      val to_fetch = io.inst_type === InstType.IMM || io.inst_type === InstType.FENCE
      state_next := Mux(to_fetch, State.FETCH, State.EXEC)
    }
    is (State.EXEC) {
      val to_mem = io.inst_type === InstType.STORE || io.inst_type === InstType.LOAD
      state_next := Mux(to_mem, State.MEM, State.COMMIT)
    }
    is (State.MEM) {
      val to_commit = io.data_valid
      state_next := Mux(to_commit, State.COMMIT, State.MEM)
    }
    is (State.COMMIT) {
      state_next := State.FETCH
    }
  }
  switch (state) {
    is (State.FETCH) {
      io.inst_fetch := state_change
    }
    is (State.DECODE) {
      switch (io.inst_type) {
        is (InstType.IMM) {
          io.rd_en := true.B
          io.rd_din_sel := RdDinSel.IMM
          io.pc_next_sel := PcNextSel.INCR
        }
        is (InstType.INT_IMM,InstType.LOAD,InstType.JALR) {
          io.rs1_en := true.B;
        }
        is (InstType.INT_REG,InstType.BRANCH,InstType.STORE) {
          io.rs1_en := true.B;
          io.rs2_en := true.B;
        }
        is (InstType.FENCE) {
          io.pc_next_sel := PcNextSel.INCR
        }
      }
    }
    is (State.EXEC) {
      switch (io.inst_type) {
        is (InstType.INT_IMM,InstType.INT_REG) {
          io.alu_din1_sel := AluDin1Sel.RS1;
          io.alu_din2_sel := Mux(io.inst_type === InstType.INT_IMM,AluDin2Sel.IMM,AluDin2Sel.RS2)
          io.alu_op := get_int_alu_op(io.funct);
          io.alu_load := true.B
        }
        is (InstType.BRANCH) {
          io.alu_din1_sel := AluDin1Sel.RS1;
          io.alu_din2_sel := AluDin2Sel.RS2;
          io.alu_load := true.B
        }
        is (InstType.STORE, InstType.LOAD) {
          io.alu_din1_sel := AluDin1Sel.RS1;
          io.alu_din2_sel := AluDin2Sel.IMM;
          io.alu_op := AluOp.ADD;
          io.alu_load := true.B
        }
        is (InstType.JAL,InstType.AUIPC,InstType.JALR) {
          io.alu_din1_sel := AluDin1Sel.PC;
          io.alu_din2_sel := Mux(io.inst_type === InstType.AUIPC,AluDin2Sel.IMM,AluDin2Sel.CONST_4);
          io.alu_op := AluOp.ADD;
          io.alu_load := true.B
        }
      }
    }
    is (State.MEM) {
      switch (io.inst_type) {
        is (InstType.STORE) {io.store_data := state_change}
        is (InstType.LOAD)  {io.load_data := state_change}
      }
    }
    is (State.COMMIT) {
      switch (io.inst_type) {
        is (InstType.BRANCH) {
          io.pc_next_sel := Mux(take_branch(io.funct,io.alu_comp),PcNextSel.ADD_IMM,PcNextSel.INCR)
        }
        is (InstType.JAL,InstType.AUIPC,InstType.JALR) {
          io.pc_next_sel := MuxLookup(io.inst_type.asUInt,PcNextSel.INCR,Array(
            InstType.JAL.asUInt -> PcNextSel.ADD_IMM,
            InstType.JALR.asUInt -> PcNextSel.ADD_RS1_IMM,
          ))
          io.rd_en := true.B;
          io.rd_din_sel := RdDinSel.ALU;
        }
        is (InstType.INT_IMM,InstType.INT_REG) {
          io.pc_next_sel := PcNextSel.INCR;
          io.rd_en := true.B
          io.rd_din_sel := RdDinSel.ALU
        }
        is (InstType.LOAD,InstType.STORE) {
          io.pc_next_sel := PcNextSel.INCR
          when (io.inst_type === InstType.LOAD) {
            io.rd_en := true.B
            io.rd_din_sel := RdDinSel.MEM
          }
        }
      }
    }
  }
}



