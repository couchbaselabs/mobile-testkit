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

    # def v2_playbook_on_task_start(self, task, is_conditional):
    #     console("TASK[{}] *********************************************** ".format(task.name))
    #     self.last_task = task
    #     self.shown_title = False
    #
    # def display_task_banner(self):
    #     if not self.shown_title:
    #         self.super_ref.v2_playbook_on_task_start(self.last_task, None)
    #         self.shown_title = True
    #
    # def v2_runner_on_failed(self, result, ignore_errors=False):
    #     console("v2_runner_on_failed: {}".format(str(result)))
    #     self.display_task_banner()
    #     self.super_ref.v2_runner_on_failed(result, ignore_errors)
    #
    # def v2_runner_on_ok(self, result):
    #     console("v2_runner_on_ok: {}".format(str(result)))
    #     if result._result.get('changed', False):
    #         self.display_task_banner()
    #         self.super_ref.v2_runner_on_ok(result)
    #     else:
    #         pass
    #
    # def v2_runner_on_unreachable(self, result):
    #     console("v2_runner_on_unreachable: {}".format(str(result)))
    #     self.display_task_banner()
    #     self.super_ref.v2_runner_on_unreachable(result)
    #
    # def v2_runner_on_skipped(self, result):
    #     console("v2_runner_on_skipped: {}".format(str(result)))
    #     pass
    #
    # def v2_playbook_on_include(self, included_file):
    #     console("v2_playbook_on_include: {}".format(str(included_file)))
    #     pass
    #
    # def v2_playbook_item_on_ok(self, result):
    #     console("v2_playbook_item_on_ok: {}".format(str(result)))
    #     self.display_task_banner()
    #     self.super_ref.v2_playbook_item_on_ok(result)
    #
    # def v2_playbook_item_on_skipped(self, result):
    #     console("v2_playbook_item_on_skipped: {}".format(str(result)))
    #     pass
    #
    # def v2_playbook_item_on_failed(self, result):
    #     console("v2_playbook_item_on_failed: {}".format(str(result)))
    #     self.display_task_banner()
    #     self.super_ref.v2_playbook_item_on_failed(result)