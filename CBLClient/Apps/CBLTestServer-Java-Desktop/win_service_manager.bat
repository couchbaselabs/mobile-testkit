echo off
REM this script is to install TestServer jar file as a Windows Service

IF [%1]==[] (
  set service_name=TestServerJava
) ELSE (
 set service_name=%1
)
echo service_name=%service_name%

IF [%2]==[] (
  set status=install
) ELSE (
  set status=%2
)
echo status=%status%

REM install Windows Service requires the following parameters
IF "%status%"=="install" (
  IF [%3]==[] (
    set location=C:\\Users\\Administrator\\Desktop\\TestServer\\TestServer-java-2.7.0-94
  ) ELSE (
    set location=%3
  )
  echo location=%location%

  IF [%4]==[] (
    set jar_name=CBLTestServer-Java-Desktop-2.7.0-94-enterprise.jar
  ) ELSE (
    set jar_name=%4
  )
  echo jar_name=%jar_name%

  IF [%5]==[] (
    set service_user=Administrator
  ) ELSE (
    set service_user=%5
  )
  echo service_user=%service_user%

  IF [%6]==[] (
    set service_pwd=Membase123
  ) ELSE (
    set service_pwd=%6
  )
  echo service_pwd=%service_pwd%
)

IF "%status%"=="install" (
  REM install Windows Service, service can be found on Windows Service console listed by name
  REM service is installed but not started automatically. 
  echo %service_name%.exe //IS//%service_name% --Install=%location%\\%service_name%.exe --Description=%service_name% --Jvm=auto --Classpath=%location%\\%jar_name% --StartMode=jvm --StartClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StartMethod=windowsService --StartParams=start --StopMode=jvm --StopClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StopMethod=windowsService --StopParams=stop --LogPath=%location%\\logs --StdOutput=auto --StdError=auto --ServiceUser=.\%service_user% --ServicePassword=%service_pwd%
  %service_name%.exe //IS//%service_name% --Install=%location%\\%service_name%.exe --Description=%service_name% --Jvm=auto --Classpath=%location%\\%jar_name% --StartMode=jvm --StartClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StartMethod=windowsService --StartParams=start --StopMode=jvm --StopClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StopMethod=windowsService --StopParams=stop --LogPath=%location%\\logs --StdOutput=auto --StdError=auto --ServiceUser=.\%service_user% --ServicePassword=%service_pwd%
)
IF "%status%"=="start" (
  REM start Windows Service
  %service_name%.exe //ES//%service_name%
)
IF "%status%"=="stop" (
  REM stop Windows Service
  %service_name%.exe //SS//%service_name%
)
IF "%status%"=="remove" (
  REM remove Windows Service, if the service is running, it will stop & remove the service
  %service_name%.exe //DS//%service_name%
)
