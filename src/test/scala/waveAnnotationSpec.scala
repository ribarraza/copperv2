import firrtl._
import firrtl.options.CustomFileEmission
import firrtl.annotations.{SingleTargetAnnotation, ReferenceTarget}
import chisel3._
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}
import chisel3.util.Decoupled
import chisel3.experimental.{annotate, ChiselAnnotation}
import firrtl.annotations.TargetToken

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import copperv2.transforms.addWaveform

class Bar extends MultiIOModule {
  val in = IO(Flipped(Decoupled(UInt(8.W))))
  val out = IO(Decoupled(UInt(8.W)))
  addWaveform(out.valid)
  out <> in
}

class Foo extends MultiIOModule {
  val in = IO(Flipped(Decoupled(UInt(8.W))))
  val out = IO(Decoupled(UInt(8.W)))
  val the_bar = Module(new Bar)
  in <> the_bar.in
  out <> the_bar.out
}

class AddWaveformSpec extends AnyFlatSpec with Matchers {
  val dir = "test_run_dir"

  behavior of "Annotation to add waveforms to visualization tool"

  it should "produce TCL script for gtkwave" in {
    val tcl_body = """gtkwave::addSignalsFromList the_bar.out_valid"""
    val tcl_path = dir + "/gtkwave.tcl"
    (new ChiselStage)
      .execute(Array("--target-dir",dir),Seq(ChiselGeneratorAnnotation(() => new Foo)))

    FileUtils.getText(tcl_path) should be(tcl_body)
  }
}