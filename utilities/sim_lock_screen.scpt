-- This script activate simulator and lock the screen
activate application "Simulator"
tell application "System Events" to tell process "Simulator" 
  keystroke "l" using command down
end tell