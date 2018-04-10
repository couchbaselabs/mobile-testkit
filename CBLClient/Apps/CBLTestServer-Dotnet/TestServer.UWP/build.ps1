param (
    [Parameter()][string]$Version,
    [Parameter()][int]$BuildNum,
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
    $version_to_use = (($Version, $env:Version -ne $null) -ne '')[0]
    if($version_to_use -eq '' -or !$version_to_use) {
        throw "Version not defined for this script!  Either pass it in as -Version or define an environment variable named VERSION"
    }

    $build_num_to_use = (($BuildNum, $env:BLD_NUM, '*' -ne $null) -ne 0)[0]
    if($build_num_to_use -ne '*') {
        $build_num_to_use = ([int]$build_num_to_use).ToString("D4")
    }

    return $version_to_use + "-b" + $build_num_to_use
}

Push-Location $PSScriptRoot
$VSRegistryKey = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\SxS\VS7"
$VSInstall = (Get-ItemProperty -Path $VSRegistryKey -Name "15.0") | Select-Object -ExpandProperty "15.0"
if(-Not $VSInstall) {
    throw "Unable to locate VS2017 installation"
}

$MSBuild = "$VSInstall\MSBuild\15.0\Bin\MSBuild.exe"

$fullVersion = Calculate-Version

try {
    Modify-Packages "$PSScriptRoot\TestServer.UWP.csproj" $fullVersion $Community
    Modify-Packages "$PSScriptRoot\..\TestServer\TestServer.csproj" $fullVersion $Community

    Push-Location ..\TestServer
    dotnet restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer"
        exit 1
    }

    Pop-Location

    if($fullVersion.EndsWith("*")) {
        $releaseVersion = $fullVersion.Split("-")[0]
        if(-Not $Community) {
            $nugetDirectory = "$HOME\.nuget\packages\couchbase.lite.enterprise"
        } else {
            $nugetDirectory = "$HOME\.nuget\packages\couchbase.lite"
        }
        
        $env:NUGET_VERSION = Get-ChildItem $nugetDirectory -Filter "$releaseVersion-b*" | Select-Object -Last 1 -ExpandProperty Name
    } else {
        $env:NUGET_VERSION = $fullVersion
    }

    & $MSBuild /t:Restore
    if($LASTEXITCODE -ne 0) {
        Write-Error "Restore failed for TestServer.UWP"
        exit 1
    }

    & $MSBuild /p:Configuration=Release /t:Rebuild /p:Platform=x64
    if($LASTEXITCODE -ne 0) {
        Write-Error "Build failed for TestServer.UWP"
        exit 1
    }

    if(-Not (Test-Path "zips")) {
        New-Item -ItemType Directory "zips"
    }

    if(Test-Path "zips\TestServer.UWP.zip") {
        Remove-Item "zips\TestServer.UWP.zip"
    }
    
    $ZipPath = Resolve-Path ".\zips"

    Push-Location "AppPackages\TestServer.UWP_1.0.0.0_x64_Test"
    try {
        7z a -r ${ZipPath}\TestServer.UWP.zip *
        7z a ${ZipPath}\TestServer.UWP.zip ..\..\run.ps1
        7z a ${ZipPath}\TestServer.UWP.zip ..\..\stop.ps1
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}