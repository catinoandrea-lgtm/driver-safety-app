// Android Starter · Andrea Catino — Independent Researcher, Italy · 2026-11-01 18:10
// Compilazione: ./gradlew assembleDebug  (eseguita da GitHub Actions a ogni push)
// Uscita:       app/build/outputs/apk/debug/app-debug.apk

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Il numero di build di GitHub diventa versionCode: ogni APK nuovo si installa sopra il precedente.
val buildNumber = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()

android {
    namespace = "it.catino.starter"
    compileSdk = 35

    defaultConfig {
        applicationId = "it.catino.starter"
        minSdk = 26
        targetSdk = 35
        versionCode = buildNumber
        versionName = "0.1.$buildNumber"
    }

    // Chiave di debug fissa, salvata nel repository: tutte le build hanno la stessa firma,
    // quindi gli aggiornamenti si installano senza disinstallare. NON usarla per il Play Store.
    signingConfigs {
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
