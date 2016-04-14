import subprocess


class NetworkUtils:

    def list_connections(self):
        output = subprocess.check_output("netstat -ant | awk '{print $6}' | sort | uniq -c | sort -n", shell=True)
        print(output)

