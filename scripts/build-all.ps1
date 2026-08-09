$ErrorActionPreference = 'Stop'

Write-Host '=== HermesX Desktop Build ==='

& "${PSScriptRoot}\build-backend.ps1"
& "${PSScriptRoot}\build-desktop.ps1"

Write-Host 'All builds completed.'
