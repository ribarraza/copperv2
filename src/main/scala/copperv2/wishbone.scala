package copperv2

import chisel3._
import dataclass.data

class CoppervBusSink(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  val ir = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dr = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dw = Flipped(new WriteChannel(addr_width=addr_width,data_width=addr_width,resp_width=resp_width))
}

class WishboneSource(addr_width: Int, data_width: Int) extends Bundle {
  val sel_width = data_width / 8
  val adr = Output(UInt(addr_width.W))
  val datwr = Output(UInt(data_width.W))
  val datrd = Input(UInt(data_width.W))
  val we = Output(Bool())
  val cyc = Output(Bool())
  val stb = Output(Bool())
  val ack = Input(Bool())
  val sel = Output(UInt(sel_width.W))
}

class WishboneAdapter(addr_width: Int, data_width: Int, resp_width: Int) extends Module with RequireSyncReset {
  val cpu = IO(Flipped(new CoppervBusSource(addr_width=addr_width,data_width=data_width,resp_width=resp_width)))
  val wb_d = IO(new WishboneSource(addr_width=addr_width,data_width=data_width))
  val wb_i = IO(new WishboneSource(addr_width=addr_width,data_width=data_width))
  cpu.dr.data.valid := 0.B
  cpu.dw.resp.valid := 0.B
  cpu.dw.resp.bits := 0.B
  cpu.ir.data.valid := 0.B
  cpu.ir.data.bits := 0.B
  cpu.dr.data.bits := 0.B
  cpu.dr.addr.ready := 0.B
  cpu.dw.req.ready := 0.B
  cpu.ir.addr.ready := 0.B
  wb_d.datwr := 0.B
  wb_d.adr := 0.B
  wb_d.sel := 0.B
  wb_d.we := 0.B
  wb_d.cyc := 0.B
  wb_d.stb := 0.B
  wb_i.datwr := 0.B
  wb_i.adr := 0.B
  wb_i.sel := 0.B
  wb_i.we := 0.B
  wb_i.cyc := 0.B
  wb_i.stb := 0.B
}
