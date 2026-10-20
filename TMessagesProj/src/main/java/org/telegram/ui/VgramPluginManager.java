package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;

import org.telegram.messenger.LiteMode;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Registry and persistent state for trusted, bundled VGRAM plugins.
 * A plugin's behavior must explicitly check isEnabled() before running.
 */
public final class VgramPluginManager {
    private static final String PREFS = "vgram_plugins";

    private VgramPluginManager() { }

    private static final List<VgramPlugin> PLUGINS;
    static {
        ArrayList<VgramPlugin> plugins = new ArrayList<>();
        plugins.add(new BasicPlugin("liquid_glass", "Жидкое стекло",
                "Управляет эффектом Liquid Glass в поддерживаемых элементах.", true));
        plugins.add(new BasicPlugin("profile_badges", "Бейджи профиля",
                "Показывает бейджи VGRAM рядом с именем в профиле.", true));
        PLUGINS = Collections.unmodifiableList(plugins);
    }

    public static List<VgramPlugin> getPlugins() {
        return PLUGINS;
    }

    public static boolean isEnabled(Context context, String pluginId) {
        if (context == null || pluginId == null) {
            return false;
        }
        for (VgramPlugin plugin : PLUGINS) {
            if (plugin.getId().equals(pluginId)) {
                SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
                if ("liquid_glass".equals(pluginId) && !prefs.contains(pluginId)) {
                    return LiteMode.isEnabled(LiteMode.FLAG_LIQUID_GLASS);
                }
                return prefs.getBoolean(pluginId, plugin.isEnabledByDefault());
            }
        }
        return false;
    }

    public static void setEnabled(Context context, String pluginId, boolean enabled) {
        if (context == null || pluginId == null || !contains(pluginId)) {
            return;
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(pluginId, enabled).apply();

        if ("liquid_glass".equals(pluginId)) {
            LiteMode.toggleFlag(LiteMode.FLAG_LIQUID_GLASS, enabled);
            context.getSharedPreferences("vgram_appearance", Context.MODE_PRIVATE)
                    .edit().putBoolean("liquid_glass", enabled).apply();
        }
    }

    private static boolean contains(String pluginId) {
        for (VgramPlugin plugin : PLUGINS) {
            if (plugin.getId().equals(pluginId)) {
                return true;
            }
        }
        return false;
    }

    private static final class BasicPlugin implements VgramPlugin {
        private final String id;
        private final String name;
        private final String description;
        private final boolean enabledByDefault;

        BasicPlugin(String id, String name, String description, boolean enabledByDefault) {
            this.id = id;
            this.name = name;
            this.description = description;
            this.enabledByDefault = enabledByDefault;
        }

        @Override public String getId() { return id; }
        @Override public String getName() { return name; }
        @Override public String getDescription() { return description; }
        @Override public boolean isEnabledByDefault() { return enabledByDefault; }
    }
}
