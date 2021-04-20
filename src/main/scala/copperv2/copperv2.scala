package copperv2

import chisel3._
import chisel3.util.Decoupled

class Cuv2Config {
  class BusConfig(
    var data_width: Int = 32, 
    var addr_width: Int = 32, 
    var resp_width: Int = 1
  )
  var bus = new BusConfig()
}

class Cuv2ReadChannel(config: Cuv2Config) extends Bundle {
  // Output
  val addr = Decoupled(UInt(config.bus.addr_width.W))
  // Input
  val data = Flipped(Decoupled(UInt(config.bus.data_width.W)))
}

class Cuv2WriteOutput(config: Cuv2Config) extends Bundle {
  val strobe_width = config.bus.data_width / 4
  val data = UInt(config.bus.data_width.W)
  val addr = UInt(config.bus.addr_width.W)
  val strobe = UInt(strobe_width.W)
}

class Cuv2WriteChannel(config: Cuv2Config) extends Bundle {
  // Output
  val req = Decoupled(new Cuv2WriteOutput(config))
  // Input
  val resp = Flipped(Decoupled(UInt(config.bus.resp_width.W)))
}

class Copperv2Bus(config: Cuv2Config) extends Bundle {
  val ir = new Cuv2ReadChannel(config)
  val dr = new Cuv2ReadChannel(config)
  val dw = new Cuv2WriteChannel(config)
}

class Copperv2 extends MultiIOModule {
  val config = new Cuv2Config
  val bus = IO(new Copperv2Bus(config))
  bus.ir.addr.valid := 0.U
  bus.ir.addr.bits := 0.U
  bus.ir.data.ready := 0.U
  bus.dr.addr.valid := 0.U
  bus.dr.addr.bits := 0.U
  bus.dr.data.ready := 0.U
  bus.dw.req.valid := 0.U
  bus.dw.req.bits.data := 0.U
  bus.dw.req.bits.addr := 0.U
  bus.dw.req.bits.strobe := 0.U
  bus.dw.resp.ready := 0.U
}

