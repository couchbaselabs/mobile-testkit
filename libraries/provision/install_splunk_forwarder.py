
import os
import ansible_runner

if __name__ == "__main__":
    
    if not os.environ["SPLUNK_SERVER"]:
        raise Exception("You must define a SPLUNK_SERVER environment variable")

    if not os.environ["SPLUNK_SERVER_AUTH"]:
        raise Exception("You must define a SPLUNK_SERVER_AUTH environment variable")


    extra_vars = "forward_server={0} forward_server_auth={1}".format(
        os.environ["SPLUNK_SERVER"],
        os.environ["SPLUNK_SERVER_AUTH"]
    )

    status = ansible_runner.run_ansible_playbook("install-splunkforwarder.yml", extra_vars=extra_vars, stop_on_fail=False)
    assert(status == 0)

