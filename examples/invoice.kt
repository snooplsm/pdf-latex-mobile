// Bundle invoice.tex and invoice.assets/logo.pdf as app assets. Use balanced or full.
val source = context.assets.open("invoice.tex").bufferedReader().use { it.readText() }
val logo = context.assets.open("invoice.assets/logo.pdf").use { it.readBytes() }
// Run on a worker thread.
val invoice = LatexMobile.compile(context, source, File(context.filesDir, "invoice.pdf"),
    assets = mapOf("logo.pdf" to logo))
