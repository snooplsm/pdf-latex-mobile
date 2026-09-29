package org.latexmobile.harness

import android.content.Intent
import android.content.ActivityNotFoundException
import androidx.core.content.FileProvider
import android.app.Activity
import android.graphics.Typeface
import android.view.Gravity
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
        fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
        val preview = ImageView(this).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            setBackgroundColor(0xfff2f2f7.toInt())
            contentDescription = "Generated PDF preview"
        }
        val source = EditText(this).apply {
            setText("\\documentclass{article}\n\\begin{document}\nHello from Android!\n\\end{document}")
            gravity = Gravity.TOP or Gravity.START
            typeface = Typeface.MONOSPACE
            textSize = 14f
            isVerticalScrollBarEnabled = true
        }
        var inputAssets = emptyMap<String, ByteArray>()
        val status = TextView(this).apply {
            text = "Ready — offline compilation"
            textSize = 12f
            setTextIsSelectable(true)
        }
        var generatedPdf: File? = null
        val openPdf = Button(this).apply {
            text = "Open PDF"
            visibility = android.view.View.GONE
            setOnClickListener {
                generatedPdf?.let { file ->
                    val uri = FileProvider.getUriForFile(this@MainActivity, "$packageName.files", file)
                    try {
                        startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "application/pdf")
                            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
                    } catch (_: ActivityNotFoundException) {
                        status.text = "No PDF viewer installed. The preview is available below."
                    }
                }
            }
        }
        var generate: () -> Unit = {}
        var launchInvoice = intent.getStringExtra("example") == "invoice"
        val examples = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item,
                listOf("Basic", "Invoice · PDF logo", "Invoice · PNG logo"))
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
                override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                    generatedPdf = null
                    openPdf.visibility = android.view.View.GONE
                    preview.setImageDrawable(null)
                    status.text = if (position == 0) "Ready — offline compilation" else "Invoice requires balanced or full"
                    if (position == 0) {
                        inputAssets = emptyMap()
                        source.setText("\\documentclass{article}\n\\begin{document}\nHello from Android!\n\\end{document}")
                    } else {
                        val extension = if (position == 1) "pdf" else "png"
                        val name = "logo.$extension"
                        inputAssets = mapOf(name to assets.open("invoice.assets/$name").use { it.readBytes() })
                        source.setText(assets.open("invoice.tex").bufferedReader().use { it.readText() }
                            .replace("logo.pdf", name))
                        if (launchInvoice) {
                            launchInvoice = false
                            source.post { generate() }
                        }
                    }
                }
            }
        }
        val compile = Button(this).apply { text = "Generate PDF" }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            addView(examples)
            addView(source, LinearLayout.LayoutParams(-1, dp(180)))
            addView(LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(compile); addView(openPdf)
            })
            addView(status)
            addView(preview, LinearLayout.LayoutParams(-1, 0, 1f))
            setOnApplyWindowInsetsListener { view, insets ->
                @Suppress("DEPRECATION")
                view.setPadding(dp(16) + insets.systemWindowInsetLeft,
                    dp(16) + insets.systemWindowInsetTop, dp(16) + insets.systemWindowInsetRight,
                    dp(16) + insets.systemWindowInsetBottom)
                insets
            }
        }
        setContentView(layout)
        compile.setOnClickListener {
            val latex = source.text.toString()
            val files = inputAssets
            compile.isEnabled = false
            examples.isEnabled = false
            generatedPdf = null
            openPdf.visibility = android.view.View.GONE
            preview.setImageDrawable(null)
            status.text = "Compiling…"
            executor.execute {
                val result = runCatching {
                    val result = LatexMobile.compile(applicationContext, latex, File(File(filesDir, "pdfs").apply { mkdirs() }, "example.pdf"), assets = files)
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
                    examples.isEnabled = true
                    result.onSuccess { (pdf, bitmap) ->
                        status.text = "${pdf.bytes} bytes · ${pdf.elapsedMs} ms"
                        generatedPdf = pdf.pdf
                        openPdf.visibility = android.view.View.VISIBLE
                        preview.setImageBitmap(bitmap)
                    }.onFailure { status.text = it.message }
                }
            }
        }
        // Optional launch argument for opening the invoice demo directly.
        generate = { compile.performClick(); Unit }
        if (launchInvoice) examples.setSelection(1)
    }
    override fun onDestroy() { executor.shutdown(); super.onDestroy() }
}
