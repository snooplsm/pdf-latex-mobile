package org.latexmobile

import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.File

class CompileTest {
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
    @Test fun invalidLatexDoesNotReplacePreviousPdf() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val output = File(context.cacheDir, "invalid.pdf").apply { writeText("previous") }
        val result = runCatching { LatexMobile.compile(context, "\\undefinedcommand\\bye", output) }
        assertTrue(result.isFailure)
        assertEquals("previous", output.readText())
    }
}
