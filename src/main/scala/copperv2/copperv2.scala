package copperv2

import chisel3._
import chisel3.util.Decoupled

class Cuv2Config {
  class BusConfig(
    data_width: Int = 32, 
    addr_width: Int = 32, 
    resp_width: Int = 1
  )
  val bus = new BusConfig()
}

//class Cuv2ReadChannel(data_width: Int, addr_width: Int) extends Bundle {
//  // Output
//  val addr = Decoupled(UInt(addr_width.W))
//  // Input
//  val data = Flipped(Decoupled(UInt(data_width.W)))
//}
//
//class Cuv2WriteChannel(data_width: Int, addr_width: Int, resp_width: Int) extends Bundle {
//  val strobe_width = data_width / 4
//  printf(p"strobe_width = $strobe_width")
//  // Output
//  val data = Decoupled(UInt(data_width.W))
//  val addr = Decoupled(UInt(addr_width.W))
//  val strobe = Decoupled(UInt(strobe_width.W))
//  // Input
//  val resp = Flipped(Decoupled(UInt(resp_width.W)))
//}

//class Cuv2BusChannel(config: Cuv2Config#BusConfig) extends Bundle {
//  val r = new Cuv2ReadChannel(config.data_width,config.addr_width)
//  val w = new Cuv2WriteChannel(config.data_width,config.addr_width,config.resp_width)
//}

class Copperv2Bus(config: Cuv2Config) extends Bundle {
  //val i = new Cuv2BusChannel(config.bus)
  //val d = new Cuv2BusChannel(config.bus)
  printf(p"config.bus.data_width = ${config.bus.data_width}")
}

class Copperv2 extends MultiIOModule {
  val config = new Cuv2Config
  val io = IO(new Copperv2Bus(config))
}

