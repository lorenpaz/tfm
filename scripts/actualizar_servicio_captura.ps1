<#
.SYNOPSIS
    Apunta el servicio NSSM "CamarasMalaga" al script de captura en scripts\ y lo reinicia.
    Ejecutar en una consola de PowerShell COMO ADMINISTRADOR desde la raíz del proyecto:
        .\scripts\actualizar_servicio_captura.ps1
#>
param(
    [string]$Nssm = "C:\Users\loren\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe",
    [string]$Servicio = "CamarasMalaga"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

& $Nssm set $Servicio Application (Join-Path $root ".venv\Scripts\python.exe")
& $Nssm set $Servicio AppParameters (Join-Path $root "scripts\captura_camaras.py")
& $Nssm set $Servicio AppDirectory (Join-Path $root "scripts")
& $Nssm restart $Servicio
& $Nssm status $Servicio
