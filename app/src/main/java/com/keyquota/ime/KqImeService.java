package com.keyquota.ime;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.inputmethodservice.InputMethodService;
import android.net.Uri;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

/**
 * Chaos Keyboard - runs the Key Quota web game as an Android IME.
 *
 * Commit path:
 *   WebView(JS) --JavascriptInterface--> KqImeService.Bridge --> InputConnection.commitText
 *
 * Game state lives in the page; native only writes/removes characters.
 */
public class KqImeService extends InputMethodService {

    private static final String TAG = "KqIME";
    private static final String PAGE = "file:///android_asset/keyquota.html";

    /** Panel height in dp. Roughly half a screen. */
    private static final int PANEL_HEIGHT_DP = 410;

    /** Auto-enter after a hit. Off: host Enter usually means newline. */
    private static final boolean AUTO_ENTER_AFTER_HIT = false;

    private WebView web;
    private FrameLayout root;
    private boolean pageReady = false;

    /** Debug channel: adb broadcast injects JS, verification only. */
    private final android.content.BroadcastReceiver debugReceiver =
            new android.content.BroadcastReceiver() {
        @Override public void onReceive(Context c, android.content.Intent i) {
            String act = i.getStringExtra("act");
            if (act != null) {
                // NOTE: deliberately if-else instead of switch(String).
                // d8 output for String switch fails ART verification on Android 16,
                // which makes the whole Service unloadable.
                if ("send".equals(act)) {
                    eval("document.getElementById('send').click()");
                } else if ("arena".equals(act)) {
                    eval("document.getElementById('arena').click()");
                } else if ("again".equals(act)) {
                    eval("document.getElementById('again').click()");
                } else if ("offer".equals(act)) {
                    eval("document.getElementById('offer').click()");
                } else if ("rack".equals(act)) {
                    eval("document.getElementById('rack').click()");
                } else if ("claim".equals(act)) {
                    eval("document.getElementById('claim').click()");
                } else if ("finish".equals(act)) {
                    eval("document.getElementById('finish').click()");
                } else if ("type".equals(act)) {
                    String ch = i.getStringExtra("ch");
                    if (ch != null) eval("type(" + jsStr(ch) + ")");
                } else if ("word".equals(act)) {
                    String w = i.getStringExtra("ch");
                    if (w != null) {
                        StringBuilder sb = new StringBuilder();
                        for (int k = 0; k < w.length(); k++) {
                            sb.append("type(").append(jsStr(String.valueOf(w.charAt(k)))).append(");");
                        }
                        eval(sb.toString());
                    }
                } else if ("theme".equals(act)) {
                    String t = i.getStringExtra("name");
                    if (t == null) t = "ios".equals(readTheme(KqImeService.this)) ? "chaos" : "ios";
                    // commit() is synchronous; apply() would make the next read stale
                    KqImeService.this.getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                            .putString(KEY_THEME, t).commit();
                    int bg = Color.parseColor(themeBackground());
                    if (root != null) root.setBackgroundColor(bg);
                    if (web != null) web.setBackgroundColor(bg);
                    applyTheme();
                    Log.d(TAG, "theme -> " + t);
                } else if ("space".equals(act)) {
                    // adb shell trims trailing spaces, so send space via this action
                    eval("type(' ')");
                } else if ("ad".equals(act)) {
                    eval("show('ad')");
                } else if ("adplay".equals(act)) {
                    // real path: goes through adProvider (may pick classic or clip)
                    eval("show('ad');adProvider.present(function(){phase='chat';show('chat');renderChat()})");
                } else if ("clipad".equals(act)) {
                    eval("show('ad');presentClipAd(function(){phase='chat';show('chat');renderChat()})");
                } else if ("classicad".equals(act)) {
                    // full ad flow, forced to the classic panel so Claim/timer work
                    eval("show('ad');adProvider.present(function(){phase='chat';show('chat');renderChat()},null,true)");
                } else if ("del".equals(act)) {
                    eval("erase()");
                } else if ("state".equals(act)) {
                    eval("KQ.log('phase='+phase+' | draft='+draft+' | pending='+pending"
                       + "+' | stock='+document.getElementById('stock').textContent)");
                } else {
                    eval("KQ.log('unknown act')");
                }
                Log.d(TAG, "dbg act: " + act);
                return;
            }
            String js = i.getStringExtra("js");
            if (js != null) {
                Log.d(TAG, "dbg js: " + js);
                eval(js);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        android.content.IntentFilter f =
                new android.content.IntentFilter("com.keyquota.ime.DEBUG");
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(debugReceiver, f, Context.RECEIVER_EXPORTED);
        } else {
            registerReceiver(debugReceiver, f);
        }
    }

    /**
     * The IME window measures with wrap_content, so a plain LayoutParams
     * height is ignored. Force EXACTLY here or the panel collapses to 0.
     */
    private static class FixedHeightPanel extends FrameLayout {
        private final int fixedHeight;
        FixedHeightPanel(Context c, int heightPx) {
            super(c);
            this.fixedHeight = heightPx;
            setMinimumHeight(heightPx);
        }
        @Override
        protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
            int h = MeasureSpec.makeMeasureSpec(fixedHeight, MeasureSpec.EXACTLY);
            super.onMeasure(widthMeasureSpec, h);
            setMeasuredDimension(getMeasuredWidth(), fixedHeight);
        }
    }

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    public View onCreateInputView() {
        Context ctx = this;

        root = new FixedHeightPanel(ctx, dp(PANEL_HEIGHT_DP));
        root.setBackgroundColor(Color.parseColor(themeBackground()));

        web = new WebView(ctx);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        // file:// pages may not load other file:// resources by default,
        // which breaks the clip-ad videos under assets/media/.
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(false);
        s.setUseWideViewPort(false);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setTextZoom(100);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        // Critical: the WebView must never take focus, or the IME retriggers itself.
        web.setFocusable(false);
        web.setFocusableInTouchMode(false);
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setBackgroundColor(Color.parseColor(themeBackground()));

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                pageReady = true;
                Log.d(TAG, "page ready: " + url);
                applyTheme();
                // Tell the page which app hosts us, for the status label.
                pushHost();
            }

