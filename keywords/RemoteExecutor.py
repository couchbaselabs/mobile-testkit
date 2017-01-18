import paramiko
import ansible.constants

from keywords.exceptions import RemoteCommandError
from keywords.utils import log_info


def stream_output(stdio_file_stream):
    for line in stdio_file_stream:
        print(line)


class RemoteExecutor:
    """Executes remote shell commands on a host.
    This assumes that the username in the __init__ constructor
    has passwordless ssh access to the host you are communicating with.
    This username is set as the 'remote_user' in your ansible.cfg file,
    located in the root of the repository
    """

    def __init__(self, host):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client = client
        self.host = host
        self.username = ansible.constants.DEFAULT_REMOTE_USER

    def execute(self, commamd):
        """Executes a shell command on a remote host.
        It will stream the stdout and stderr and return an error code
        """

        log_info("Connecting to {}".format(self.host))
        self.client.connect(self.host, username=self.username)

        log_info("Running '{}' on host {}".format(commamd, self.host))

        # get_pty=True is required for sudo commands
        stdin, stdout, stderr = self.client.exec_command(commamd, get_pty=True)

        # We should not be sending / recieving data on the stdin channel so close it
        stdin.close()

        stdout_p = stdout.readlines()
        stream_output(stdout_p)
        stderr_p = stderr.readlines()
        stream_output(stderr_p)


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

        self.execute(command)
        if status != 0:
            raise RemoteCommandError("command: {} failed on host: {}".format(command, self.host))
