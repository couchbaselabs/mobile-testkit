import os
import sys
from flask import Flask
from optparse import OptionParser

app = Flask(__name__, static_url_path='')


@app.route("/syncFunction")
def sync_function():
    return """function(doc, oldDoc){
                throw({forbidden: "read only!"})
                    }"""


@app.route("/importFilter")
def import_filter():
    return 'function(doc){ return doc.type == "mobile"}'


@app.route("/conflictResolver")
def conflict_resolver():
    return """function (conflict) {
    if (conflict.LocalDocument.priority > conflict.RemoteDocument.priority) {
        return conflict.LocalDocument;
    } else if (conflict.LocalDocument.priority < conflict.RemoteDocument.priority) {
        return conflict.RemoteDocument;
    }
    return defaultPolicy(conflict);
}"""


@app.route("/webhookFilter")
def webhook_filter():
    return 'function(doc) { if (doc.content.data == "webhook_filter") { return true } return false }'


if __name__ == '__main__':

    usage = """ usage: host_sgw_jscode.py --start --sslstart --stop"""

    parser = OptionParser(usage=usage)

    parser.add_option("--start",
                      action="store_true", dest="start", default=False,
                      help="will start the hosting the jscode")

    parser.add_option("--stop",
                      action="store_true", dest="stop", default=False,
                      help="will stop hosting the jscode")

    parser.add_option("--sslstart",
                      action="store_true", dest="sslstart", default=False,
                      help="will start the hosting the jscode")

    arg_parameters = sys.argv[1:]
    (opts, args) = parser.parse_args(arg_parameters)
    if opts.start and opts.stop:
        raise Exception("use either one of the flage from --start or --stop")

    if opts.start:
        app.run(host='0.0.0.0', port=5007)

    if opts.stop:
        command = "kill $(ps aux | grep 'host_sgw_jscode.py --start' | awk '{print $2}')"
        os.system(command)

    if opts.sslstart:
        app.run(host='0.0.0.0', port=5007, ssl_context='adhoc')