            /**
             * The ad card's X link is target="_blank". An IME WebView cannot open
             * a new window, so it would navigate the keyboard itself to x.com and
             * leave the user stuck on a web page with no way back.
             * Hand http(s) to the system browser instead of navigating in place.
             * The link itself is untouched: it stays clickable and reachable.
             */
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest request) {
                return handleExternalUrl(request == null ? null : request.getUrl());
            }

            /** Legacy overload for older WebView implementations. */
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleExternalUrl(url == null ? null : Uri.parse(url));
            }
        });

        web.addJavascriptInterface(new Bridge(), "KQNative");
        web.loadUrl(PAGE);

        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        // IME windows cannot host a SurfaceView, so WebView video paints black.
        // Software layer routes frames through a bitmap and actually shows them.
        web.setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        root.addView(web, lp);

        return root;
    }

    /** Never enter fullscreen extract mode, not even in landscape. */
    @Override
    public boolean onEvaluateFullscreenMode() {
        return false;
    }

    @Override
    public void onStartInput(EditorInfo attribute, boolean restarting) {
        super.onStartInput(attribute, restarting);
        if (attribute != null) {
            Log.d(TAG, "input: pkg=" + attribute.packageName
                    + " inputType=0x" + Integer.toHexString(attribute.inputType)
                    + " imeOptions=0x" + Integer.toHexString(attribute.imeOptions)
                    + " actionId=" + attribute.actionId
                    + " action=" + (attribute.imeOptions & EditorInfo.IME_MASK_ACTION));
        }
        if (pageReady) {
            // New input field: drop the leftover draft state.
            eval("window.KQReset && KQReset();");
            pushHost();
        }
    }

    @Override
    public void onStartInputView(EditorInfo info, boolean restarting) {
        super.onStartInputView(info, restarting);
        recoverPageIfNeeded();
        applyTheme();
        pushHost();
    }

    /**
     * Self-heal: if the keyboard WebView ever ended up on a foreign page
     * (e.g. the ad's X link was followed inside the IME), reload our asset
     * so the next time the keyboard pops up it is usable again.
     */
    private void recoverPageIfNeeded() {
        if (web == null) return;
        String url = web.getUrl();
        if (url == null || url.isEmpty()) return;
        if (!url.startsWith("file:///android_asset/")) {
            Log.w(TAG, "recovering from foreign url: " + url);
            pageReady = false;
            web.loadUrl(PAGE);
        }
    }

    /**
     * Open http/https outside the IME. Everything else (file/about/javascript)
     * keeps default behaviour so the asset page still works normally.
     */
    private boolean handleExternalUrl(Uri uri) {
        if (uri == null) return false;
        String scheme = uri.getScheme();
        if (scheme == null) return false;
        if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
            return false;
        }
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, uri);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
            Log.d(TAG, "opened externally: " + uri);
        } catch (Throwable t) {
            // No browser installed, or the OS refused; stay silent, never crash.
            Log.w(TAG, "no activity for " + uri + ": " + t);
        }
        return true;
    }

    @Override
    public void onFinishInput() {
        super.onFinishInput();
        // Keep the page alive so quota, ad and wheel progress survive.
    }

    @Override
    public void onDestroy() {
        try { unregisterReceiver(debugReceiver); } catch (Throwable ignored) { }
        if (web != null) {
            web.removeJavascriptInterface("KQNative");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    // ---------------------------------------------------------------- utils

    // ---------------------------------------------------------------- theme

    /** SharedPreferences key used by SetupActivity to switch themes. */
    public static final String PREFS = "kq";
    public static final String KEY_THEME = "theme";

    /** Returns "ios" (default) or "chaos". */
    public static String readTheme(Context c) {
        return c.getSharedPreferences(PREFS, MODE_PRIVATE)
                .getString(KEY_THEME, "ios");
    }

    private String currentTheme() {
        return readTheme(this);
    }

    /** Window / WebView background that matches the active theme. */
    private String themeBackground() {
        String t = currentTheme();
        if ("ios".equals(t))   return "#D1D3D9";
        if ("cream".equals(t)) return "#F5F1E8";
        if ("punk".equals(t))  return "#2A0E2E";
        if ("anime".equals(t)) return "#FFF8E7";
        if ("neon".equals(t))  return "#0A0A0A";
        if ("rainbow".equals(t)) return "#0A0A0E";
        return "#171127";
    }

    /** Push the theme into the page: <html data-theme="ios|chaos">. */
    private void applyTheme() {
        if (web == null) return;
        final String t = currentTheme();
        web.post(new Runnable() {
            @Override public void run() {
                if (web != null) {
                    web.evaluateJavascript(
                            "window.KQSetTheme?KQSetTheme('" + t + "'):"
                          + "document.documentElement.dataset.theme='" + t + "'", null);
                }
            }
        });
    }

    private int dp(int v) {
        return Math.round(getResources().getDisplayMetrics().density * v);
    }

    private void eval(final String js) {
        if (web == null) return;
        web.post(new Runnable() {
            @Override public void run() {
                if (web != null) web.evaluateJavascript(js, null);
            }
        });
    }

    private void pushHost() {
        EditorInfo ei = getCurrentInputEditorInfo();
        String pkg = (ei != null && ei.packageName != null) ? ei.packageName.toString() : "";
        String label = hostLabel(pkg);
        eval("window.KQSetHost && KQSetHost(" + jsStr(label) + "," + jsStr(pkg) + ");");
    }

    private static String hostLabel(String pkg) {
        if (pkg == null || pkg.isEmpty()) return "Input field";
        // Also avoid switch(String); use if-else.
        if ("com.tencent.mm".equals(pkg))           return "WeChat";
        if ("com.tencent.mobileqq".equals(pkg))     return "QQ";
        if ("com.tencent.tim".equals(pkg))          return "TIM";
        if ("com.tencent.wework".equals(pkg))       return "WeCom";
        if ("com.ss.android.ugc.aweme".equals(pkg)) return "TikTok";
        if ("com.sina.weibo".equals(pkg))           return "Weibo";
        if ("com.tencent.weread".equals(pkg))       return "WeRead";
        return pkg;
    }

    private static String jsStr(String s) {
        if (s == null) return "''";
        StringBuilder b = new StringBuilder("'");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\'': b.append("\\'"); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        return b.append("'").toString();
    }

    private void buzz() {
        try {
            Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (v == null || !v.hasVibrator()) return;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createOneShot(12, VibrationEffect.DEFAULT_AMPLITUDE));
            } else {
                v.vibrate(12);
            }
        } catch (Throwable ignored) { }
    }

    // ---------------------------------------------------------------- JS bridge

    public class Bridge {

        @JavascriptInterface
        public void typeChar(final String ch) {
            if (ch == null || ch.isEmpty()) return;
            root.post(new Runnable() {
                @Override public void run() {
                    InputConnection ic = getCurrentInputConnection();
                    if (ic != null) ic.commitText(ch, 1);
                }
            });
        }

        /**
         * Send: commit the whole line into the host input.
         * Returns success synchronously so JS never rolls back a failed commit.
         */
        @JavascriptInterface
        public boolean commitText(final String text) {
            Log.d(TAG, "commit: " + text);
            if (text == null || text.isEmpty()) return false;
            final InputConnection ic = getCurrentInputConnection();
            if (ic == null) {
                Log.w(TAG, "commit failed: no InputConnection");
                return false;
            }
            try {
                return ic.commitText(text, 1);
            } catch (Throwable t) {
                Log.w(TAG, "commit failed: " + t);
                return false;
            }
        }

        @JavascriptInterface
        public void typeText(final String text) {
            commitText(text);
        }

        /**
         * Delete must act on the host input, not just the local buffer.
         * Order: end composing -> delete one code point -> fallback to DEL.
         */
        @JavascriptInterface
        public void deleteBack(final int n) {
            if (n <= 0) return;
            root.post(new Runnable() {
                @Override public void run() {
                    InputConnection ic = getCurrentInputConnection();
                    if (ic == null) {
                        Log.w(TAG, "delete failed: no InputConnection");
                        return;
                    }
                    for (int i = 0; i < n; i++) {
                        // 1) End composing first, or the host ignores the delete.
                        ic.setComposingText("", 0);

                        // 2) Delete one full code point. The CodePoints variant
                        //    keeps surrogate pairs (emoji) intact.
                        boolean ok;
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                            ok = ic.deleteSurroundingTextInCodePoints(1, 0);
                        } else {
                            ok = ic.deleteSurroundingText(1, 0);
                        }

                        // 3) Fallback: WebView / Flutter / RN often ignore that.
                        //    sendDownUpKeyEvents is not on the InputConnection
                        //    interface, so send the DOWN/UP pair explicitly.
                        if (!ok) {
                            ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DEL));
                            ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DEL));
                        }
                    }
                    Log.d(TAG, "delete x" + n + " sent to host");
                }
            });
        }

        @JavascriptInterface
        public void enter() {
            root.post(new Runnable() {
                @Override public void run() {
                    InputConnection ic = getCurrentInputConnection();
                    if (ic == null) return;
                    ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER));
                    ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER));
                }
            });
        }

        /**
         * Wheel hit: commit text only. Never send, never hide the keyboard.
         * Forbidden here: performEditorAction / sendDefaultEditorAction /
         * requestHideSelf / hideWindow / finishInput.
         */
        @JavascriptInterface
        public void onCommitted(final String text) {
            Log.d(TAG, "hit, commit only: " + text);
            if (text == null || text.isEmpty()) return;
            root.post(new Runnable() {
                @Override public void run() {
                    InputConnection ic = getCurrentInputConnection();
                    if (ic == null) return;
                    ic.commitText(text, 1);
                    ic.finishComposingText();
                    // That's all. No send, no hide, no input method switch.
                }
            });
        }

        @JavascriptInterface
        public void haptic() {
            root.post(new Runnable() {
                @Override public void run() { buzz(); }
            });
        }

        @JavascriptInterface
        public String hostPackage() {
            EditorInfo ei = getCurrentInputEditorInfo();
            return (ei != null && ei.packageName != null) ? ei.packageName.toString() : "";
        }

        @JavascriptInterface
        public void log(String msg) {
            Log.d(TAG + "/JS", String.valueOf(msg));
        }
    }
}


