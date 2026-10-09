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
        versionCode = 5
        versionName = "0.3.1-post-itf1-superior"
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