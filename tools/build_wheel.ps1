Param(
  [string]$BuildType = "Release"
)

$ErrorActionPreference = "Stop"

Write-Host "[build_wheel] Configuring CMake ($BuildType)" -ForegroundColor Cyan
if (!(Test-Path build)) { New-Item -ItemType Directory build | Out-Null }
cmake -S . -B build -DCMAKE_BUILD_TYPE=$BuildType | Out-Null
cmake --build build --config $BuildType -j

Write-Host "[build_wheel] Note: For packaging, prefer scikit-build-core with a pyproject.toml in a future task." -ForegroundColor Yellow
Write-Host "[build_wheel] For now, the built extension should be under build/bindings/python/pyvesper/." -ForegroundColor Yellow


