# Скачивание встроенного Python и настройка pip (вызывается из Собрать_установщик.bat)
$ErrorActionPreference = 'Stop'
$embedUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip = Join-Path $root 'python-embed.zip'
$out = Join-Path $root 'python'

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Write-Host 'Скачиваю Python...'
Invoke-WebRequest -Uri $embedUrl -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $out -Force
Remove-Item $zip -Force

$pthFile = Get-ChildItem (Join-Path $out 'python*._pth') | Select-Object -First 1
if ($pthFile) {
    $lines = Get-Content $pthFile.FullName
    $lines = $lines -replace '^# import site', 'import site'
    $lines + 'Lib/site-packages' | Set-Content $pthFile.FullName
}

Write-Host 'Скачиваю get-pip...'
Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile (Join-Path $out 'get-pip.py') -UseBasicParsing
& (Join-Path $out 'python.exe') (Join-Path $out 'get-pip.py')
if ($LASTEXITCODE -ne 0) { exit 1 }
exit 0
