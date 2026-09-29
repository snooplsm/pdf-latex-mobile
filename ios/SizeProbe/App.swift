import SwiftUI
#if WITH_LATEX
import LaTeXMobile
#endif

@main
struct SizeProbe: App {
    var body: some Scene { WindowGroup { ProbeView() } }
}

struct ProbeView: View {
    @State private var source = #"\documentclass{article}\begin{document}Size probe\end{document}"#
    @State private var status = "Ready"
    var body: some View {
        VStack {
            TextEditor(text: $source)
            Button("Generate PDF") {
                Task {
#if WITH_LATEX
                    do {
                        let output = FileManager.default.temporaryDirectory.appendingPathComponent("probe.pdf")
                        let result = try await LaTeXMobile.compile(source, to: output)
                        status = "\(result.bytes) bytes"
                    } catch { status = error.localizedDescription }
#else
                    status = "Baseline"
#endif
                }
            }
            Text(status)
        }.padding()
    }
}
