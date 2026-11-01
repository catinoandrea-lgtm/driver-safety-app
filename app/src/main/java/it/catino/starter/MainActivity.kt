/* Android Starter — schermata di prova della pipeline GitHub Actions
 * Andrea Catino — Independent Researcher, Italy · 2026-11-01 18:10
 * Compilazione: ./gradlew assembleDebug (su GitHub Actions)
 * Esecuzione:   installare app-debug.apk dalla pagina Releases del repository
 */
package it.catino.starter

import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val info = packageManager.getPackageInfo(packageName, 0)
        val text = TextView(this).apply {
            gravity = Gravity.CENTER
            textSize = 20f
            setPadding(48, 48, 48, 48)
            text = buildString {
                appendLine("Pipeline OK")
                appendLine()
                appendLine("Versione: ${info.versionName}")
                appendLine("Telefono: ${Build.MANUFACTURER} ${Build.MODEL}")
                append("Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            }
        }
        setContentView(text)
    }
}
