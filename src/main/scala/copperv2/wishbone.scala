package copperv2

import chisel3._

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
//  val cpu = IO(Flipped(new CoppervBusSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH,resp_width=CoppervCore.RESP_WIDTH)))
//  val wb_dbus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
//  val wb_ibus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
//  cpu.dr.data.valid := 0.B
//  cpu.dw.resp.valid := 0.B
//  cpu.dw.resp.bits := 0.B
//  cpu.ir.data.valid := 0.B
//  cpu.ir.data.bits := 0.B
//  cpu.dr.data.bits := 0.B
//  cpu.dr.addr.ready := 0.B
//  cpu.dw.req.ready := 0.B
//  cpu.ir.addr.ready := 0.B
//  wb_dbus.datwr := 0.B
//  wb_dbus.adr := 0.B
//  wb_dbus.sel := 0.B
//  wb_dbus.we := 0.B
//  wb_dbus.cyc := 0.B
//  wb_dbus.stb := 0.B
//  wb_ibus.datwr := 0.B
//  wb_ibus.adr := 0.B
//  wb_ibus.sel := 0.B
//  wb_ibus.we := 0.B
//  wb_ibus.cyc := 0.B
//  wb_ibus.stb := 0.B
}
