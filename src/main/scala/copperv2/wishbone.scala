package copperv2

import chisel3._

class CoppervBusSink(addr_width: Int, data_width: Int, resp_width: Int) extends Bundle {
  val ir = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dr = Flipped(new ReadChannel(addr_width=addr_width,data_width=addr_width))
  val dw = Flipped(new WriteChannel(addr_width=addr_width,data_width=addr_width,resp_width=resp_width))
}

class WishboneSource(addr_width: Int, data_width: Int) extends Bundle {
  val adr = Output(UInt(addr_width.W))
  val dat_write = Output(UInt(data_width.W))
  val dat_read = Input(UInt(data_width.W))
  val we = Output(Bool())
  val sel = Output(UInt(data_width.W))
}

class WishboneAdapter extends MultiIOModule with RequireSyncReset {
  val cpu = IO(Flipped(new CoppervBusSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH,resp_width=CoppervCore.RESP_WIDTH)))
  val dbus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
  val ibus = IO(new WishboneSource(addr_width=CoppervCore.ADDR_WIDTH,data_width=CoppervCore.DATA_WIDTH))
}
