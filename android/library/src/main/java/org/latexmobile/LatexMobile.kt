package org.latexmobile

import android.content.Context
import android.net.Uri
import java.io.InputStream
import org.json.JSONObject
import java.io.File

object LatexMobile {
    init { System.loadLibrary("latex_mobile") }
    @JvmStatic private external fun compileNative(request: String): String

    data class Result(val pdf: File, val bytes: Long, val elapsedMs: Long, val log: String)

    sealed class Asset {
        data class FileSource(val file: File) : Asset()
        data class Bytes(val bytes: ByteArray) : Asset()
        data class ContentUri(val uri: Uri) : Asset()
        data class AppAsset(val path: String) : Asset()
        // Opened once during compile; the library always closes the returned stream.
        class Stream(val open: () -> InputStream) : Asset()
    }

    // Call on a worker thread. Bytes are staged without Base64 or JSON copies.
    fun compile(context: Context, source: String, output: File, assets: Map<String, ByteArray> = emptyMap()): Result =
        compileWithAssets(context, source, output, assets.mapValues { Asset.Bytes(it.value) })

    fun compileWithFiles(context: Context, source: String, output: File, assets: Map<String, File>): Result =
        compileWithAssets(context, source, output, assets.mapValues { Asset.FileSource(it.value) })

    // FileSource remains on disk. Other inputs stream to temporary files with a 64 KiB buffer.
    // Keep source files unchanged until this synchronous call returns.
    fun compileWithAssets(context: Context, source: String, output: File, assets: Map<String, Asset>): Result {
        require(assets.size <= 128) { "At most 128 assets are allowed" }
        assets.keys.forEach { name ->
            require(name.isNotEmpty() && !name.contains('\\') && !name.contains(':') && !name.contains('\u0000') &&
                name.split('/').all { it.isNotEmpty() && it != "." && it != ".." } &&
                name != "main.tex" && name != "main.pdf") { "Invalid asset path: $name" }
        }
        val bundle = installBundle(context.applicationContext)
        val staging = java.nio.file.Files.createTempDirectory(context.cacheDir.toPath(), "latex-assets-").toFile()
        try {
            val paths = JSONObject()
            var remaining = 256L * 1024 * 1024
            assets.entries.forEachIndexed { index, (name, asset) ->
                val file = if (asset is Asset.FileSource) {
                    require(asset.file.isFile) { "Asset must be a regular file: ${asset.file}" }
                    require(asset.file.length() <= remaining) { "Assets exceed 256 MiB" }
                    remaining -= asset.file.length()
                    asset.file
                } else {
                    val input = when (asset) {
                        is Asset.Bytes -> asset.bytes.inputStream()
                        is Asset.ContentUri -> context.contentResolver.openInputStream(asset.uri)
                            ?: error("Cannot open ${asset.uri}")
                        is Asset.AppAsset -> context.assets.open(asset.path)
                        is Asset.Stream -> asset.open()
                        is Asset.FileSource -> error("unreachable")
                    }
                    File(staging, index.toString()).also { destination ->
                        input.use { stream ->
                            destination.outputStream().use { sink ->
                                val buffer = ByteArray(64 * 1024)
                                while (true) {
                                    val count = stream.read(buffer)
                                    if (count == -1) break
                                    remaining -= count
                                    require(remaining >= 0) { "Assets exceed 256 MiB" }
                                    sink.write(buffer, 0, count)
                                }
                            }
                        }
                    }
                }
                paths.put(name, file.absolutePath)
            }
            val request = JSONObject().put("source", source)
                .put("bundle_path", bundle.absolutePath).put("output_path", output.absolutePath)
                .put("asset_files", paths)
            val response = JSONObject(compileNative(request.toString()))
            check(response.getBoolean("ok")) { "${response.optString("error")}\n${response.optString("log")}" }
            return Result(output, response.getLong("pdf_bytes"), response.getLong("elapsed_ms"), response.getString("log"))
        } finally {
            staging.deleteRecursively()
        }
    }

    @Synchronized
    private fun installBundle(context: Context): File {
        val hash = context.assets.open("texbundle/SHA256SUM").bufferedReader().use { it.readText().trim() }
        require(hash.matches(Regex("[0-9a-f]{64}"))) { "Invalid bundle fingerprint" }
        val directory = File(context.noBackupFilesDir, "latex-mobile/$hash")
        val ready = File(directory, ".ready")
        if (!ready.isFile) {
            directory.mkdirs()
            fun copy(path: String, target: File) {
                val children = context.assets.list(path).orEmpty()
                if (children.isEmpty()) {
                    context.assets.open(path).use { input -> target.outputStream().use { input.copyTo(it) } }
                } else {
                    target.mkdirs()
                    children.forEach { copy("$path/$it", File(target, it)) }
                }
            }
            copy("texbundle", directory)
            ready.writeText(hash)
        }
        return directory
    }
}
