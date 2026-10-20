package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LiteMode;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

/** VGRAM appearance preferences: saved accent palette and Liquid Glass preference. */
public class VgramAppearanceActivity extends BaseFragment {
    private static final String PREFS = "vgram_appearance";
    private static final String KEY_ACCENT = "accent";
    private static final String KEY_GLASS = "liquid_glass";
    private int accent;
    private boolean glass = true;
    private LinearLayout palette;
    private TextView previewTitle;
    private TextView glassValue;

    private static final int[] COLORS = new int[] {
        0xFFC5B878, 0xFF8E9AAF, 0xFF9A8CB8, 0xFF7FAE9B,
        0xFFCB8F91, 0xFF7898C9, 0xFFB5A6A0, 0xFF9AA77D
    };

    @Override
    public View createView(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        accent = prefs.getInt(KEY_ACCENT, COLORS[0]);
        glass = LiteMode.isEnabled(LiteMode.FLAG_LIQUID_GLASS);
        applyAccent(accent);

        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setTitle("Оформление VGRAM");
        actionBar.setAllowOverlayTitle(true);
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override public void onItemClick(int id) {
                if (id == -1) finishFragment();
            }
        });

        ScrollView scroll = new ScrollView(context);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));
        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(28));
        scroll.addView(root, LayoutHelper.createScroll(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));

        TextView intro = text(context, "Material 3 • Liquid Glass", 22, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true);
        root.addView(intro, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 6));
        TextView desc = text(context, "Минимализм, мягкие поверхности и спокойные цвета. Выбери акцент VGRAM.", 14, Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2), false);
        root.addView(desc, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 18));

        LinearLayout card = new LinearLayout(context);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16));
        card.setBackground(cardBackground(accent, glass));
        root.addView(card, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 14));

        previewTitle = text(context, "Предпросмотр интерфейса", 17, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true);
        card.addView(previewTitle, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        TextView preview = text(context, "Стеклянная карточка · VGRAM", 14, Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2), false);
        preview.setPadding(0, AndroidUtilities.dp(10), 0, AndroidUtilities.dp(12));
        card.addView(preview, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        TextView chip = text(context, "Акцент", 13, Color.WHITE, true);
        chip.setGravity(Gravity.CENTER);
        chip.setPadding(AndroidUtilities.dp(18), AndroidUtilities.dp(8), AndroidUtilities.dp(18), AndroidUtilities.dp(8));
        chip.setBackground(pill(accent));
        card.addView(chip, LayoutHelper.createLinear(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT));

        root.addView(text(context, "Цвет акцента", 17, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true),
            LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 8, 0, 10));
        palette = new LinearLayout(context);
        palette.setOrientation(LinearLayout.HORIZONTAL);
        palette.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(palette, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, AndroidUtilities.dp(54), 0, 0, 0, 18));
        buildPalette(context);

        LinearLayout glassCard = new LinearLayout(context);
        glassCard.setOrientation(LinearLayout.VERTICAL);
        glassCard.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(14), AndroidUtilities.dp(16), AndroidUtilities.dp(14));
        glassCard.setBackground(cardBackground(accent, glass));
        root.addView(glassCard, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 16));
        TextView glassTitle = text(context, "Эффект жидкого стекла", 16, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true);
        glassCard.addView(glassTitle, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        glassValue = text(context, glass ? "Включён в поддерживаемых элементах интерфейса" : "Выключен", 13, Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2), false);
        glassValue.setPadding(0, AndroidUtilities.dp(5), 0, 0);
        glassCard.addView(glassValue, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        glassCard.setOnClickListener(v -> {
            glass = !glass;
            VgramPluginManager.setEnabled(context, "liquid_glass", glass);
            prefs.edit().putBoolean(KEY_GLASS, glass).apply();
            glassValue.setText(glass ? "Включён в поддерживаемых элементах интерфейса" : "Выключен");
            glassCard.setBackground(cardBackground(accent, glass));
            card.setBackground(cardBackground(accent, glass));
        });

        LinearLayout badges = new LinearLayout(context);
        badges.setOrientation(LinearLayout.VERTICAL);
        badges.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16));
        badges.setBackground(cardBackground(accent, glass));
        root.addView(badges, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        badges.addView(text(context, "Бейджи VGRAM", 17, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true),
            LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        badges.addView(text(context, "Бейджи, назначенные владельцем, отображаются рядом с именем в профиле. Управление доступно только владельцу через бота.", 14,
            Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2), false),
            LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 8, 0, 0));

        LinearLayout pluginsCard = new LinearLayout(context);
        pluginsCard.setOrientation(LinearLayout.VERTICAL);
        pluginsCard.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16));
        pluginsCard.setBackground(cardBackground(accent, glass));
        root.addView(pluginsCard, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 14, 0, 0));
        pluginsCard.addView(text(context, "Плагины VGRAM", 17, Theme.getColor(Theme.key_windowBackgroundWhiteBlackText), true),
            LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        pluginsCard.addView(text(context, "Включай и выключай встроенные расширения.", 14,
            Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2), false),
            LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 6, 0, 0));
        pluginsCard.setOnClickListener(v -> presentFragment(new VgramPluginsActivity()));

        fragmentView = scroll;
        return fragmentView;
    }

    private void applyAccent(int color) {
        Theme.setColor(Theme.key_windowBackgroundWhiteBlueText, color, false);
        Theme.setColor(Theme.key_featuredStickers_buttonText, color, false);
    }

    private void buildPalette(Context context) {
        palette.removeAllViews();
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        for (int color : COLORS) {
            TextView swatch = new TextView(context);
            swatch.setText(color == accent ? "✓" : "");
            swatch.setTextColor(Color.WHITE);
            swatch.setTextSize(18);
            swatch.setTypeface(Typeface.DEFAULT_BOLD);
            swatch.setGravity(Gravity.CENTER);
            GradientDrawable shape = new GradientDrawable();
            shape.setShape(GradientDrawable.OVAL);
            shape.setColor(color);
            if (color == accent) shape.setStroke(AndroidUtilities.dp(3), Theme.getColor(Theme.key_windowBackgroundWhite));
            swatch.setBackground(shape);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(AndroidUtilities.dp(36), AndroidUtilities.dp(36));
            lp.rightMargin = AndroidUtilities.dp(8);
            palette.addView(swatch, lp);
            swatch.setOnClickListener(v -> {
                accent = color;
                prefs.edit().putInt(KEY_ACCENT, accent).apply();
                applyAccent(accent);
                buildPalette(context);
                View card = ((View) previewTitle.getParent());
                card.setBackground(cardBackground(accent, glass));
            });
        }
    }

    private TextView text(Context context, String value, int size, int color, boolean bold) {
        TextView view = new TextView(context);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable cardBackground(int color, boolean glass) {
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(AndroidUtilities.dp(22));
        bg.setColor(glass ? ((color & 0x00FFFFFF) | 0x26000000) : Theme.getColor(Theme.key_windowBackgroundWhite));
        bg.setStroke(AndroidUtilities.dp(1), (color & 0x00FFFFFF) | 0x70000000);
        return bg;
    }

    private GradientDrawable pill(int color) {
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(AndroidUtilities.dp(50));
        bg.setColor(color);
        return bg;
    }
}
