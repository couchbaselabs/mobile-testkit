param (
    [Parameter][string]$Version,
    [Parameter][int]$BuildNum,
    [switch]$Community
)

function Modify-Packages {
    $filename = $args[0]
    $ver = $args[1]
    $community = $args[2]

    $content = [System.IO.File]::ReadAllLines($filename)
    $regex = New-Object -TypeName "System.Text.RegularExpressions.Regex" ".*?<PackageReference Include=`"Couchbase\.Lite(.*?)`" Version=`"(.*?)`""
    for($i = 0; $i -lt $content.Length; $i++) {
        $line = $content[$i]
        $matches = $regex.Matches($line)
        if($matches.Count -gt 0) {
            $oldPackageName = $matches[0].Groups[1].Value;
            $packageName = $oldPackageName.Replace(".Enterprise", "")
            if(-Not $community) {
                $packageName = ".Enterprise" + $packageName;
            }

            $oldVersion = $matches[0].Groups[2]
            $line = $line.Replace("Couchbase.Lite$oldPackageName", "Couchbase.Lite$packageName").Replace($oldVersion, $ver)
            $content[$i] = $line
        }
    }

    [System.IO.File]::WriteAllLines($filename, $content)
}

Push-Location $PSScriptRoot

$version_to_use = $Version
if(-Not $version_to_use) {
    if(-Not $env:VERSION) {
        throw "Version not defined for this script!  Either pass it in as -Version or define an environment variable named VERSION"
    }

    $version_to_use = $env:VERSION
}

$build_num_to_use = $BuildNum
if(-Not $build_num_to_use) {
    if(-Not $env:BLD_NUM) {
        throw "Build Number not defined for this script!  Either pass it in as -BuildNum or define an environment variable named BLD_NUM"
    }

    $build_num_to_use = [int]$env:BLD_NUM
}

try {
    if($build_num_to_use -lt 538) {
        $Community = $true
    }

    $fullVersion = $version_to_use + "-b" + $build_num_to_use.ToString("D4")
    Modify-Packages "$PSScriptRoot\TestServer.NetCore.csproj" $fullVersion $Community
    Modify-Packages "$PSScriptRoot\..\TestServer\TestServer.csproj" $fullVersion $Community

    Push-Location ..\TestServer
    dotnet restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer"
        exit 1
    }

    Pop-Location

    dotnet restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer.NetCore"
        exit 1
    }

    dotnet publish -c Release
    if($LASTEXITCODE -ne 0) {
        Write-Error "Publish failed for TestServer.NetCore"
        exit 1
    }

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