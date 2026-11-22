package com.keyquota.ime;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.provider.Settings;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.List;
import java.util.Random;

/**
 * Home screen styled after the KeyQuota 2.1.1 mock-up:
 * warm paper background, hand-placed hero letters, tilted cards.
 */
public class SetupActivity extends Activity {

    /** One selectable theme. */
    private static final class ThemeDef {
        final String id, name, tag, desc;
        final int cardBg, cardBorder, keyBg, keyBorder, keyText,
                  titleColor, tagBg, tagText, descColor, specColor;

        ThemeDef(String id, String name, String tag, String desc,
                 int cardBg, int cardBorder, int keyBg, int keyBorder, int keyText,
                 int titleColor, int tagBg, int tagText, int descColor, int specColor) {
            this.id = id; this.name = name; this.tag = tag; this.desc = desc;
            this.cardBg = cardBg; this.cardBorder = cardBorder;
            this.keyBg = keyBg; this.keyBorder = keyBorder; this.keyText = keyText;
            this.titleColor = titleColor; this.tagBg = tagBg; this.tagText = tagText;
            this.descColor = descColor; this.specColor = specColor;
        }
    }

    private static final int PAPER = Color.parseColor("#F2EFE6");
    private static final int BLUE = Color.parseColor("#3B5BDB");
    private static final int INK = Color.parseColor("#1A1A1A");
    private static final int CORAL = Color.parseColor("#F26B4E");
    private static final int GOLD = Color.parseColor("#E8C547");

