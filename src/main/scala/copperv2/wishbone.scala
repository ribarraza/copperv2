package copperv2

import chisel3._

class CoppervBusSink(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  val ir = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dr = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dw = Flipped(new WriteChannel(addr_width=addr_width,data_width=addr_width,resp_width=resp_width))
}

class WishboneSource(addr_width: Int, data_width: Int) extends Bundle {
  val adr = Output(UInt(addr_width.W))
  val datwr = Output(UInt(data_width.W))
  val datrd = Input(UInt(data_width.W))
  val we = Output(Bool())
  val cyc = Output(Bool())
  val stb = Output(Bool())
  val ack = Input(Bool())
}

class WishboneAdapter extends MultiIOModule with RequireSyncReset {
  val cpu = IO(Flipped(new CoppervBusSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH,resp_width=CoppervCore.RESP_WIDTH)))
  val dbus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
  val ibus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
  cpu.dr.data.valid := 0.B
  cpu.dw.resp.valid := 0.B
  ibus.sel := 0.B
  ibus.we := 0.B
  cpu.dw.resp.bits := 0.B
  cpu.ir.data.valid := 0.B
  cpu.ir.data.bits := 0.B
  cpu.dr.data.bits := 0.B
  dbus.sel := 0.B
  ibus.datwr := 0.B
  cpu.dr.addr.ready := 0.B
  ibus.adr := 0.B
  cpu.dw.req.ready := 0.B
  dbus.datwr := 0.B
  dbus.we := 0.B
  dbus.adr := 0.B
  cpu.ir.addr.ready := 0.B
}
