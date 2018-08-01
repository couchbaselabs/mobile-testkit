set mode to system attribute "mode"
tell application "System Preferences"
activate
set current pane to pane "com.apple.Network-Link-Conditioner"
end tell

tell application "System Events"
 tell process "System Preferences"
  tell window "Network Link Conditioner"
    delay 3
    click button "ON"
    tell group 1
        click pop up button 1
        click menu item mode of menu 1 of pop up button 1
    end tell
  end tell
  tell window "Network Link Conditioner" to quit
 end tell
end tell