    private static final ThemeDef[] THEMES = new ThemeDef[]{
        new ThemeDef("ios", "iOS", "Clean · Light",
                "Light grey panel, white rounded keys, SF style. Apple's keyboard, with the quota still on.",
                Color.parseColor("#F2F2F7"), Color.parseColor("#C6C6C8"),
                Color.parseColor("#FFFFFF"), Color.parseColor("#C6C6C8"), Color.parseColor("#000000"),
                Color.parseColor("#000000"), Color.parseColor("#E5E5EA"), Color.parseColor("#6B6B70"),
                Color.parseColor("#3A3A3C"), Color.parseColor("#8E8E93")),

        new ThemeDef("chaos", "Chaos", "Violet · Neon",
                "Deep violet enamel with brass outlines. Two keys per letter and a quota that never forgives.",
                Color.parseColor("#21163E"), Color.parseColor("#6B4E7A"),
                Color.parseColor("#B62C40"), Color.parseColor("#EFD58B"), Color.parseColor("#FFF1AC"),
                Color.parseColor("#FFE2A4"), Color.parseColor("#382344"), Color.parseColor("#FFDA85"),
                Color.parseColor("#C8B7CD"), Color.parseColor("#9E6F7A")),

        new ThemeDef("cream", "Cream", "Metal · Mono",
                "Cream metal panel, monospaced digits and gauge ticks. A typewriter that passed inspection.",
                Color.parseColor("#F5F1E8"), Color.parseColor("#E0A458"),
                Color.parseColor("#FFFFFF"), Color.parseColor("#D8D0C0"), Color.parseColor("#3A3630"),
                Color.parseColor("#3A3630"), Color.parseColor("#E8DFC8"), Color.parseColor("#5A5040"),
                Color.parseColor("#5A5040"), Color.parseColor("#8A8070")),

        new ThemeDef("punk", "Punk", "Pixel · Neon",
                "Neon violet with pixel keycaps, 2px hard stroke and hard shadows. 108 lives on the street.",
                Color.parseColor("#2A0E2E"), Color.parseColor("#7A3A7A"),
                Color.parseColor("#B62C40"), Color.parseColor("#EFD58B"), Color.parseColor("#FFF1AC"),
                Color.parseColor("#FFF1AC"), Color.parseColor("#C9A227"), Color.parseColor("#2A0E2E"),
                Color.parseColor("#E8D8F0"), Color.parseColor("#8A6A7A")),

        new ThemeDef("anime", "Anime", "Clash · Sticker",
                "High saturation clash colors, thick black outlines, tilted sticker energy. Every tap is a sound effect.",
                Color.parseColor("#FFF8E7"), Color.parseColor("#1A1A1A"),
                Color.parseColor("#F5C518"), Color.parseColor("#1A1A1A"), Color.parseColor("#1A1A1A"),
                Color.parseColor("#1A1A1A"), Color.parseColor("#E63946"), Color.parseColor("#FFFFFF"),
                Color.parseColor("#3A3A3A"), Color.parseColor("#9A9A9A")),

        new ThemeDef("neon", "Neon", "Red · Terminal",
                "Black panel, red keycaps, yellow glow. A terminal that charges you by the keystroke.",
                Color.parseColor("#0A0A0A"), Color.parseColor("#FF0000"),
                Color.parseColor("#FF0000"), Color.parseColor("#FFFF00"), Color.parseColor("#FFFF00"),
                Color.parseColor("#FFFF00"), Color.parseColor("#FF0000"), Color.parseColor("#FFFF00"),
                Color.parseColor("#FFB3B3"), Color.parseColor("#FF6B6B")),

        new ThemeDef("rainbow", "Rainbow", "Multi · Neon",
                "Every keycap a different neon, contrast outlines on a black grid. Loud on purpose.",
                Color.parseColor("#0A0A0E"), Color.parseColor("#FFD700"),
                Color.parseColor("#FF2D2D"), Color.parseColor("#FFD700"), Color.parseColor("#0A0A0A"),
                Color.parseColor("#FFFFFF"), Color.parseColor("#FFD700"), Color.parseColor("#0A0A0E"),
                Color.parseColor("#B8B8C8"), Color.parseColor("#7A7A8A")),

        new ThemeDef("pixel", "Pixel Punk", "Pixels · Neon",
                "Catch the red keycaps under the neon lights. Arcade collision, no mercy.",
                Color.parseColor("#170A20"), Color.parseColor("#A34168"),
                Color.parseColor("#B52446"), Color.parseColor("#FFCA94"), Color.parseColor("#FFEDAB"),
                Color.parseColor("#FFEBB2"), Color.parseColor("#3C1231"), Color.parseColor("#FFDF88"),
                Color.parseColor("#C8ABC8"), Color.parseColor("#8A6A7A")),

        new ThemeDef("comic", "Pop Comic", "Pop · Comic",
                "Primary-colour stickers bounce across a printed page. Thick outlines, loud colours.",
                Color.parseColor("#2678C8"), Color.parseColor("#211A1B"),
                Color.parseColor("#FFDB36"), Color.parseColor("#1E191B"), Color.parseColor("#151519"),
                Color.parseColor("#201B20"), Color.parseColor("#FF5A4E"), Color.parseColor("#211719"),
                Color.parseColor("#2A2118"), Color.parseColor("#514443")),

        new ThemeDef("industrial", "Instrument", "LCD · Gauge",
                "Olive display, two-tone keys and an orange send switch. A machine that measures you.",
                Color.parseColor("#E8E4D9"), Color.parseColor("#B0AA98"),
                Color.parseColor("#F5F1E4"), Color.parseColor("#B0AA98"), Color.parseColor("#302E28"),
                Color.parseColor("#292923"), Color.parseColor("#ED7625"), Color.parseColor("#2E2618"),
                Color.parseColor("#5C5B52"), Color.parseColor("#8A8578")),

        new ThemeDef("mist", "Silver Mist", "Silver · Matte",
                "Cool grey keycaps and a blue highlight. Quiet hardware, same cold quota.",
                Color.parseColor("#DFE3E8"), Color.parseColor("#B8C0CA"),
                Color.parseColor("#F5F7FA"), Color.parseColor("#C2C9D2"), Color.parseColor("#2B323C"),
                Color.parseColor("#2B323C"), Color.parseColor("#4A79C9"), Color.parseColor("#FFFFFF"),
                Color.parseColor("#5A6470"), Color.parseColor("#8A94A0")),

        new ThemeDef("oat", "Oat Paper", "Cream · Warm",
                "Warm paper, biscuit keys and terracotta controls. Soft on the eyes, still strict.",
                Color.parseColor("#EFE8D8"), Color.parseColor("#C9B99A"),
                Color.parseColor("#F7F0E2"), Color.parseColor("#CBBFA6"), Color.parseColor("#3A3328"),
                Color.parseColor("#3A3328"), Color.parseColor("#C2703D"), Color.parseColor("#FFFFFF"),
                Color.parseColor("#6A5F4C"), Color.parseColor("#9A8E78")),

        new ThemeDef("chalk", "Chalk", "Static · Ordered",
                "Keys stay in a neat grid, nothing flies. For anyone who just wants to type.",
                Color.parseColor("#EDF0F5"), Color.parseColor("#C8D0DD"),
                Color.parseColor("#FBFCFF"), Color.parseColor("#C8D0DD"), Color.parseColor("#1B2840"),
                Color.parseColor("#1B2840"), Color.parseColor("#3649BC"), Color.parseColor("#FFFFFF"),
                Color.parseColor("#4E607A"), Color.parseColor("#8A94A6")),
    };

