param(
    [Parameter(Mandatory=$true)][string]$Version,
    [switch]$Community
)

if(!$Version.Contains("-")) {
    if(-Not $Community) {
        $nugetDirectory = "$HOME\.nuget\packages\couchbase.lite.enterprise"
    } else {
        $nugetDirectory = "$HOME\.nuget\packages\couchbase.lite"
    }
        
    $fullVersion = Get-ChildItem $nugetDirectory -Filter "$Version-b*" | Select-Object -Last 1 -ExpandProperty Name
} else {
    $fullVersion = $Version
}

$ShortVersion = $fullVersion.Split('-')[0]
$BuildNumber = $fullVersion.Split('-')[1].TrimStart('b', '0')
"SHORT_VERSION=$ShortVersion`r`nBLD_NUM=$BuildNumber`r`nNUGET_VERSION=$fullVersion" | Set-Content -Encoding ASCII $pwd\env.properties