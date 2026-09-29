package org.latexmobile

import android.content.Context
import android.util.Base64
import org.json.JSONObject
import java.io.File

object LatexMobile {
    init { System.loadLibrary("latex_mobile") }
    @JvmStatic private external fun compileNative(request: String): String

    data class Result(val pdf: File, val bytes: Long, val elapsedMs: Long, val log: String)

    // Call on a worker thread. The native engine serializes simultaneous requests.
    fun compile(context: Context, source: String, output: File, assets: Map<String, ByteArray> = emptyMap()): Result {
        val bundle = installBundle(context.applicationContext)
        val encodedAssets = JSONObject()
        assets.forEach { (name, bytes) -> encodedAssets.put(name, Base64.encodeToString(bytes, Base64.NO_WRAP)) }
        val request = JSONObject().put("source", source)
            .put("bundle_path", bundle.absolutePath).put("output_path", output.absolutePath).put("assets", encodedAssets)
        val response = JSONObject(compileNative(request.toString()))
        check(response.getBoolean("ok")) { "${response.optString("error")}\n${response.optString("log")}" }
        return Result(output, response.getLong("pdf_bytes"), response.getLong("elapsed_ms"), response.getString("log"))
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
