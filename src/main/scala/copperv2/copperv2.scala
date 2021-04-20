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

class Cuv2ReadChannel(data_width: Int, addr_width: Int) extends Bundle {
  // Output
  val addr = Decoupled(UInt(addr_width.W))
  // Input
  val data = Flipped(Decoupled(UInt(data_width.W)))
}

class Cuv2WriteChannel(data_width: Int, addr_width: Int, resp_width: Int) extends Bundle {
  val strobe_width = data_width / 4
  // Output
  val data = Decoupled(UInt(data_width.W))
  val addr = Decoupled(UInt(addr_width.W))
  val strobe = Decoupled(UInt(strobe_width.W))
  // Input
  val resp = Flipped(Decoupled(UInt(resp_width.W)))
}

class Copperv2Bus(config: Cuv2Config) extends Bundle {
  val ir = new Cuv2ReadChannel(config.bus.data_width,config.bus.addr_width)
  val iw = new Cuv2WriteChannel(config.bus.data_width,config.bus.addr_width,config.bus.resp_width)
  val dr = new Cuv2ReadChannel(config.bus.data_width,config.bus.addr_width)
  val dw = new Cuv2WriteChannel(config.bus.data_width,config.bus.addr_width,config.bus.resp_width)
}

class Copperv2 extends MultiIOModule {
  val config = new Cuv2Config
  val io = IO(new Copperv2Bus(config))
  io.dw.strobe.bits := 0.U
  io.dw.data.bits := 0.U
  io.dw.data.valid := 0.U
  io.ir.addr.valid := 0.U
  io.iw.data.valid := 0.U
  io.dw.addr.valid := 0.U
  io.dw.strobe.valid := 0.U
  io.dr.addr.valid := 0.U
  io.dw.addr.bits := 0.U
  io.iw.addr.valid := 0.U
  io.iw.strobe.bits := 0.U
  io.iw.data.bits := 0.U
  io.ir.data.ready := 0.U
  io.dr.addr.bits := 0.U
  io.iw.addr.bits := 0.U
  io.dr.data.ready := 0.U
  io.iw.resp.ready := 0.U
  io.dw.resp.ready := 0.U
  io.ir.addr.bits := 0.U
  io.iw.strobe.valid := 0.U
}

