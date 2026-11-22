# 手动构建 APK：aapt2 -> javac -> d8 -> zipalign -> apksigner
# 完全绕开 Gradle 的 native-platform.dll
$ErrorActionPreference = "Continue"

$root   = "C:\Users\47469\Documents\deepseek-harness\default-workspace"
$proj   = "$root\KeyQuotaIME"
$sdk    = "$root\android-sdk"
$jdk    = "$root\tools\jdk21"
$bt     = "$sdk\build-tools\35.0.0"
$aj     = "$sdk\platforms\android-35\android.jar"
$build  = "$proj\build"

$env:JAVA_HOME = $jdk
$env:Path = "$jdk\bin;$bt;$sdk\platform-tools;$env:Path"
$env:TMP = "$root\.tmp\adbtmp"; $env:TEMP = $env:TMP
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null

# 清理
if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Force -Path "$build\gen","$build\classes","$build\dex" | Out-Null

Write-Host "`n[1/7] aapt2 compile res" -ForegroundColor Cyan
& "$bt\aapt2.exe" compile --dir "$proj\app\src\main\res" -o "$build\res.zip"
if ($LASTEXITCODE -ne 0) { throw "aapt2 compile failed" }

Write-Host "[2/7] aapt2 link" -ForegroundColor Cyan
& "$bt\aapt2.exe" link `
    -o "$build\base.apk" `
    -I $aj `
    --manifest "$proj\app\src\main\AndroidManifest.xml" `
    -R "$build\res.zip" `
    -A "$proj\app\src\main\assets" `
    --java "$build\gen" `
    --min-sdk-version 24 `
    --target-sdk-version 35 `
    --auto-add-overlay
if ($LASTEXITCODE -ne 0) { throw "aapt2 link failed" }

Write-Host "[3/7] javac" -ForegroundColor Cyan
$srcs = Get-ChildItem "$proj\app\src\main\java" -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$gen  = Get-ChildItem "$build\gen" -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$all  = @($srcs) + @($gen)
& "$jdk\bin\javac.exe" -encoding UTF-8 -source 17 -target 17 `
    -nowarn -cp $aj -d "$build\classes" $all 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "javac failed" }

Write-Host "[4/7] d8 -> classes.dex" -ForegroundColor Cyan
$cls = Get-ChildItem "$build\classes" -Recurse -Filter *.class | ForEach-Object { $_.FullName }
& "$bt\d8.bat" --lib $aj --min-api 24 --output "$build\dex" $cls
if ($LASTEXITCODE -ne 0) { throw "d8 failed" }

Write-Host "[5/7] pack classes.dex into apk" -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$apkPath = "$build\unsigned.apk"
Copy-Item "$build\base.apk" $apkPath -Force
$zip = [System.IO.Compression.ZipFile]::Open($apkPath, 'Update')

# aapt2 on Windows writes nested asset paths with backslashes, which the
# WebView cannot resolve. Drop those entries and re-add them with "/".
$bad = @($zip.Entries | Where-Object { $_.FullName -like '*\*' } | ForEach-Object { $_.FullName })
foreach ($b in $bad) {
    $entry = $zip.GetEntry($b)
    if ($entry) { $entry.Delete() }
}
if ($bad.Count -gt 0) { Write-Host "    fixed $($bad.Count) backslash asset paths" }

$assetRoot = "$proj\app\src\main\assets"
Get-ChildItem $assetRoot -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($assetRoot.Length + 1).Replace('\', '/')
    $name = "assets/$rel"
    $existing = $zip.GetEntry($name)
    if ($existing) { $existing.Delete() }
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $name) | Out-Null
}

$dexEntry = $zip.CreateEntry("classes.dex", [System.IO.Compression.CompressionLevel]::Optimal)
$dexStream = $dexEntry.Open()
$dexBytes = [System.IO.File]::ReadAllBytes("$build\dex\classes.dex")
$dexStream.Write($dexBytes, 0, $dexBytes.Length)
$dexStream.Close()
$zip.Dispose()
Write-Host "    classes.dex = $([math]::Round($dexBytes.Length/1KB,1)) KB"

Write-Host "[6/7] zipalign" -ForegroundColor Cyan
& "$bt\zipalign.exe" -f -p 4 "$build\unsigned.apk" "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "zipalign failed" }

Write-Host "[7/7] apksigner" -ForegroundColor Cyan
$ks = "$proj\debug.keystore"
if (-not (Test-Path $ks)) {
    & "$jdk\bin\keytool.exe" -genkeypair -v `
        -keystore $ks -storepass android -keypass android `
        -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 `
        -dname "CN=Android Debug,O=Android,C=US" 2>&1 | Out-Null
}
& "$bt\apksigner.bat" sign --ks $ks --ks-pass pass:android --key-pass pass:android `
    --out "$build\KeyQuota-IME.apk" "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "apksigner failed" }

& "$bt\apksigner.bat" verify --print-certs "$build\KeyQuota-IME.apk" 2>&1 | Select-Object -First 4

$apk = Get-Item "$build\KeyQuota-IME.apk"
Write-Host "`nAPK: $($apk.FullName)" -ForegroundColor Green
Write-Host "size: $([math]::Round($apk.Length/1MB,2)) MB" -ForegroundColor Green
