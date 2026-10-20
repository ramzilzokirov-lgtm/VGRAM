package org.telegram.ui;

/**
 * Contract for a trusted, bundled VGRAM plugin.
 *
 * Plugins are compiled with the app. Do not load arbitrary APK/JAR code from storage.
 */
public interface VgramPlugin {
    String getId();
    String getName();
    String getDescription();
    boolean isEnabledByDefault();
}
