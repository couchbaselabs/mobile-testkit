from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from robot.api.logger import info

class CallbackModule(CallbackModule_default):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'robot_tee'

    def __init__(self):
        self.super_ref = super(CallbackModule, self)
        self.super_ref.__init__()
        self.last_task = None
        self.shown_title = False

    def v2_playbook_on_task_start(self, task, is_conditional):
        if len(task.name) > 0:
            info("TASK [{}] ---------------------------------------------- ".format(task.name), also_console=True)
        super(CallbackModule, self).v2_playbook_on_task_start(task, is_conditional)

    def v2_playbook_on_include(self, included_file):
        info("TASK [include] ---------------------------------------------- ", also_console=True)
        info("included: {}".format(included_file), also_console=True)
        super(CallbackModule, self).v2_playbook_on_include(included_file)

    def v2_runner_on_ok(self, result):
        info("ok: [{}]".format(result._host), also_console=True)
        super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if ignore_errors:
            info("ignoring errors: [{}]".format(result._host), also_console=True)
        else:
            info("failed: [{}]".format(result._host), also_console=True)
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)

    def v2_runner_on_skipped(self, result):
        info("skipping: [{}]".format(result._host), also_console=True)
        super(CallbackModule, self).v2_runner_on_skipped(result)

    def v2_runner_on_unreachable(self, result):
        info("unreachable: [{}]".format(result._host), also_console=True)
        super(CallbackModule, self).v2_runner_on_unreachable(result)
