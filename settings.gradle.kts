// Android Starter · Andrea Catino — Independent Researcher, Italy · 2026-11-01 18:10
// Compilazione: avviene su GitHub Actions (./gradlew assembleDebug), non serve Android Studio.

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "android-starter"
include(":app")
