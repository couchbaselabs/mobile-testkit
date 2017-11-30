-- This script activate simulator and close(minimize) the app
activate application "Simulator"
tell application "System Events" to tell process "Simulator" 
  keystroke "H" using command down
end tell
