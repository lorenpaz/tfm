<#
.SYNOPSIS
    Gestión del servidor CVAT local (Docker) para la anotación del TFM.

.DESCRIPTION
    Uso (desde la raíz del proyecto):
        .\cvat\cvat.ps1 instalar      # clona CVAT (versión fijada), arranca contenedores y crea el superusuario
        .\cvat\cvat.ps1 arrancar      # docker compose up -d
        .\cvat\cvat.ps1 parar         # docker compose stop (conserva datos)
        .\cvat\cvat.ps1 estado        # estado de los contenedores y de la API
        .\cvat\cvat.ps1 superusuario  # (re)crea el usuario admin con la contraseña de cvat\.env
        .\cvat\cvat.ps1 logs          # últimos logs del servidor

    Requisitos: Docker Desktop (backend WSL2) en ejecución y git.
    La versión de CVAT debe coincidir con cvat-sdk de requirements.txt.
    Las credenciales se guardan en cvat\.env (excluido de git) y las lee 03_anotacion_cvat.ipynb.
    Interfaz web: http://localhost:8080
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("instalar", "arrancar", "parar", "estado", "superusuario", "logs")]
    [string]$Accion = "estado"
)

$ErrorActionPreference = "Stop"

# PowerShell 5.1 trata como error cualquier salida por stderr de un ejecutable (git, docker
# escriben su progreso ahí). Se ejecutan con Continue y se comprueba el código de salida.
function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { "$_" }
    }
    finally {
        $ErrorActionPreference = $previous
    }
    if ($LASTEXITCODE -ne 0) { throw "$Exe $($Arguments -join ' ') falló ($LASTEXITCODE)" }
}

function Assert-DockerEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker no está instalado o no está en el PATH. Instala Docker Desktop y ábrelo."
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $version = & docker version --format "{{.Server.Version}}" 2>$null
    $ErrorActionPreference = $previous
    if ($LASTEXITCODE -ne 0 -or -not $version) {
        throw "El motor de Docker no responde. Abre Docker Desktop, acepta el acuerdo inicial y espera a 'Engine running'."
    }
}

$CvatVersion = "v2.78.0"
$CvatDir = Join-Path $PSScriptRoot "cvat-server"
$EnvFile = Join-Path $PSScriptRoot ".env"
$CvatUrl = "http://localhost:8080"

function Get-CvatEnv {
    if (-not (Test-Path $EnvFile)) {
        $password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
        @(
            "CVAT_URL=$CvatUrl",
            "CVAT_USER=admin",
            "CVAT_EMAIL=admin@localhost",
            "CVAT_PASSWORD=$password"
        ) | Set-Content -Path $EnvFile -Encoding utf8
        Write-Host "Credenciales generadas en $EnvFile"
    }
    $values = @{}
    Get-Content $EnvFile | Where-Object { $_ -match "^\s*([^#=]+)=(.*)$" } | ForEach-Object {
        $values[$Matches[1].Trim()] = $Matches[2].Trim()
    }
    return $values
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    if (-not (Test-Path $CvatDir)) {
        throw "CVAT no está instalado. Ejecuta primero: .\cvat\cvat.ps1 instalar"
    }
    Assert-DockerEngine
    Push-Location $CvatDir
    try {
        $env:CVAT_VERSION = $CvatVersion
        Invoke-Native "docker" (@("compose") + $ComposeArgs)
    }
    finally {
        Pop-Location
    }
}

function Wait-CvatApi {
    Write-Host "Esperando a que la API de CVAT responda..."
    for ($i = 0; $i -lt 180; $i++) {
        try {
            $about = Invoke-RestMethod -Uri "$CvatUrl/api/server/about" -TimeoutSec 5
            Write-Host "CVAT $($about.version) disponible en $CvatUrl"
            return
        }
        catch {
            Start-Sleep -Seconds 5
        }
    }
    throw "CVAT no respondió en 15 minutos (el primer arranque aplica las migraciones de la base de datos). Revisa: .\cvat\cvat.ps1 logs"
}

function New-Superuser {
    $cfg = Get-CvatEnv
    Write-Host "Creando superusuario '$($cfg.CVAT_USER)'..."
    $cmd = "python3 ~/manage.py createsuperuser --noinput --username $($cfg.CVAT_USER) --email $($cfg.CVAT_EMAIL) " +
           "|| echo 'El usuario ya existe'"
    Invoke-Native "docker" @("exec", "-e", "DJANGO_SUPERUSER_PASSWORD=$($cfg.CVAT_PASSWORD)", "cvat_server", "bash", "-c", $cmd)
}

switch ($Accion) {
    "instalar" {
        Assert-DockerEngine
        if (-not (Test-Path (Join-Path $CvatDir "docker-compose.yml"))) {
            Remove-Item -Recurse -Force $CvatDir -ErrorAction SilentlyContinue
            Invoke-Native "git" @("clone", "--depth", "1", "--branch", $CvatVersion, "https://github.com/cvat-ai/cvat.git", $CvatDir)
        }
        Invoke-Compose @("up", "-d")
        Wait-CvatApi
        New-Superuser
        $cfg = Get-CvatEnv
        Write-Host "`nListo. Entra en $CvatUrl con usuario '$($cfg.CVAT_USER)' (contraseña en $EnvFile)."
    }
    "arrancar" {
        Invoke-Compose @("up", "-d")
        Wait-CvatApi
    }
    "parar" {
        Invoke-Compose @("stop")
    }
    "estado" {
        Invoke-Compose @("ps")
        try {
            $about = Invoke-RestMethod -Uri "$CvatUrl/api/server/about" -TimeoutSec 5
            Write-Host "API OK - CVAT $($about.version) en $CvatUrl"
        }
        catch {
            Write-Host "La API de CVAT no responde en $CvatUrl"
        }
    }
    "superusuario" {
        New-Superuser
    }
    "logs" {
        Invoke-Native "docker" @("logs", "--tail", "100", "cvat_server")
    }
}
