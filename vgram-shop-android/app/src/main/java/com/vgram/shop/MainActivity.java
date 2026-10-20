package com.vgram.shop;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.content.Intent;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.widget.*;

public class MainActivity extends Activity {
    private final int bg = Color.rgb(16,17,19), panel = Color.rgb(29,30,33), yellow = Color.rgb(218,196,91), white = Color.rgb(245,245,242), muted = Color.rgb(165,166,169);
    private static final String BOT_USERNAME = "VGRAM2_bot";
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(bg); getWindow().setNavigationBarColor(bg);
        ScrollView scroll = new ScrollView(this); scroll.setBackgroundColor(bg);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(22),dp(28),dp(22),dp(28)); scroll.addView(root);
        TextView brand = text("VGRAM", 14, yellow, true); root.addView(brand);
        TextView title = text("SHOP", 34, white, true); LinearLayout.LayoutParams tp = params(-2,-2); tp.topMargin=dp(8); root.addView(title,tp);
        TextView subtitle = text("Твой магазин цифровых товаров", 15, muted, false); root.addView(subtitle,params(-2,-2));
        LinearLayout banner = card(); banner.setOrientation(LinearLayout.VERTICAL);
        TextView b1=text("🎁  Бесплатные +888",20,white,true); banner.addView(b1);
        TextView b2=text("До 2 000 выдач · один раз на аккаунт",13,muted,false); LinearLayout.LayoutParams p=params(-1,-2);p.topMargin=dp(8);banner.addView(b2,p);
        root.addView(banner,topMargin(params(-1,-2),dp(26)));
        LinearLayout paid=card(); paid.setOrientation(LinearLayout.VERTICAL); paid.addView(text("💎  Платные +888",20,white,true));
        TextView price=text("15 ⭐ за номер",15,yellow,true); LinearLayout.LayoutParams pp=params(-1,-2);pp.topMargin=dp(8);paid.addView(price,pp);
        TextView rate=text("Информационный курс: 5 ⭐ = 1 ₽",13,muted,false); paid.addView(rate,topMargin(params(-1,-2),dp(4)));
        root.addView(paid,topMargin(params(-1,-2),dp(12)));
        LinearLayout settings=card(); settings.setOrientation(LinearLayout.VERTICAL);
        settings.addView(text("Подключение к боту",17,white,true));
        TextView help=text("Подключён Telegram-бот: @VGRAM2_bot. Нажми кнопку ниже, чтобы открыть магазин.",13,muted,false); root.addView(settings,topMargin(params(-1,-2),dp(12)));
        settings.addView(help,topMargin(params(-1,-2),dp(8)));
        Button open=button("ОТКРЫТЬ @VGRAM2_bot В TELEGRAM"); settings.addView(open,topMargin(params(-1,dp(50)),dp(12)));
        open.setOnClickListener(v -> openBot());
        TextView note=text("Номера и оплата обрабатываются ботом. Не вводи здесь коды входа или пароли.",12,muted,false); root.addView(note,topMargin(params(-1,-2),dp(18)));
        TextView footer=text("VGRAM SHOP  •  VERSION 0.1",11,muted,true); footer.setGravity(Gravity.CENTER); root.addView(footer,topMargin(params(-1,-2),dp(28)));
        setContentView(scroll);
    }
    private void openBot() {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/" + BOT_USERNAME))); }
        catch(Exception e) { Toast.makeText(this,"Не удалось открыть Telegram",Toast.LENGTH_LONG).show(); }
    }
    private LinearLayout card(){ LinearLayout l=new LinearLayout(this); l.setPadding(dp(16),dp(16),dp(16),dp(16)); l.setBackground(shape(panel,18)); return l; }
    private TextView text(String s,int size,int color,boolean bold){ TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t; }
    private Button button(String s){ Button b=new Button(this);b.setText(s);b.setTextColor(Color.rgb(25,25,22));b.setTextSize(13);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setBackground(shape(yellow,14));return b; }
    private GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
    private LinearLayout.LayoutParams params(int w,int h){return new LinearLayout.LayoutParams(w,h);}
    private LinearLayout.LayoutParams topMargin(LinearLayout.LayoutParams p,int m){p.topMargin=m;return p;}
    private int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+0.5f);}
}
