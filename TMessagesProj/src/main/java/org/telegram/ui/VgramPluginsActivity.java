package org.telegram.ui;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.CompoundButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

/** Settings screen for built-in VGRAM plugins. */
public class VgramPluginsActivity extends BaseFragment {
    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setTitle("Плагины VGRAM");
        actionBar.setAllowOverlayTitle(true);
        actionBar.setActionBarMenuOnItemClick(new org.telegram.ui.ActionBar.ActionBar.ActionBarMenuOnItemClick() {
            @Override public void onItemClick(int id) {
                if (id == -1) finishFragment();
            }
        });

        ScrollView scroll = new ScrollView(context);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));
        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(24));
        scroll.addView(root, LayoutHelper.createScroll(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));

        TextView intro = new TextView(context);
        intro.setText("Встроенные расширения VGRAM. Выключенные плагины не должны выполнять свои функции.");
        intro.setTextSize(14);
        intro.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        root.addView(intro, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 14));

        for (VgramPlugin plugin : VgramPluginManager.getPlugins()) {
            LinearLayout card = new LinearLayout(context);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(14), AndroidUtilities.dp(12), AndroidUtilities.dp(14));
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(Theme.getColor(Theme.key_windowBackgroundWhite));
            bg.setCornerRadius(AndroidUtilities.dp(18));
            card.setBackground(bg);
            root.addView(card, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 10));

            LinearLayout labels = new LinearLayout(context);
            labels.setOrientation(LinearLayout.VERTICAL);
            TextView title = new TextView(context);
            title.setText(plugin.getName());
            title.setTextSize(16);
            title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
            title.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
            labels.addView(title, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));

            TextView description = new TextView(context);
            description.setText(plugin.getDescription());
            description.setTextSize(13);
            description.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
            labels.addView(description, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 4, 0, 0));
            card.addView(labels, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

            Switch toggle = new Switch(context);
            toggle.setContentDescription(plugin.getName());
            toggle.setChecked(VgramPluginManager.isEnabled(context, plugin.getId()));
            card.addView(toggle, LayoutHelper.createLinear(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, 12, 0, 0, 0));
            toggle.setOnCheckedChangeListener((CompoundButton button, boolean checked) ->
                    VgramPluginManager.setEnabled(context, plugin.getId(), checked));
            card.setOnClickListener(v -> toggle.setChecked(!toggle.isChecked()));
        }

        TextView note = new TextView(context);
        note.setText("Плагины сейчас встроены в APK. Загрузка сторонних APK/JAR и выполнение произвольного кода не поддерживаются.");
        note.setTextSize(12);
        note.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        root.addView(note, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 10, 0, 0));

        fragmentView = scroll;
        return fragmentView;
    }
}
