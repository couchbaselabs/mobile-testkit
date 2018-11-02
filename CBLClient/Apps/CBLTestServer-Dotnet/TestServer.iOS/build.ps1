param (
    [string]$Version,
    [switch]$Community
)

function Modify-Packages {
    $filename = $args[0]
    $ver = $args[1]
    $community = $args[2]

    $content = [System.IO.File]::ReadAllLines($filename)
    $checkNextLine = $false
    for($i = 0; $i -lt $content.Length; $i++) {
        $line = $content[$i]
        $isMatch = $line -match ".*?<PackageReference Include=`"Couchbase\.Lite(.*?)`""
        if($isMatch) {
            $oldPackageName = $matches[1]
            $packageName = $oldPackageName.Replace(".Enterprise", "")
            if(-Not $community) {
                $packageName = ".Enterprise" + $packageName;
            }

            $isMatch = $line -match ".*?Version=`"(.*?)`""
            if($isMatch) {
                $oldVersion = $matches[1]
                $line = $line.Replace("Couchbase.Lite$oldPackageName", "Couchbase.Lite$packageName").Replace($oldVersion, $ver)
            } else {
                $checkNextLine = $true
            }
            
            $content[$i] = $line
        } elseif($checkNextLine) {
            $isMatch = $line -match ".*?<Version>(.*?)</Version>"
            if($isMatch) {
                $oldVersion = $matches[1]
                $line = $line.Replace($oldVersion, $ver)
                $checkNextLine = $false
                $content[$i] = $line
            } else {
                $checkNextLine = !$line.Contains("</PackageReference>")
            }
        }
    }

    [System.IO.File]::WriteAllLines($filename, $content)
}

function Calculate-Version {
    $version_to_use = (($Version, $env:VERSION -ne $null) -ne '')[0]
    if($version_to_use -eq '' -or !$version_to_use) {
        throw "Version not defined for this script!  Either pass it in as -Version or define an environment variable named VERSION"
    }

    if($version_to_use.Contains("-")) {
        return $version_to_use
    }

    return $version_to_use + "-b*"
}
cd ..
Push-Location $PSScriptRoot

$fullVersion = Calculate-Version

try {
    Modify-Packages "$PSScriptRoot/TestServer.iOS.csproj" $fullVersion $Community
    Modify-Packages "$PSScriptRoot/../TestServer/TestServer.csproj" $fullVersion $Community

    Push-Location ../TestServer
    dotnet restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer"
        exit 1
    }

    Pop-Location

    & msbuild /t:Restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer.Android"
        exit 1
    }

    if($fullVersion.EndsWith("*")) {
        $releaseVersion = $fullVersion.Split("-")[0]
        if(-Not $Community) {
            $nugetDirectory = "$HOME/.nuget/packages/couchbase.lite.enterprise"
        } else {
            $nugetDirectory = "$HOME/.nuget/packages/couchbase.lite"
        }
        
        $env:NUGET_VERSION = Get-ChildItem $nugetDirectory -Filter "$releaseVersion-b*" | Select-Object -Last 1 -ExpandProperty Name
    } else {
        $env:NUGET_VERSION = $fullVersion
    }

    "NUGET_VERSION=$env:NUGET_VERSION" | Set-Content $env:WORKSPACE\env.properties
    security unlock-keychain -p Passw0rd /Users/mobile/Library/Keychains/login.keychain-db
    & msbuild /p:Configuration=Release /p:Platform=iPhoneSimulator /t:Rebuild
    if($LASTEXITCODE -ne 0) {
        Write-Error "Build failed for TestServer.iOS"
        exit 1
    }

    if(-Not (Test-Path "zips")) {
        New-Item -ItemType Directory "zips"
    }

    if(Test-Path "zips/TestServer.iOS.zip") {
        Remove-Item "zips/TestServer.iOS.zip"
    }
    
    $ZipPath = Resolve-Path "./zips"

    Push-Location "bin/iPhoneSimulator/Release"
    try {
        zip -r TestServer.iOS.zip TestServer.iOS.app
        Copy-Item TestServer.iOS.zip $ZipPath/TestServer.iOS.zip
    } finally {
        Pop-Location
    }
    
    Remove-Item -Recurse -Force bin
    Remove-Item -Recurse -Force obj
    Push-Location ../TestServer
     dotnet restore
     if($LASTEXITCODE -ne 0) {
         Write-Error "Restore failed for TestServer"
         exit 1
     }

    Pop-Location
    & msbuild /t:Restore
    & msbuild /p:Configuration=Release /p:Platform=iPhone /t:Rebuild
    if($LASTEXITCODE -ne 0) {
        Write-Error "Build failed for TestServer.iOS"
        exit 1
    }

    Push-Location "bin/iPhone/Release"
    mv TestServer.iOS.app TestServer.iOS-Device.app
    zip -r $ZipPath/TestServer.iOS.zip TestServer.iOS-Device.app
    Pop-Location
} finally {
    Pop-Location
}
