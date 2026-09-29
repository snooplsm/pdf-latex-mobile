import XCTest
import PDFKit
@testable import LaTeXMobile

final class CompileTests: XCTestCase {
    func testEverySelectedFeature() async throws {
        let manifestURL = Bundle.module.url(forResource: "manifest", withExtension: "json", subdirectory: "texbundle")!
        let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: manifestURL)) as! [String: Any]
        let selected = manifest["features"] as! [String]
        for name in selected {
            let fixture = Bundle(for: Self.self).url(forResource: name, withExtension: "tex", subdirectory: "examples")!
            let source = try String(contentsOf: fixture, encoding: .utf8)
            let output = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".pdf")
            defer { try? FileManager.default.removeItem(at: output) }
            var assets: [String: Data] = [:]
            if let folder = Bundle(for: Self.self).url(forResource: "\(name).assets", withExtension: nil, subdirectory: "examples") {
                for file in try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil) {
                    assets[file.lastPathComponent] = try Data(contentsOf: file)
                }
            }
            let documents = name == "invoice" ? [source, source.replacingOccurrences(of: "logo.pdf", with: "logo.png")] : [source]
            for document in documents {
                _ = try await LaTeXMobile.compile(document, to: output, assets: assets)
                let pages = PDFDocument(url: output)?.pageCount ?? 0
                XCTAssertGreaterThan(pages, 0, name)
                if name == "invoice" { XCTAssertEqual(pages, 1) }
            }
        }
    }

    func testCreatesReadablePDFOffline() async throws {
        let output = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".pdf")
        defer { try? FileManager.default.removeItem(at: output) }
        let result = try await LaTeXMobile.compile("\\documentclass{article}\\begin{document}iOS harness\\end{document}", to: output)
        XCTAssertGreaterThan(result.bytes, 100)
        XCTAssertEqual(PDFDocument(url: output)?.pageCount, 1)
    }
    func testInvalidInputPreservesPreviousOutput() async throws {
        let output = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".pdf")
        defer { try? FileManager.default.removeItem(at: output) }
        try Data("previous".utf8).write(to: output)
        do {
            _ = try await LaTeXMobile.compile("\\undefinedcommand\\bye", to: output)
            XCTFail("Expected a compiler error")
        } catch { XCTAssertEqual(try Data(contentsOf: output), Data("previous".utf8)) }
    }
}
