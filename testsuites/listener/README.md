=== Dependencies

Android SDK. Download http://developer.android.com/sdk/index.html[Android Studio] to install

```
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH
```

Mono to execute LiteServ .NET on macosx
```
http://www.mono-project.com/docs/getting-started/install/mac/
```

Install libimobiledevice for capture device logging for iOS
```
$ brew install --HEAD libimobiledevice
$ brew install ideviceinstaller
```
Install ios-deploy to bootstrap install / lauching of iOS apps
```
brew install node
npm install -g ios-deploy
```

The Listener is exposed via a LiteServ application which will be downloaded and launched when running the test.

NOTE: For running with Android, you must be running an emulator or device. The easiest is Genymotion with NAT,
however devices are supported as long the sync_gateway and the android device can communicate. 

