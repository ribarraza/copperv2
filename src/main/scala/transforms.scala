package copperv2
package transforms

import firrtl._
import firrtl.options.CustomFileEmission
import firrtl.annotations.{SingleTargetAnnotation, ReferenceTarget}
import chisel3._
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}
import chisel3.util.Decoupled
import chisel3.experimental.{annotate, ChiselAnnotation}
import firrtl.annotations.TargetToken

case class WaveformAnnotation(target: ReferenceTarget)
    extends SingleTargetAnnotation[ReferenceTarget]
    with CustomFileEmission {
  def duplicate(n: ReferenceTarget) = this.copy(n)

  // API for serializing a custom metadata file
  // Note that multiple of this annotation will collide which is an error, not handled in this example
  protected def baseFileName(annotations: AnnotationSeq): String = "my_metadata"
  protected def suffix: Option[String] = Some(".txt")
  def string_path: String = (target.path.map(seq => seq._1.value) :+ target.ref).mkString(".")
  def getBytes: Iterable[Byte] = {
    s"Annotated signal: ${string_path}".getBytes
  }
}

object addWaveform {
  def apply[T <: Data](data: T): T = {
    annotate(new ChiselAnnotation {
      def toFirrtl = WaveformAnnotation(data.toAbsoluteTarget)
    })
    data
  }
}
