from keywords.utils import log_info

'''
Created on 16-Jan-2018

@author: hemant
'''
from collections import OrderedDict
import re
import os
from subprocess import Popen


literal = ("SELECT",
           "FROM",
           "WHERE")

prec = {"+": 0,
        "-": 0,
        "*": 0,
        "/": 0,
        "%": 0,
        "<": 0,
        "<=": 0,
        "=": 0,
        ">": 0,
        ">=": 0,
        "!=": 0,
        "BETWEEN": 1,
        "AND": 2,
        "OR": 2,
        "NOT": 1,
        "IN": 1,
        "IS": 1,
        "IS-NOT": 1,
        "IS-NULL": 1,
        "EXIST": 1,
        "LIKE": 1,
        "LIKE": 1,
        "IS-MISSING": 1,
        "IS-NOT-MISSING": 1,
        "IS-NOT-NULL": 1,
        "IS-NULL": 1,
        "ANY-AND-EVERY": 1,
        "NOT-IN": 1,
        '(': 3,
        ')': 3}

arithmetic_operator = ("+",
                       "-",
                       "*",
                       "/",
                       "%",
                       "<",
                       "<=",
                       "=",
                       ">",
                       ">=",
                       "!=")

logical_operator = ("BETWEEN",
                    "AND",
                    "OR",
                    "NOT",
                    "IN",
                    "IS",
                    "IS-NOT",
                    "IS-NULL",
                    "EXIST",
                    "LIKE",
                    "IS-NOT",
                    "IS-MISSING",
                    "IS-NOT-MISSING",
                    "IS-NOT-NULL",
                    "IS-NULL",
                    "ANY-AND-EVERY",
                    "NOT-IN",)

operators = logical_operator + arithmetic_operator + ('(', ')')

trans_op = {
    "IS NOT": "IS-NOT",
    "NOT IN": "NOT-IN",
    "IS MISSING": "IS-MISSING",
    "IS NOT MISSING": "IS-NOT-MISSING",
    "IS NOT NULL": "IS-NOT-NULL",
    "IS NULL": "IS-NULL",
    "ANY AND EVERY": "ANY-AND-EVERY",
}

operations = {
    "+": "2+",
    "-": "1-2",
    "*": "2+",
    "/": "2",
    "%": "2",
    "`": "1",
    "=": "2",
    "!=": "2",
    "<": "2",
    "<=": "2",
    ">": "2",
    ">=": "2",
    "BETWEEN": "3",
    "IS": "2",
    "IS-NOT": "2",
    "LIKE": "2",
    "NOT-LIKE": "2",
    "MATCH": "2",
    "IN": "2",
    "NOT-IN": "2",
    "EXISTS": "1",
    "IS-MISSING": "1",
    "IS-NOT-MISSING": "1",
    "IS-NULL": "1",
    "IS-NOT-NULL": "1",
    "COLLATE": "2",
    "NOT": "1",
    "AND": "2",
    "OR": "2",
    "CASE": "2+",
    "WHEN": "2",
    "ELSE": "1",
    "ANY": "3",
    "EVERY": "3",
    "ANY-AND-EVERY": "3",
    ".": "0+",
    "$": "1",
    "?": "1+"
}


def get_operand(token):
    if token.startswith('$'):
        return ['."$"{}'.format(token[1:])]
#         return "".join([".", "$", token[1:]])
    elif token.isdigit():
        return int(token)
    elif token == "meta().id":
        return ["._id"]
    elif token.startswith('"'):
        if token == '"True"' or token == '"true"':
            return "true"
        elif token == '"False"' or token == '"false"':
            return "false"
        return token.strip('"')
    elif token == "null":
        return "null"
    elif token.isalpha():
        return ["".join(['.', token])]
    else:
        return token


def get_prefix_list(query):
    between_pattern = re.compile("BETWEEN ([0-9]+) and ([0-9]+)")
    between_match = re.search(between_pattern, query)

    if between_match:
        num1, num2 = between_match.groups()
        target_pattern = "BETWEEN {} and {}".format(num1, num2)
        replacement_pattern = "BETWEEN {} {}".format(num1, num2)
        query = re.sub(target_pattern, replacement_pattern, query)

    query = query.split()
    item_list = []
    split_word = ''
    for word in query:
        if word.startswith('"') and not word.endswith('"'):
            split_word += word
        elif not word.startswith('"') and word.endswith('"'):
            split_word += " " + word
            item_list.append(split_word)
            split_word = ''
        elif split_word != '':
            split_word += " " + word
        else:
            item_list.append(word)
    query = item_list
    query.reverse()
    for index, item in enumerate(query):
        if item == '(':
            query[index] = ')'
        elif item == ')':
            query[index] = '('
    query = ['('] + query + [')']

    opstack = []
    result = []

    for token in query:
        if token not in operators:
            operand = get_operand(token)
            if isinstance(operand, int) or isinstance(operand, float):
                result.append(operand)
            else:
                # result.append('[{}]'.format(get_operand(token)))
                result.append(operand)
        elif token == '(':
            opstack.append(token)
        elif token == ')':
            while opstack[-1] != '(':
                item = opstack.pop()
                result.append(item)
            opstack.pop()
        else:
            while prec[token] > prec[opstack[-1]]:
                item = opstack.pop()
                result.append(item)
            opstack.append(token)

    result.reverse()
    return result


