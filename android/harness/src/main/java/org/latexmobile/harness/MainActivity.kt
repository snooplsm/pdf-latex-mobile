package org.latexmobile.harness

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.widget.*
import org.latexmobile.LatexMobile
import java.io.File
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val source = EditText(this).apply {
            setText("\\documentclass{article}\n\\begin{document}\nHello from Android!\n\\end{document}")
            minLines = 5
        }
        val status = TextView(this)
        val preview = ImageView(this).apply { adjustViewBounds = true }
        val compile = Button(this).apply { text = "Generate PDF" }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
            addView(source); addView(compile); addView(status); addView(preview)
        }
        setContentView(ScrollView(this).apply { addView(layout) })
        compile.setOnClickListener {
            val latex = source.text.toString()
            compile.isEnabled = false
            status.text = "Compiling offline…"
            executor.execute {
                val result = runCatching {
                    val result = LatexMobile.compile(applicationContext, latex, File(filesDir, "example.pdf"))
                    val bitmap = ParcelFileDescriptor.open(result.pdf, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                        PdfRenderer(fd).use { renderer ->
                            renderer.openPage(0).use { page ->
                                Bitmap.createBitmap(page.width * 2, page.height * 2, Bitmap.Config.ARGB_8888).also {
                                    it.eraseColor(android.graphics.Color.WHITE)
                                    page.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                                }
                            }
                        }
                    }
                    result to bitmap
                }
                runOnUiThread {
                    compile.isEnabled = true
                    result.onSuccess { (pdf, bitmap) ->
                        status.text = "${pdf.bytes} bytes · ${pdf.elapsedMs} ms\n${pdf.pdf}"
                        preview.setImageBitmap(bitmap)
                    }.onFailure { status.text = it.message }
                }
            }
        }
    }
    override fun onDestroy() { executor.shutdown(); super.onDestroy() }
}
