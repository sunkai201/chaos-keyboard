# KeyQuota — a keyboard that charges you by the keystroke

An Android input method (IME) that turns typing into a resource game. Every key
has **3 uses**. Run out and you must send the line through a timing wheel to
bank it — miss, and a sponsored ad eats five seconds before you can type again.

Fourteen visual themes, a working suggestion bar, and a genuinely hostile set of
"key conflict" mechanics that make the keyboard fight back.

## What it does

| Mechanic | Behaviour |
|---|---|
| **Key quota** | Each of the 108 keycaps carries 3 charges. Deplete one and it greys out. |
| **Draft-only typing** | Characters are held in an in-page draft. Nothing reaches the host app until you commit. |
| **Send wheel** | `Send` opens a spinning dial. Hit the red zone to commit the whole line; miss and the line is rolled back. |
| **Sponsored reload** | A failed round plays a 5-second ad. Claim unlocks only when the countdown ends. |
| **Key conflict** | Word swaps, brand suggestions, delete hijacking and an undo bar — deliberately obstructive, deliberately undoable. |
| **Static mode** | The `Chalk` theme pins every key into an ordered grid with no motion, for people who just want to type. |

## Themes

`iOS` · `Chaos` · `Cream` · `Punk` · `Anime` · `Neon` · `Rainbow` · `Pixel Punk`
· `Pop Comic` · `Instrument` · `Silver Mist` · `Oat Paper` · **`Chalk`**

Themes are grouped in the launcher as **Chaos Keys** (keys fly and collide) and
**Chalk** (keys stay put). Every theme also recolours the ad panel, the wheel and
the reload screen — not just the keyboard.

## Build

Requirements: JDK 21, Android SDK build-tools 35, `android-35` platform.

```bash
python build_assets.py                     # regenerate assets/keyquota.html
powershell -ExecutionPolicy Bypass -File build_manual.ps1
# -> build/KeyQuota-IME.apk
```

`build_manual.ps1` drives `aapt2 → javac → d8 → zipalign → apksigner` directly,
so Gradle is not required. Signed with the bundled debug keystore.

## Architecture

```
app/src/main/java/com/keyquota/ime/
  KqImeService.java    InputMethodService hosting a single WebView
  SetupActivity.java   Launcher: theme picker + enable/switch steps
app/src/main/assets/
  keyquota.html        The whole game: keys, wheel, ads, suggestions
  media/               Ad creatives (mp4 + animated WebP + stills)
```

The WebView *is* the keyboard. All game logic lives in `keyquota.html`;
`KqImeService` exposes a small `@JavascriptInterface` bridge (`KQNative`) for
committing text, deleting, and haptic feedback.

### Notes on the IME window

Two things bite when rendering media inside an `InputMethodService` window:

1. **Video surfaces do not composite.** A `<video>` element decodes and reports
   `videoWidth`, but never paints. Ads therefore ship a static poster frame
   underneath and an animated WebP layered on top.
2. **Nested asset paths from `aapt2` arrive with backslashes** on Windows, which
   the WebView cannot resolve. `build_manual.ps1` rewrites them to `/` when
   packaging.

## License

MIT — see [LICENSE](LICENSE).

## Run from source

```bash
git clone <repo-url> && cd keyquota
cp local.properties.example local.properties   # then set sdk.dir to your Android SDK
python build_assets.py
powershell -ExecutionPolicy Bypass -File build_manual.ps1
adb install -r build/KeyQuota-IME.apk
```

Or open the folder in Android Studio — `app/build.gradle` is a standard AGP module.

Every source file needed to rebuild the shipped APK is in this repository;
`dist/KeyQuota-IME.apk` is the exact artifact produced by the commands above.