    private static final int[] RAINBOW_PREVIEW = {
            Color.parseColor("#FF2D2D"), Color.parseColor("#FF7A00"),
            Color.parseColor("#FFD700"), Color.parseColor("#22C55E"),
            Color.parseColor("#22D3EE"), Color.parseColor("#3B82F6"),
            Color.parseColor("#8B5CF6"), Color.parseColor("#EC4899")
    };

    private static final String[] PREVIEW_ROWS = {
            "1234567890", "qwertyuiop", "asdfghjkl"
    };

    private TextView status;
    private LinearLayout cards;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildRoot());
    }

    private View buildRoot() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(PAPER);
        scroll.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(26), dp(18), dp(30));
        scroll.addView(root, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        root.addView(buildHero());

        TextView sub = new TextView(this);
        sub.setText("Choose a keyboard, then aim to deliver. Every key has 3 uses.");
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        sub.setTextColor(Color.parseColor("#8C8578"));
        sub.setPadding(dp(4), dp(10), dp(4), dp(18));
        sub.setLineSpacing(dp(3), 1f);
        root.addView(sub);

        status = new TextView(this);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        status.setTextColor(Color.parseColor("#6B6357"));
        status.setPadding(dp(14), dp(10), dp(14), dp(10));
        GradientDrawable sb = new GradientDrawable();
        sb.setColor(Color.parseColor("#E9E4D8"));
        sb.setCornerRadius(dp(10));
        status.setBackground(sb);
        root.addView(status, matchWrap());

        root.addView(bigButton("1  Enable keyboard", BLUE, Color.WHITE, false,
                new View.OnClickListener() {
                    @Override public void onClick(View v) {
                        startActivity(new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS));
                    }
                }));
        root.addView(bigButton("2  Choose input method", Color.WHITE, INK, true,
                new View.OnClickListener() {
                    @Override public void onClick(View v) {
                        InputMethodManager imm =
                                (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) imm.showInputMethodPicker();
                    }
                }));
        root.addView(bigButton("3  Try the demo chat", GOLD, Color.parseColor("#7A6A2A"), true,
                new View.OnClickListener() {
                    @Override public void onClick(View v) {
                        Intent i = new Intent(Intent.ACTION_SEND);
                        i.setType("text/plain");
                        i.putExtra(Intent.EXTRA_TEXT, "");
                        try { startActivity(Intent.createChooser(i, "Pick a place to type")); }
                        catch (Throwable ignored) { }
                    }
                }));

        TextView reset = new TextView(this);
        reset.setText("Reset key balances");
        reset.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        reset.setTextColor(Color.parseColor("#8C8578"));
        reset.setPadding(dp(6), dp(16), dp(6), dp(18));
        reset.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                getSharedPreferences(KqImeService.PREFS, MODE_PRIVATE)
                        .edit().remove("balances").apply();
            }
        });
        root.addView(reset);

        cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.VERTICAL);
        root.addView(cards, matchWrap());

        TextView help = new TextView(this);
        help.setText("Tap a card to switch. The active theme is marked.");
        help.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        help.setTextColor(Color.parseColor("#8C8578"));
        help.setPadding(dp(4), dp(10), dp(4), dp(18));
        root.addView(help);

        return scroll;
    }

    /** "KEY QUOTA" with every letter nudged and tinted like a sticker sheet. */
    private View buildHero() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(2), dp(6), dp(2), dp(4));

        String text = "KEYQUOTA";
        int[] colors = {INK, GOLD, INK, CORAL, CORAL, INK, CORAL, INK};
        float[] rise = {-8f, 6f, -4f, 8f, -6f, 4f, -8f, 6f};
        float[] tilt = {-5f, 3f, -2f, 4f, -3f, 2f, -4f, 3f};

        for (int i = 0; i < text.length(); i++) {
            if (i == 3) {
                View gap = new View(this);
                gap.setLayoutParams(new LinearLayout.LayoutParams(dp(10), 1));
                row.addView(gap);
            }
            TextView t = new TextView(this);
            t.setText(String.valueOf(text.charAt(i)));
            t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 40);
            t.setTextColor(colors[i % colors.length]);
            t.setTypeface(Typeface.create("sans-serif-black", Typeface.BOLD));
            t.setRotation(tilt[i % tilt.length]);
            t.setTranslationY(dp((int) rise[i % rise.length] / 2));
            t.setShadowLayer(2f, 2f, 3f, Color.parseColor("#1A1A1A22"));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.rightMargin = dp(1);
            row.addView(t, lp);
        }
        return row;
    }

    private View bigButton(String text, int bg, int fg, boolean outlined, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17);
        b.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
        b.setTextColor(fg);
        GradientDrawable d = new GradientDrawable();
        d.setColor(bg);
        d.setCornerRadius(dp(14));
        if (outlined) d.setStroke(dp(2), INK);
        b.setBackground(d);
        b.setOnClickListener(l);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(58));
        lp.bottomMargin = dp(12);
        b.setLayoutParams(lp);
        return b;
    }

    private void renderCards() {
        cards.removeAllViews();
        String active = getSharedPreferences(KqImeService.PREFS, MODE_PRIVATE)
                .getString(KqImeService.KEY_THEME, "ios");

        addGroupHeader("Chaos Keys", "Keys fly around and collide. Pick this if you can handle it.");
        int idx = 0;
        for (ThemeDef t : THEMES) {
            if (!"chalk".equals(t.id)) addCard(t, active, idx++);
        }

        addGroupHeader("Chalk", "Keys stay in an ordered grid. No movement at all.");
        for (ThemeDef t : THEMES) {
            if ("chalk".equals(t.id)) addCard(t, active, 0);
        }
    }

    private void addGroupHeader(String title, String hint) {
        TextView h = new TextView(this);
        h.setText(title);
        h.setTextSize(TypedValue.COMPLEX_UNIT_SP, 21);
        h.setTextColor(GOLD);
        h.setTypeface(Typeface.create("sans-serif-black", Typeface.BOLD));
        h.setRotation(-1.6f);
        LinearLayout.LayoutParams hp = matchWrap();
        hp.topMargin = dp(14);
        cards.addView(h, hp);

        TextView s = new TextView(this);
        s.setText(hint);
        s.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        s.setTextColor(Color.parseColor("#8C8578"));
        LinearLayout.LayoutParams sp = matchWrap();
        sp.bottomMargin = dp(10);
        cards.addView(s, sp);
    }

    private void addCard(final ThemeDef t, String active, int index) {
        boolean on = t.id.equals(active);

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(16), dp(16), dp(14));

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.WHITE);
        bg.setCornerRadius(dp(16));
        bg.setStroke(dp(on ? 3 : 2), BLUE);
        card.setBackground(bg);

        /* alternating tilt so the column reads hand-placed */
        float tilt = (index % 3 == 0) ? -1.1f : (index % 3 == 1 ? 0.9f : -0.5f);
        card.setRotation(tilt);

        LinearLayout.LayoutParams lp = matchWrap();
        lp.bottomMargin = dp(16);
        card.setLayoutParams(lp);

        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);

        TextView name = new TextView(this);
        name.setText(t.name);
        name.setTextSize(TypedValue.COMPLEX_UNIT_SP, 21);
        name.setTextColor(INK);
        name.setTypeface(Typeface.create("sans-serif-black", Typeface.BOLD));
        head.addView(name);

        TextView tag = new TextView(this);
        tag.setText(t.tag);
        tag.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);
        tag.setTextColor(Color.WHITE);
        tag.setPadding(dp(9), dp(3), dp(9), dp(3));
        GradientDrawable pill = new GradientDrawable();
        pill.setColor(index % 2 == 0 ? BLUE : CORAL);
        pill.setCornerRadius(dp(20));
        tag.setBackground(pill);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tlp.leftMargin = dp(10);
        head.addView(tag, tlp);
        card.addView(head);

        TextView desc = new TextView(this);
        desc.setText(t.desc);
        desc.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        desc.setTextColor(Color.parseColor("#5A5348"));
        desc.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams dlp = matchWrap();
        dlp.topMargin = dp(10);
        card.addView(desc, dlp);

        card.addView(buildPreview(t));

        LinearLayout foot = new LinearLayout(this);
        foot.setOrientation(LinearLayout.HORIZONTAL);
        foot.setGravity(Gravity.CENTER_VERTICAL);
        TextView spec = new TextView(this);
        spec.setText("Local keyboard · 108 uses");
        spec.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        spec.setTextColor(Color.parseColor("#8C8578"));
        foot.addView(spec);

        if (on) {
            TextView badge = new TextView(this);
            badge.setText("Active");
            badge.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);
            badge.setTextColor(Color.WHITE);
            badge.setPadding(dp(10), dp(3), dp(10), dp(3));
            GradientDrawable bb = new GradientDrawable();
            bb.setColor(BLUE);
            bb.setCornerRadius(dp(20));
            badge.setBackground(bb);
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            blp.leftMargin = dp(10);
            foot.addView(badge, blp);
        }
        LinearLayout.LayoutParams flp = matchWrap();
        flp.topMargin = dp(10);
        card.addView(foot, flp);

        card.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                getSharedPreferences(KqImeService.PREFS, MODE_PRIVATE)
                        .edit().putString(KqImeService.KEY_THEME, t.id).apply();
                renderCards();
                refreshStatus();
            }
        });
        cards.addView(card);
    }

    private View buildPreview(ThemeDef t) {
        LinearLayout pad = new LinearLayout(this);
        pad.setOrientation(LinearLayout.VERTICAL);
        pad.setPadding(dp(8), dp(10), dp(8), dp(10));
        GradientDrawable pb = new GradientDrawable();
        pb.setColor(shade(t.cardBg, 0.94f));
        pb.setCornerRadius(dp(8));
        pad.setBackground(pb);
        LinearLayout.LayoutParams plp = matchWrap();
        plp.topMargin = dp(12);
        pad.setLayoutParams(plp);

        for (int r = 0; r < PREVIEW_ROWS.length; r++) {
            String row = PREVIEW_ROWS[r];
            LinearLayout line = new LinearLayout(this);
            line.setOrientation(LinearLayout.HORIZONTAL);
            for (int i = 0; i < row.length(); i++) {
                int idx = r * 10 + i;
                boolean rainbow = "rainbow".equals(t.id);

                TextView k = new TextView(this);
                k.setText(String.valueOf(row.charAt(i)).toUpperCase());
                k.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
                k.setTextColor(rainbow ? Color.parseColor("#0A0A0A") : t.keyText);
                k.setGravity(Gravity.CENTER);
                k.setTypeface(Typeface.MONOSPACE);

                GradientDrawable kb = new GradientDrawable();
                kb.setColor(rainbow ? RAINBOW_PREVIEW[idx % RAINBOW_PREVIEW.length] : t.keyBg);
                kb.setCornerRadius(dp(3));
                kb.setStroke(dp(rainbow ? 2 : 1),
                        rainbow ? RAINBOW_PREVIEW[(idx + 3) % RAINBOW_PREVIEW.length] : t.keyBorder);
                k.setBackground(kb);

                LinearLayout.LayoutParams klp = new LinearLayout.LayoutParams(0, dp(28), 1f);
                klp.rightMargin = dp(3);
                klp.bottomMargin = dp(3);
                line.addView(k, klp);
            }
            pad.addView(line);
        }
        return pad;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int v) {
        return Math.round(getResources().getDisplayMetrics().density * v);
    }

    private static int shade(int color, float f) {
        int r = (int) (Color.red(color) * f);
        int g = (int) (Color.green(color) * f);
        int b = (int) (Color.blue(color) * f);
        return Color.rgb(Math.min(r, 255), Math.min(g, 255), Math.min(b, 255));
    }

    @Override
    protected void onResume() {
        super.onResume();
        renderCards();
        refreshStatus();
    }

    private void refreshStatus() {
        boolean enabled = false, selected = false;
        ComponentName me = new ComponentName(this, KqImeService.class);
        InputMethodManager imm =
                (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            List<InputMethodInfo> list = imm.getEnabledInputMethodList();
            for (InputMethodInfo info : list) {
                if (me.equals(info.getComponent())) { enabled = true; break; }
            }
            String cur = Settings.Secure.getString(getContentResolver(),
                    Settings.Secure.DEFAULT_INPUT_METHOD);
            if (cur != null) selected = me.equals(ComponentName.unflattenFromString(cur));
        }
        String theme = getSharedPreferences(KqImeService.PREFS, MODE_PRIVATE)
                .getString(KqImeService.KEY_THEME, "ios");
        String label = theme;
        for (ThemeDef t : THEMES) if (t.id.equals(theme)) label = t.name;

        status.setText((enabled ? "Enabled" : "Not enabled")
                + "  ·  " + (selected ? "Active" : "Inactive")
                + "  ·  " + label);
    }
}
