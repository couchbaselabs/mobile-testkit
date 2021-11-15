import paramiko
import ansible.constants

from keywords.exceptions import RemoteCommandError
from keywords.utils import log_info
from keywords.constants import REMOTE_EXECUTOR_TIMEOUT
from utilities.cluster_config_utils import load_cluster_config_json


def stream_output(stdio_file_stream):
    lines = []
    for line in stdio_file_stream:
        print(line)
        lines.append(line)
    return lines


class RemoteExecutor:
    """Executes remote shell commands on a host.
    This assumes that the username in the __init__ constructor
    has passwordless ssh access to the host you are communicating with.
    This username is set as the 'remote_user' in your ansible.cfg file,
    located in the root of the repository
    """

    def __init__(self, host, sg_platform="centos", username=None, password=None, cluster_config=None):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client = client
        self.host = host
        self.sg_platform = sg_platform
        if "[" in self.host:
            self.host = self.host.replace("[", "")
            self.host = self.host.replace("]", "")
        if cluster_config is not None:
            if sg_platform == "windows" or sg_platform == "macos":
                json_cluster = load_cluster_config_json(cluster_config)
                username = json_cluster["sync_gateways:vars"]["ansible_user"]
                password = json_cluster["sync_gateways:vars"]["ansible_password"]
        self.username = ansible.constants.DEFAULT_REMOTE_USER
        if username is not None:
            self.username = username
            self.password = password

    def execute(self, command):
        """Executes a shell command on a remote host.
        It will stream the stdout and stderr and return an error code
        """

        log_info("Connecting to {}".format(self.host))
        log_info("Running '{}' on host {}".format(command, self.host))
        if self.sg_platform == "windows":
            self.client.connect(self.host, username=self.username, password=self.password, banner_timeout=REMOTE_EXECUTOR_TIMEOUT)
            command = "cmd /c " + command
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
        elif self.sg_platform.startswith("c-"):
            self.client.connect(self.host, username=self.username, password=self.password,
                                banner_timeout=REMOTE_EXECUTOR_TIMEOUT)
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
        else:
            if "macos" in self.sg_platform:
                self.client.connect(self.host, username=self.username, password=self.password, banner_timeout=REMOTE_EXECUTOR_TIMEOUT)
            else:
                self.client.connect(self.host, username=self.username, banner_timeout=REMOTE_EXECUTOR_TIMEOUT)
            # get_pty=True is required for sudo commands
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True)

        # We should not be sending / recieving data on the stdin channel so close it
        stdin.close()

        # Stream output to console, and capture all of the output.
        # TODO: this is not memory efficient and if there is a ton of output, this will blow up
        stdout_p = stream_output(stdout)
        stderr_p = stream_output(stderr)

        # this will block until the command has completed and will return the error code from
        # the command. If the command does not return an exit status, then -1 is returned
        status = stdout.channel.recv_exit_status()

        log_info("Closing connection to {}".format(self.host))
        self.client.close()

        return status, stdout_p, stderr_p

    def must_execute(self, command):
        """This wraps self.execute(command) and throws
        an exception if the status returned is non-zero
        """

        status, stdout_p, stderr_p = self.execute(command)
        if status != 0:
            log_info("{}: {}".format(stdout_p, stderr_p))
            raise RemoteCommandError("command: {} failed on host: {}".format(command, self.host))
        return stdout_p, stderr_p
