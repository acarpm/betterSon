# Installe BatConnect (Windows) depuis la dernière release GitHub.
#   irm https://raw.githubusercontent.com/acarpm/betterSon/main/install.ps1 | iex
# Relancer la même commande réinstalle la dernière version. Les données (profils, mesures) ne sont pas touchées.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # accélère fortement Invoke-WebRequest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$depot = "acarpm/betterSon"
$url = if ($env:BATCONNECT_BASE_URL) { $env:BATCONNECT_BASE_URL } else { "https://github.com/$depot/releases/latest/download" }
$dest = Join-Path $env:LOCALAPPDATA "Programs\BatConnect"
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("batconnect-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force $tmp, $dest | Out-Null

Write-Host "==> Installation de BatConnect"
try {
    Invoke-WebRequest "$url/BatConnect-windows.exe" -OutFile "$tmp\BatConnect.exe" -UseBasicParsing
    Invoke-WebRequest "$url/SHA256SUMS.txt" -OutFile "$tmp\SHA256SUMS.txt" -UseBasicParsing

    $ligne = Get-Content "$tmp\SHA256SUMS.txt" | Where-Object { $_ -match "BatConnect-windows\.exe\s*$" } | Select-Object -First 1
    if (-not $ligne) { throw "Somme de contrôle introuvable." }
    $attendu = ($ligne -split "\s+")[0].ToLower()
    $reel = (Get-FileHash "$tmp\BatConnect.exe" -Algorithm SHA256).Hash.ToLower()
    if ($attendu -ne $reel) { throw "Fichier corrompu (somme de contrôle différente), installation annulée." }

    $exe = Join-Path $dest "BatConnect.exe"
    if (Test-Path $exe) {   # un exécutable en cours d'exécution peut être renommé, pas écrasé
        Remove-Item "$exe.old" -Force -ErrorAction SilentlyContinue
        Move-Item $exe "$exe.old" -Force
    }
    Copy-Item "$tmp\BatConnect.exe" $exe -Force

    $shell = New-Object -ComObject WScript.Shell
    foreach ($dossier in @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))) {
        $raccourci = $shell.CreateShortcut((Join-Path $dossier "BatConnect.lnk"))
        $raccourci.TargetPath = $exe
        $raccourci.WorkingDirectory = $dest
        $raccourci.Save()
    }
    Write-Host "==> Installé : $exe (raccourcis : Bureau et menu Démarrer)"
    Write-Host "==> Terminé. Les prochaines versions seront proposées automatiquement dans le logiciel."
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
