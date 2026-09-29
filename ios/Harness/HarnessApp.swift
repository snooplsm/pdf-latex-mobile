import SwiftUI
import PDFKit
import LaTeXMobile

@main
struct HarnessApp: App {
    var body: some Scene { WindowGroup { ContentView() } }
}
struct ContentView: View {
    @State private var source = "\\documentclass{article}\n\\begin{document}\nHello from iOS!\n\\end{document}"
    @State private var status = "Ready — offline compilation"
    @State private var document: PDFDocument?
    @State private var busy = false
    var body: some View {
        VStack(alignment: .leading) {
            TextEditor(text: $source).font(.system(.body, design: .monospaced)).frame(height: 180)
            Button("Generate PDF") {
                let input = source
                busy = true
                status = "Compiling…"
                Task {
                    do {
                        let output = FileManager.default.temporaryDirectory.appendingPathComponent("example.pdf")
                        let result = try await LaTeXMobile.compile(input, to: output)
                        document = PDFDocument(url: result.pdf)
                        status = "\(result.bytes) bytes · \(result.elapsedMilliseconds) ms"
                    } catch { status = error.localizedDescription }
                    busy = false
                }
            }.disabled(busy)
            Text(status).font(.caption).textSelection(.enabled)
            PDFPreview(document: document)
        }.padding()
    }
}
struct PDFPreview: UIViewRepresentable {
    let document: PDFDocument?
    func makeUIView(context: Context) -> PDFView { let view = PDFView(); view.autoScales = true; return view }
    func updateUIView(_ view: PDFView, context: Context) { view.document = document }
}
