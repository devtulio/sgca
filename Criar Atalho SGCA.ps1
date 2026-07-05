# Cria atalho "Iniciar SGCA.lnk" na Area de Trabalho com icone personalizado
$batPath  = Join-Path $PSScriptRoot "Iniciar SGCA.bat"
$icoPath  = Join-Path $PSScriptRoot "sgca.ico"
$desktop  = [Environment]::GetFolderPath("Desktop")
$lnkPath  = Join-Path $desktop "Iniciar SGCA.lnk"

$wsh  = New-Object -ComObject WScript.Shell
$link = $wsh.CreateShortcut($lnkPath)
$link.TargetPath       = $batPath
$link.IconLocation     = "$icoPath,0"
$link.WorkingDirectory = $PSScriptRoot
$link.WindowStyle      = 7
$link.Description      = "SGCA - Sistema de Gestao de Contratos e Atas"
$link.Save()

Write-Host "Atalho criado em: $lnkPath" -ForegroundColor Green
