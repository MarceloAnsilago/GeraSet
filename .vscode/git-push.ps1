$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

$status = git status --porcelain

if (-not $status) {
    Write-Host "Nenhuma alteracao para enviar."
    git status --short --branch
    exit 0
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$message = "Atualizacao pelo VS Code - $timestamp"

git add -A
git commit -m $message
git push

Write-Host ""
Write-Host "Alteracoes enviadas para o GitHub."
