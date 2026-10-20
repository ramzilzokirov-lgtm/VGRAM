package org.telegram.ui;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.content.SharedPreferences;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class VgramServerActivity extends Activity {
    private static final String API = "https://vgram-31xt.onrender.com";
    private static final String PREFS = "vgram_server_session";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText usernameInput, passwordInput, recipientInput, messageInput;
    private TextView statusView, inboxView;
    private String token = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        token = getSharedPreferences(PREFS, MODE_PRIVATE).getString("token", "");
        buildUi();
        if (!token.isEmpty()) {
            statusView.setText("Сессия сохранена. Обнови входящие сообщения.");
            loadInbox();
        }
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(18), dp(20), dp(24));
        root.setBackgroundColor(Color.rgb(20, 20, 24));
        scroll.addView(root);
        setContentView(scroll);

        TextView title = new TextView(this);
        title.setText("VGRAM • Свой сервер");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(title, matchWrap());

        statusView = new TextView(this);
        statusView.setText("Сервер: " + API + "\nСоздай аккаунт или войди.");
        statusView.setTextColor(Color.LTGRAY);
        statusView.setTextSize(14);
        statusView.setPadding(0, dp(10), 0, dp(14));
        root.addView(statusView, matchWrap());

        usernameInput = field("Логин (3–32 символа)");
        passwordInput = field("Пароль (минимум 10 символов)");
        passwordInput.setInputType(129);
        root.addView(usernameInput, matchWrap());
        root.addView(passwordInput, matchWrap());

        Button register = button("СОЗДАТЬ VGRAM-АККАУНТ");
        register.setOnClickListener(v -> auth("register"));
        root.addView(register, matchWrap());

        Button login = button("ВОЙТИ");
        login.setOnClickListener(v -> auth("login"));
        root.addView(login, matchWrap());

        Button logout = button("ВЫЙТИ И УДАЛИТЬ СЕССИЮ");
        logout.setOnClickListener(v -> {
            token = "";
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove("token").apply();
            statusView.setText("Сессия удалена с устройства.");
            inboxView.setText("");
        });
        root.addView(logout, matchWrap());

        TextView separator = new TextView(this);
        separator.setText("ЛИЧНЫЕ СООБЩЕНИЯ");
        separator.setTextColor(Color.rgb(245, 205, 70));
        separator.setTextSize(15);
        separator.setPadding(0, dp(22), 0, dp(8));
        root.addView(separator, matchWrap());

        recipientInput = field("ID получателя, например VG-1A2B3C4D");
        messageInput = field("Текст сообщения");
        root.addView(recipientInput, matchWrap());
        root.addView(messageInput, matchWrap());

        Button send = button("ОТПРАВИТЬ СООБЩЕНИЕ");
        send.setOnClickListener(v -> sendMessage());
        root.addView(send, matchWrap());

        Button refresh = button("ОБНОВИТЬ ВХОДЯЩИЕ");
        refresh.setOnClickListener(v -> loadInbox());
        root.addView(refresh, matchWrap());

        inboxView = new TextView(this);
        inboxView.setTextColor(Color.WHITE);
        inboxView.setTextSize(14);
        inboxView.setPadding(0, dp(12), 0, dp(12));
        root.addView(inboxView, matchWrap());
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(-1, -2);
    }

    private int dp(float value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private EditText field(String hint) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setTextColor(Color.WHITE);
        edit.setHintTextColor(Color.GRAY);
        edit.setSingleLine(true);
        edit.setPadding(dp(12), dp(6), dp(12), dp(6));
        return edit;
    }

    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        return b;
    }

    private JSONObject request(String path, String method, JSONObject payload, boolean authenticated) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(API + path).openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setRequestProperty("Accept", "application/json");
        if (payload != null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            try (OutputStream out = conn.getOutputStream()) {
                out.write(payload.toString().getBytes(StandardCharsets.UTF_8));
            }
        }
        if (authenticated && !token.isEmpty()) {
            conn.setRequestProperty("Authorization", "Bearer " + token);
        }
        int code = conn.getResponseCode();
        InputStream stream = code >= 200 && code < 400 ? conn.getInputStream() : conn.getErrorStream();
        StringBuilder body = new StringBuilder();
        if (stream != null) {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) body.append(line);
            }
        }
        conn.disconnect();
        JSONObject result = body.length() == 0 ? new JSONObject() : new JSONObject(body.toString());
        if (code < 200 || code >= 300) {
            throw new Exception(result.optString("detail", "HTTP " + code));
        }
        return result;
    }

    private void runNetwork(String working, NetworkTask task) {
        statusView.setText(working);
        executor.execute(() -> {
            try {
                String result = task.run();
                runOnUiThread(() -> statusView.setText(result));
            } catch (Exception e) {
                runOnUiThread(() -> statusView.setText("Ошибка: " + e.getMessage()));
            }
        });
    }

    private interface NetworkTask { String run() throws Exception; }

    private void auth(String mode) {
        String username = usernameInput.getText().toString().trim();
        String password = passwordInput.getText().toString();
        if (username.isEmpty() || password.isEmpty()) {
            statusView.setText("Введи логин и пароль.");
            return;
        }
        runNetwork("Подключение к VGRAM-серверу…", () -> {
            JSONObject data = new JSONObject();
            data.put("username", username);
            data.put("password", password);
            JSONObject result = request("/auth/" + mode, "POST", data, false);
            token = result.getString("access_token");
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("token", token).apply();
            String id = result.optString("vgram_id", "");
            runOnUiThread(() -> {
                statusView.setText("Вход выполнен. Твой VGRAM ID: " + id);
                loadInbox();
            });
            return "Вход выполнен. Твой VGRAM ID: " + id;
        });
    }

    private void sendMessage() {
        String recipient = recipientInput.getText().toString().trim();
        String body = messageInput.getText().toString().trim();
        if (token.isEmpty()) {
            statusView.setText("Сначала войди в VGRAM-аккаунт.");
            return;
        }
        if (recipient.isEmpty() || body.isEmpty()) {
            statusView.setText("Введи ID получателя и текст.");
            return;
        }
        runNetwork("Отправка сообщения…", () -> {
            JSONObject data = new JSONObject();
            data.put("recipient_id", recipient);
            data.put("body", body);
            JSONObject result = request("/chat/send", "POST", data, true);
            return "Сообщение сохранено на сервере. ID: " + result.optLong("message_id");
        });
    }

    private void loadInbox() {
        if (token.isEmpty()) return;
        runNetwork("Загрузка входящих…", () -> {
            JSONObject result = request("/chat/inbox?limit=50", "GET", null, true);
            JSONArray messages = result.optJSONArray("messages");
            StringBuilder text = new StringBuilder();
            if (messages == null || messages.length() == 0) {
                text.append("Входящих сообщений пока нет.");
            } else {
                for (int i = 0; i < messages.length(); i++) {
                    JSONObject m = messages.getJSONObject(i);
                    text.append("От: ").append(m.optString("sender_id")).append("\n")
                        .append(m.optString("body")).append("\n")
                        .append(m.optString("created_at")).append("\n\n");
                }
            }
            String finalText = text.toString();
            runOnUiThread(() -> inboxView.setText(finalText));
            return "Связь с VGRAM-сервером работает.";
        });
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
