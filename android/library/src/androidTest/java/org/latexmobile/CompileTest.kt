package org.latexmobile

import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.File

class CompileTest {
    @Test fun exportsParityInvoice() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val source = instrumentation.context.assets.open("invoice.tex").bufferedReader().use { it.readText() }
        val directory = File(context.filesDir, "parity").apply { mkdirs() }
        val logo = File(directory, "logo.pdf")
        instrumentation.context.assets.open("invoice.assets/logo.pdf").use { input ->
            logo.outputStream().use { input.copyTo(it) }
        }
        for (index in 1..2) {
            val output = File(directory, "invoice-$index.pdf")
            output.delete()
            LatexMobile.compileWithFiles(context, source, output, mapOf("logo.pdf" to logo))
            ParcelFileDescriptor.open(output, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                PdfRenderer(fd).use { assertEquals(1, it.pageCount) }
            }
        }
        assertArrayEquals(File(directory, "invoice-1.pdf").readBytes(), File(directory, "invoice-2.pdf").readBytes())
    }

    @Test fun compilesEverySelectedFeature() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val manifest = JSONObject(context.assets.open("texbundle/manifest.json").bufferedReader().use { it.readText() })
        val features = manifest.getJSONArray("features")
        for (index in 0 until features.length()) {
            val name = features.getString(index)
            val source = instrumentation.context.assets.open("$name.tex").bufferedReader().use { it.readText() }
            val assets = instrumentation.context.assets.list("$name.assets").orEmpty().associateWith { asset ->
                instrumentation.context.assets.open("$name.assets/$asset").use { it.readBytes() }
            }
            val sources = if (name == "invoice") listOf(source, source.replace("logo.pdf", "logo.png")) else listOf(source)
            for (document in sources) {
                val result = LatexMobile.compile(context, document, File(context.cacheDir, "$name.pdf"), assets)
                ParcelFileDescriptor.open(result.pdf, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                    PdfRenderer(fd).use {
                        assertTrue("$name produced no pages", it.pageCount > 0)
                        if (name == "invoice") assertEquals(1, it.pageCount)
                    }
                }
            }
        }
    }

    @Test fun createsReadablePdfOffline() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val result = LatexMobile.compile(context,
            "\\documentclass{article}\\begin{document}Android harness\\end{document}",
            File(context.cacheDir, "smoke.pdf"))
        assertTrue(result.bytes > 100)
        ParcelFileDescriptor.open(result.pdf, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
            PdfRenderer(fd).use { assertEquals(1, it.pageCount) }
        }
    }
    @Test fun acceptsFileUriStreamAndBytesWithoutBase64() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val file = File(context.cacheDir, "message.tex").apply { writeText("Disk-backed input") }
        val source = "\\documentclass{article}\\begin{document}\\input{message.tex}\\end{document}"
        var closed = false
        val inputs = listOf(
            LatexMobile.Asset.FileSource(file),
            LatexMobile.Asset.ContentUri(android.net.Uri.fromFile(file)),
            LatexMobile.Asset.Bytes("Small byte input".toByteArray()),
            LatexMobile.Asset.Stream {
                object : java.io.ByteArrayInputStream("Stream input".toByteArray()) {
                    override fun close() { closed = true; super.close() }
                }
            })
        inputs.forEach { asset ->
            val result = LatexMobile.compileWithAssets(context, source, File(context.cacheDir, "inputs.pdf"),
                mapOf("message.tex" to asset,
                    "bundle-hash.txt" to LatexMobile.Asset.AppAsset("texbundle/SHA256SUM")))
            assertTrue(result.bytes > 100)
        }
        assertTrue(closed)
        assertEquals("Disk-backed input", file.readText())
    }

    @Test fun failedStreamClosesAndRemovesStaging() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val before = context.cacheDir.list().orEmpty().filter { it.startsWith("latex-assets-") }.toSet()
        var closed = false
        val output = File(context.cacheDir, "failed-stream.pdf").apply { writeText("previous") }
        val result = runCatching {
            LatexMobile.compileWithAssets(context, "unused", output, mapOf("asset" to LatexMobile.Asset.Stream {
                object : java.io.InputStream() {
                    override fun read(): Int = throw java.io.IOException("stream failed")
                    override fun close() { closed = true }
                }
            }))
        }
        assertTrue(result.isFailure)
        assertTrue(closed)
        assertEquals("previous", output.readText())
        assertEquals(before, context.cacheDir.list().orEmpty().filter { it.startsWith("latex-assets-") }.toSet())
    }

    @Test fun invalidLatexDoesNotReplacePreviousPdf() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val output = File(context.cacheDir, "invalid.pdf").apply { writeText("previous") }
        val result = runCatching { LatexMobile.compile(context, "\\undefinedcommand\\bye", output) }
        assertTrue(result.isFailure)
        assertEquals("previous", output.readText())
    }
}
