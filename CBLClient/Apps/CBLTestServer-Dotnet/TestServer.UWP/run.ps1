param (
    [Parameter()][string]$AppDirectory
)

$PackageFullName="b0bd6c4c-e257-44c1-aeeb-7188f65af9d0_1.0.0.0_x64__75cr2b68sm664"
$LaunchName="b0bd6c4c-e257-44c1-aeeb-7188f65af9d0_75cr2b68sm664!App"
if(-Not $AppDirectory) {
    $AppDirectory = $PSScriptRoot
}

Remove-AppxPackage $PackageFullName -ErrorAction Ignore
Push-Location $AppDirectory
try {
    .\Add-AppDevPackage.ps1 -Force
} finally {
    Pop-Location
}

Invoke-Expression "start shell:AppsFolder\$LaunchName"