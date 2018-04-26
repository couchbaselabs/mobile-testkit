# coding=utf-8
import winrm
import base64

proto = winrm.Protocol(endpoint='http://192.168.34.51:5985/wsman', username='localtest', password='password123!', transport='ntlm')

sid = proto.open_shell(codepage=65001)

script = u'Write-Host こんにちは'

encoded_ps = base64.b64encode(script.encode('utf_16_le')).decode('ascii')

cmdid = proto.run_command(sid, 'powershell', ['-nologo', '-command', script])

res = proto.get_command_output(sid, cmdid)

print res[0]

proto.cleanup_command(sid, cmdid)
proto.close_shell(sid)

pass

