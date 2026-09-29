plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("maven-publish")
    id("signing")
}
val variants = listOf("tiny", "small", "balanced", "full")
val apiJars = variants.associateWith { variant ->
    tasks.register<Jar>("${variant}ApiJar") {
        archiveBaseName.set("latex-mobile-$variant")
        archiveClassifier.set("javadoc")
        from("api")
    }
}
val releaseVersion = providers.gradleProperty("releaseVersion").getOrElse("0.1.0")
android {
    namespace = "org.latexmobile"
    compileSdk = 35
    defaultConfig {
        minSdk = 28
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        consumerProguardFiles("consumer-rules.pro")
        ndk { abiFilters += providers.gradleProperty("abis").getOrElse("armeabi-v7a,arm64-v8a,x86_64").split(",") }
    }
    packaging {
        jniLibs {
            val selected = providers.gradleProperty("abis").getOrElse("armeabi-v7a,arm64-v8a,x86_64").split(",")
            listOf("armeabi-v7a", "arm64-v8a", "x86_64").filter { it !in selected }.forEach {
                excludes += "**/$it/**"
            }
        }
    }
    flavorDimensions += "content"
    productFlavors { variants.forEach { create(it) { dimension = "content" } } }
    sourceSets { getByName("androidTest").assets.srcDir("../../examples"); variants.forEach {
        getByName(it).assets.srcDir("../../dist/bundles/$it")
        val nativeProfile = if (it == "full") "full" else "compact"
        getByName(it).jniLibs.srcDir("../../dist/native/android/$nativeProfile")
    } }
    publishing { variants.forEach { singleVariant("${it}Release") { withSourcesJar() } } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
}
// Refuse an AAR missing its selected native profile.
variants.forEach { variant ->
    tasks.matching { it.name.startsWith("merge${variant.replaceFirstChar(Char::uppercase)}") && it.name.endsWith("NativeLibs") }.configureEach {
        doFirst {
            val profile = if (variant == "full") "full" else "compact"
            providers.gradleProperty("abis").getOrElse("armeabi-v7a,arm64-v8a,x86_64").split(",").forEach { abi ->
                check(file("../../dist/native/android/$profile/$abi/liblatex_mobile.so").isFile) { "Run tools/build-native.sh android ($profile, $abi)." }
            }
        }
    }
}
variants.forEach { variant ->
    tasks.matching { it.name == "merge${variant.replaceFirstChar(Char::uppercase)}ReleaseAssets" || it.name == "merge${variant.replaceFirstChar(Char::uppercase)}DebugAssets" }.configureEach {
        doFirst { check(file("../../dist/bundles/$variant/texbundle/manifest.json").isFile) { "Run tools/release.py to prepare $variant." } }
    }
}
afterEvaluate {
    publishing {
        publications {
            variants.forEach { variant ->
                create<MavenPublication>(variant) {
                    from(components["${variant}Release"])
                    groupId = "io.github.snooplsm"
                    artifactId = "latex-mobile-$variant"
                    version = releaseVersion
                    artifact(apiJars.getValue(variant))
                    pom {
                        name.set("LaTeX Mobile ($variant)")
                        description.set("Offline LaTeX to PDF for Android. Original code is MIT; bundled components retain their licenses in assets/texbundle/licenses.")
                        url.set("https://github.com/snooplsm/pdf-latex-mobile")
                        licenses { license { name.set("MIT"); url.set("https://opensource.org/licenses/MIT") } }
                        developers { developer { id.set("snooplsm"); name.set("Ryan G"); url.set("https://github.com/snooplsm") } }
                        scm {
                            url.set("https://github.com/snooplsm/pdf-latex-mobile")
                            connection.set("scm:git:https://github.com/snooplsm/pdf-latex-mobile.git")
                            developerConnection.set("scm:git:ssh://git@github.com/snooplsm/pdf-latex-mobile.git")
                        }
                    }
                }
            }
        }
        repositories { maven { name = "staging"; url = uri("../../dist/maven") } }
    }
}

tasks.withType<Jar>().matching { it.name.startsWith("source") && it.name.endsWith("ReleaseJar") }.configureEach {
    metadataCharset = "UTF-8"
    filePermissions { unix("0644") }
    dirPermissions { unix("0755") }
    from("../../crates") { into("native/crates") }
    from("../../vendor") { into("native/vendor") }
    from(listOf("../../Cargo.toml", "../../Cargo.lock", "../../LICENSE", "../../THIRD_PARTY.md")) { into("native") }
    from("../../notices") { into("native/notices") }
    from("../../tools") { into("native/tools"); exclude("**/__pycache__/**") }
    from("../../experiments/licenses") { into("native/experiments/licenses") }
    from("../../include") { into("native/include") }
}

val signingKeyFile = providers.environmentVariable("MAVEN_SIGNING_KEY_FILE")
if (signingKeyFile.isPresent) {
    signing {
        val passwordFile = providers.environmentVariable("MAVEN_SIGNING_PASSWORD_FILE")
        val password = providers.environmentVariable("MAVEN_SIGNING_PASSWORD").orNull
            ?: passwordFile.orNull?.let { file(it).readText().trimEnd('\n', '\r') }
        useInMemoryPgpKeys(file(signingKeyFile.get()).readText(), password)
        afterEvaluate { sign(publishing.publications) }
    }
}