def prefix_evaluation(prefix_list):
    opstack = []
    for token in prefix_list[::-1]:
        if token not in operators:
            opstack.append(token)
        else:
            num_of_pop = int(operations[token])
            opd = []
            if token == 'IN':
                var = opstack.pop().strip()
                while opstack[-1] != ']':
                    item = opstack.pop()
                    #print "*" + item + "*" + str(len(item))
                    if item == '[' or item == ',':
                        continue
                    opd.append(item)
                opstack.pop()
                opd = [var, opd]
            else:
                for _ in range(int(num_of_pop)):
                    item = opstack.pop()
                    opd.append(item)
            eq = [token] + opd
            opstack.append(eq)
    return opstack.pop()


def clear_evaluated_list(eval_list, prev_op=None):
    eval_list = eval_list.split()
    result = []
    for item in eval_list:
        if item in logical_operator:
            item = item.replace("-", " ")
            result.append(item)
            prev_op = item
        else:
            if isinstance(item, list):
                if item[0] == prev_op:
                    result.extend(clear_evaluated_list(item[1:], prev_op))
                elif item in logical_operator:
                    result.append(clear_evaluated_list(item, item[1]))
                else:
                    result.append(item)
            else:
                result.append(item)
    return " ".join(result)


def get_json_query(query="SELECT name.first, name.last FROM students WHERE grade = 12 AND gpa >= $GPA"):
    # removing extra white spaces from the query string
    query = ' '.join(query.split())

    query = multiple_replace(query, trans_op)
    pattern = re.compile(r"SELECT (.*?) FROM (.*?) WHERE (.*)", re.IGNORECASE)
    regex_out = re.search(pattern, query)
    select_token, from_token, where_token = regex_out.groups()
    json_txt = OrderedDict()

    # creating select statement
    tokens = select_token.split(',')
    json_txt["WHAT"] = []
    for item in tokens:
        item = item.strip()
        tk_list = []
        if "meta().id" in item:
            tk_list.append("._id")
        elif '.' in item:
            tk_list.extend(item.split('.'))
        elif item == '*':
            tk_list.append(".")
        else:
            tk_list.append(".{}".format(item))
        json_txt["WHAT"].append(tk_list)

    # creating from statement
    # json_txt["FROM"] = []
    # for db in from_token.strip().split(' '):
    #     json_txt["FROM"].append([".", db])
    # creating where statement
    json_txt["WHERE"] = []
    json_txt["WHERE"] = prefix_evaluation(get_prefix_list(where_token.strip()))
    json_txt["DISTINCT"] = '"False"'
    if 'DISTINCT' in select_token.strip():
        out = re.search("DISTINCT\((.*?)\)", select_token)
        select_token = out.groups()[0]
        json_txt["DISTINCT"] = '"True"'
    return json_txt


def multiple_replace(text, a_dict):
    rx = re.compile('|'.join(map(re.escape, a_dict)))

    def one_xlat(match):
        return a_dict[match.group(0)]
    return rx.sub(one_xlat, text)

def converty_to_json_string(query):
    query_str = ''
    for k, v in query.iteritems():
        query_str += k + ": " + str(v).replace('\'', '"') + ", "
    query_str = '{ ' + query_str.rstrip(", ") + ' }'
    query_str = query_str.replace('"true"', 'true')
    query_str = query_str.replace('"null"', 'null')
    query_str = query_str.replace('[', '[ ')
    query_str = query_str.replace(']', '] ')
    return query_str

if __name__ == '__main__':
    queries = [
        'SELECT * FROM `travel-sample` WHERE meta().id = "airline_10"',
        'SELECT name, type, meta().id FROM `travel-sample` WHERE country = "France"',
        'SELECT meta().id FROM `travel-sample` WHERE type = "hotel" AND ( country = "United States" OR country = "France" ) AND vacancy = "True"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  AND name LIKE "Royal Engineers Museum"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  OR name LIKE "Royal engineers museum"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  OR name LIKE "eng%e%"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  AND name LIKE "Eng%e%"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  OR name LIKE "%eng____r%"',
        'SELECT meta().id, country, name FROM `travel-sample` where type = "landmark"  AND name LIKE "%Eng____r%"',
        'SELECT meta().id FROM `travel-sample` where id = 24',
        'SELECT meta().id FROM `travel-sample` where id != 24',
        'SELECT meta().id FROM `travel-sample` where id > 2400',
        'SELECT meta().id FROM `travel-sample` where id >= 2400',
        'SELECT meta().id FROM `travel-sample` where id < 2400',
        'SELECT meta().id FROM `travel-sample` where id <= 2400',
        'SELECT meta().id FROM `travel-sample` where id BETWEEN 24 and 28',
        'SELECT meta().id FROM `travel-sample` where callsign IS null',
#         'SELECT meta().id FROM `travel-sample` where callsign IS NOT null',
        ]
    os.chdir("/Users/hemant/couchbase/couchbase/rqg/")
    fh = open("n1ql_queries_in_JSON.txt", "w")
    for query in queries:
        try:
            json_query = converty_to_json_string(get_json_query(query))
            fh.write(json_query)
            fh.write("\n")
            cmd = ["./cblite", "query", "--limit", "10", "travel-sample.cblite2"]
            print "*" * 60
            print "Executing command {} '{}'".format(" ".join(cmd), json_query)
            print "*" * 60
            cmd.append(json_query)
            p = Popen(cmd)
            p.communicate()
            print "\n"
        except Exception, err:
            log_info("Error for Query: {}\n{}\n".format(query, str(err)))
    fh.close()
