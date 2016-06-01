from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from robot.api.logger import console

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
            console("TASK [{}] ---------------------------------------------- ".format(task.name))
        super(CallbackModule, self).v2_playbook_on_task_start(task, is_conditional)

    def v2_playbook_on_include(self, included_file):
        console("TASK [include] ---------------------------------------------- ")
        console("included: {}".format(included_file))
        super(CallbackModule, self).v2_playbook_on_include(included_file)

    def v2_runner_on_ok(self, result):
        console("ok: [{}]".format(result._host))
        super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if ignore_errors:
            console("ignoring errors: [{}]".format(result._host))
        else:
            console("failed: [{}]".format(result._host))
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)

    def v2_runner_on_skipped(self, result):
        console("skipping: [{}]".format(result._host))
        super(CallbackModule, self).v2_runner_on_skipped(result)

    def v2_runner_on_unreachable(self, result):
        console("unreachable: [{}]".format(result._host))
        super(CallbackModule, self).v2_runner_on_unreachable(result)
