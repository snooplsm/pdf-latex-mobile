import Foundation
import CLatexMobile

public enum LaTeXMobile {
    public struct Result: Sendable {
        public let pdf: URL
        public let bytes: Int
        public let elapsedMilliseconds: Int
        public let log: String
    }
    public struct Failure: LocalizedError {
        public let message: String
        public var errorDescription: String? { message }
    }
    private struct Request: Encodable {
        let source: String
        let bundle_path: String
        let output_path: String
    }
    private struct Response: Decodable {
        let ok: Bool
        let error: String?
        let log: String
        let pdf_bytes: Int
        let elapsed_ms: Int
    }
    public static func compile(_ source: String, to output: URL) async throws -> Result {
        // The Rust side serializes its process-global engine state.
        try await Task.detached(priority: .userInitiated) {
            guard let bundle = Bundle.module.url(forResource: "texbundle", withExtension: nil) else {
                throw Failure(message: "Missing TeX bundle")
            }
            let data = try JSONEncoder().encode(Request(source: source, bundle_path: bundle.path, output_path: output.path))
            let json = String(decoding: data, as: UTF8.self)
            let response: Response = try json.withCString { input in
                guard let pointer = lm_compile(input) else { throw Failure(message: "Native allocation failed") }
                defer { lm_string_free(pointer) }
                return try JSONDecoder().decode(Response.self, from: Data(String(cString: pointer).utf8))
            }
            guard response.ok else { throw Failure(message: "\(response.error ?? "Compile failed")\n\(response.log)") }
            return Result(pdf: output, bytes: response.pdf_bytes, elapsedMilliseconds: response.elapsed_ms, log: response.log)
        }.value
    }
}
