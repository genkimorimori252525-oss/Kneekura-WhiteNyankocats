plugins {
    id("com.android.application")
}

android {
    namespace = "jp.kneekura.whitenyankocats"
    compileSdk = 35

    defaultConfig {
        applicationId = "jp.kneekura.whitenyankocats"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0-stage-alpha"
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}