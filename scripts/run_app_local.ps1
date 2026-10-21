# Runs the Streamlit app locally against the Databricks workspace, using your CLI login
# (profile Brick). Deployed, the same variables come from app.yaml resources instead.
#
#   pwsh scripts/run_app_local.ps1            -> http://localhost:8501

param(
    [string]$DbProfile = "Brick",
    [string]$WarehouseId = "1248956e7aafdfec",
    [string]$GenieSpaceId = "01f1cd86c2551a3d8fd3868fbfa90429",
    [int]$Port = 8501
)

$env:DATABRICKS_CONFIG_PROFILE = $DbProfile
$env:DATABRICKS_WAREHOUSE_ID = $WarehouseId
$env:GENIE_SPACE_ID = $GenieSpaceId

$root = Split-Path $PSScriptRoot
Set-Location (Join-Path $root "app")   # so Streamlit picks up app/.streamlit/config.toml
& (Join-Path $root ".venv\Scripts\python.exe") -m streamlit run app.py `
    --server.port $Port --server.headless true
