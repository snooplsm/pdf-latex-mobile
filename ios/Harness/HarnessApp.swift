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
    @State private var example = 0
    @State private var assets: [String: Data] = [:]
    private func loadExample() {
        document = nil
        if example == 0 {
            source = "\\documentclass{article}\n\\begin{document}\nHello from iOS!\n\\end{document}"
            assets = [:]
            return
        }
        do {
            guard let root = Bundle.main.url(forResource: "examples", withExtension: nil) else {
                throw NSError(domain: "Harness", code: 1, userInfo: [NSLocalizedDescriptionKey: "Missing invoice resources"])
            }
            let name = example == 1 ? "logo.pdf" : "logo.png"
            let text = try String(contentsOf: root.appendingPathComponent("invoice.tex"), encoding: .utf8)
            let logo = try Data(contentsOf: root.appendingPathComponent("invoice.assets/\(name)"))
            source = text.replacingOccurrences(of: "logo.pdf", with: name)
            assets = [name: logo]
            status = "Invoice requires balanced or full"
        } catch { status = error.localizedDescription }
    }
    var body: some View {
        VStack(alignment: .leading) {
            Picker("Example", selection: $example) {
                Text("Basic").tag(0)
                Text("Invoice · PDF logo").tag(1)
                Text("Invoice · PNG logo").tag(2)
            }.disabled(busy).onChange(of: example) { _ in loadExample() }
            TextEditor(text: $source).font(.system(.body, design: .monospaced)).frame(height: 180)
            Button("Generate PDF") {
                let input = source
                let files = assets
                busy = true
                status = "Compiling…"
                Task {
                    do {
                        let output = FileManager.default.temporaryDirectory.appendingPathComponent("example.pdf")
                        let result = try await LaTeXMobile.compile(input, to: output, assets: files)
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
