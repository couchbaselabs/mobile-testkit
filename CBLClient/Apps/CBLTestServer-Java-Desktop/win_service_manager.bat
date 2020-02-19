echo off
set service_name=%1
set status=%2
set location=%3
set jar_name=%4
set service_user=%5
set service_pwd=%6


IF "%status%"=="start" (
  %service_name%.exe //IS//%service_name% --Install=%location%\\%service_name%.exe --Description=%service_name% --Jvm=auto --Classpath=%location%\\%jar_name% --StartMode=jvm --StartClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StartMethod=windowsService --StartParams=start --StopMode=jvm --StopClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StopMethod=windowsService --StopParams=stop --LogPath=%location%\\logs --StdOutput=auto --StdError=auto --ServiceUser=%service_user% --ServicePassword=%service_pwd%
  
  %service_name%.exe //ES//%service_name%
) ELSE (
  %service_name%.exe //DS//%service_name%
)



