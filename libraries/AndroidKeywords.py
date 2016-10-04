import subprocess


class AndroidKeywords:

    def start_emulator(self, api_level):

        subprocess.check_call(["utilities/start_emulator.sh", api_level])

    def build_liteserv(self, branch):

        subprocess.check_call(["utilities/build_and_deploy_liteserv.sh", branch])
