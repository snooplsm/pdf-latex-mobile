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
            val result = LatexMobile.compile(context, source, File(context.cacheDir, "$name.pdf"))
            ParcelFileDescriptor.open(result.pdf, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                PdfRenderer(fd).use { assertTrue("$name produced no pages", it.pageCount > 0) }
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
