param (
    [Parameter()][string]$AppDirectory
)

$PackageFullName="b0bd6c4c-e257-44c1-aeeb-7188f65af9d0_1.0.0.0_x64__1v3rwxh47wwxj"
$LaunchName="b0bd6c4c-e257-44c1-aeeb-7188f65af9d0_1v3rwxh47wwxj!App"
if(-Not $AppDirectory) {
    $AppDirectory = "$PSScriptRoot\AppPackages\TestServer.UWP_1.0.0.0_x64_Test"
}

Remove-AppxPackage $PackageFullName -ErrorAction Ignore
Push-Location $AppDirectory
try {
    .\Add-AppDevPackage.ps1 -Force
} finally {
    Pop-Location
}

Invoke-Expression "start shell:AppsFolder\$LaunchName"