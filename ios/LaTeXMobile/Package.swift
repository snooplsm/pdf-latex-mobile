// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "LaTeXMobile",
    platforms: [.iOS(.v15)],
    products: [.library(name: "LaTeXMobile", targets: ["LaTeXMobile"])],
    targets: [
        .binaryTarget(name: "CLatexMobile", path: "Artifacts/CLatexMobile.xcframework"),
        .target(name: "LaTeXMobile", dependencies: ["CLatexMobile"],
                resources: [.copy("Resources/texbundle")],
                linkerSettings: [.linkedLibrary("c++"), .linkedLibrary("z"), .linkedLibrary("iconv"), .linkedFramework("CoreText"), .linkedFramework("CoreGraphics"), .linkedFramework("CoreFoundation")])
    ]
)
