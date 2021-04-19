package copperv2

import chisel3._
import chisel3.util.Decoupled

class Cuv2Config {
  object bus {
    val data_width = 32
    val addr_width = 32
    val resp_width = 1
    val strobe_width = data_width/8
  }
}

class Cuv2InputBundle(config: Cuv2Config) extends Bundle {
  val dr_data = UInt(config.bus.data_width.W)
  val dw_resp = UInt(config.bus.resp_width.W)
}

class Cuv2OutputBundle(config: Cuv2Config) extends Bundle {
  val dr_addr = UInt(config.bus.addr_width.W)
  val dw_addr = UInt(config.bus.addr_width.W)
  val dw_data = UInt(config.bus.addr_width.W)
  val dw_strobe = UInt(config.bus.strobe_width.W)
}


class Copperv2 extends MultiIOModule {
  val config = new Cuv2Config
  val input = IO(Flipped(Decoupled(new Cuv2InputBundle(config))))
  val output = IO(Decoupled(new Cuv2OutputBundle(config)))
}
