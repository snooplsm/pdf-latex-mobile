// Use balanced or full. Run on a worker thread.
val source = context.assets.open("invoice.tex").bufferedReader().use { it.readText() }
val invoice = LatexMobile.compileWithAssets(context, source, File(context.filesDir, "invoice.pdf"),
    mapOf("logo.pdf" to LatexMobile.Asset.AppAsset("invoice.assets/logo.pdf")))

// Other inputs can be mixed in the same map:
val inputs = mapOf(
    "logo.pdf" to LatexMobile.Asset.FileSource(File(context.filesDir, "logo.pdf")),
    "photo.jpg" to LatexMobile.Asset.ContentUri(selectedUri),
    "chart.png" to LatexMobile.Asset.Stream { openChartStream() },
    "small.png" to LatexMobile.Asset.Bytes(smallImageBytes))
// Streams are opened during compile and closed by the library; temporary files are removed.
// Keep FileSource files unchanged until compileWithAssets returns.
