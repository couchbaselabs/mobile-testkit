$MyPath = Split-Path $MyInvocation.MyCommand.Source
Push-Location $MyPath

try {
    dotnet restore
    dotnet publish -c Release

    if(-Not (Test-Path "zips")) {
        New-Item -ItemType Directory "zips"
    }

    if(Test-Path "zips\TestServer.zip") {
        Remove-Item "zips\TestServer.zip"
    }
    
    $ZipPath = Resolve-Path ".\zips"

    Push-Location bin\Release\netcoreapp2.0\publish
    try {
        7z a -r ${ZipPath}\TestServer.zip *
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}