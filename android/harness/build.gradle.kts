plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "org.latexmobile.harness"
    compileSdk = 35
    defaultConfig { applicationId = "org.latexmobile.harness"; minSdk = 28; targetSdk = 35; versionCode = 1; versionName = "0.1.0" }
    flavorDimensions += "content"
    productFlavors { listOf("tiny", "small", "balanced", "full").forEach { create(it) { dimension = "content" } } }
    sourceSets.getByName("main").assets.srcDir("../../examples")
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation(project(":library")) }
