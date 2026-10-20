package org.telegram.ui;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.R;
import org.telegram.messenger.browser.Browser;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

/**
 * VGRAM: screen "Разработчики".
 * Only real information is shown: no invented names or links.
 */
public class VgramDevelopersActivity extends BaseFragment {

    private static final String OWNER_NAME = "ramzilzokirov-lgtm";
    private static final String OWNER_URL = "https://github.com/ramzilzokirov-lgtm";

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setTitle("Разработчики");
        actionBar.setAllowOverlayTitle(true);
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        ScrollView scroll = new ScrollView(context);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));

        LinearLayout list = new LinearLayout(context);
        list.setOrientation(LinearLayout.VERTICAL);
        list.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(24));
        scroll.addView(list, LayoutHelper.createScroll(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP));

        list.addView(createCard(context, "R", OWNER_NAME, "Автор и владелец проекта VGRAM", OWNER_URL),
                LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 12));
        list.addView(createCard(context, "AI", "ChatGPT", "ИИ-помощник: идеи и техническое задание", null),
                LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 12));

        TextView footer = new TextView(context);
        footer.setText("VGRAM 0.1");
        footer.setTextSize(13);
        footer.setGravity(Gravity.CENTER);
        footer.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        list.addView(footer, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 12, 0, 0));

        fragmentView = scroll;
        return fragmentView;
    }

    private View createCard(Context context, String letters, String name, String role, final String url) {
        LinearLayout card = new LinearLayout(context);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16), AndroidUtilities.dp(16));

        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(AndroidUtilities.dp(20));
        bg.setColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        bg.setStroke(AndroidUtilities.dp(1), Theme.getColor(Theme.key_divider));
        card.setBackground(bg);

        // Avatar: circle with initials (no external images needed)
        TextView avatar = new TextView(context);
        avatar.setText(letters);
        avatar.setTextSize(18);
        avatar.setTypeface(Typeface.DEFAULT_BOLD);
        avatar.setGravity(Gravity.CENTER);
        avatar.setTextColor(0xFF24231F);
        GradientDrawable circle = new GradientDrawable();
        circle.setShape(GradientDrawable.OVAL);
        circle.setColor(0xFFC5B878);
        avatar.setBackground(circle);
        card.addView(avatar, LayoutHelper.createLinear(52, 52, 0, 0, 14, 0));

        LinearLayout texts = new LinearLayout(context);
        texts.setOrientation(LinearLayout.VERTICAL);

        TextView nameView = new TextView(context);
        nameView.setText(name);
        nameView.setTextSize(17);
        nameView.setTypeface(Typeface.DEFAULT_BOLD);
        nameView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        texts.addView(nameView, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));

        TextView roleView = new TextView(context);
        roleView.setText(role);
        roleView.setTextSize(14);
        roleView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        texts.addView(roleView, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 2, 0, 0));

        if (url != null) {
            TextView link = new TextView(context);
            link.setText("Открыть профиль на GitHub");
            link.setTextSize(14);
            link.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlueText));
            texts.addView(link, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 6, 0, 0));
            card.setOnClickListener(v -> Browser.openUrl(getParentActivity(), url));
        }

        card.addView(texts, LayoutHelper.createLinear(0, LayoutHelper.WRAP_CONTENT, 1f));
        return card;
    }
}
