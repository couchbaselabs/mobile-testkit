import sys
from optparse import OptionParser

import kill_sync_gateway

def main():

    valid_cmds = [
        "kill-sg",
        "kill-server",
        "start-sg",
        "start-server"
    ]

    def print_help():
        print "Command Options: "
        for cmd in valid_cmds:
            print "    {}".format(cmd)

    def validate_cmd(cmd):
        if cmd in valid_cmds:
            return True
        return False

    def process_cmd(cmd, args):
        print "### Running: {0} with args {1}".format(cmd, args)
        if cmd == "kill-sg":
            if len(args) != 1:
                print "usages: kill_sg <vm_name>"
            kill_sync_gateway.kill_sync_gateway(args[0])

    while True:
        input = raw_input(">>> Enter a command (-h for help): ")

        parser = OptionParser()
        parser.add_option("-n", "", action="store", type="string", dest="vm_name", help="name of vm to target")

        cmd_args = input.split(" ")
        sub_program = cmd_args[0]
        sub_program_args = cmd_args[1:]

        if sub_program == "exit":
            print "Exiting"
            sys.exit(0)
        if validate_cmd(sub_program):
            process_cmd(sub_program, sub_program_args)
        else:
            print "!! Invalid Command"
            print_help()

if __name__ == "__main__":
    main()
