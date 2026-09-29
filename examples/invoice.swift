// Bundle invoice.tex and invoice.assets/logo.pdf as app resources. Use balanced or full.
let source = try String(contentsOf: Bundle.main.url(forResource: "invoice", withExtension: "tex")!, encoding: .utf8)
let logo = Bundle.main.url(forResource: "logo", withExtension: "pdf", subdirectory: "invoice.assets")!
let invoice = try await LaTeXMobile.compile(source,
    to: FileManager.default.temporaryDirectory.appendingPathComponent("invoice.pdf"),
    assetFiles: ["logo.pdf": logo])
