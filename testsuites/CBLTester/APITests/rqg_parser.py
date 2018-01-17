'''
Created on 16-Jan-2018

@author: hemant
'''
from Queue import Queue
from collections import OrderedDict
import re
import json
import pprint

from ansible.modules.core.utilities import logic

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
       "AND": 1,
       "OR": 1,
       "NOT": 1,
       "IN": 1,
       "IS": 1,
       "EXIST": 1,
       '(': 1,
       ')': 1}
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
                       "!="
                       )

logical_operator = ("BETWEEN",
                    "AND",
                    "OR",
                    "NOT",
                    "IN",
                    "IS",
                    "EXIST")
operators = logical_operator + arithmetic_operator +  ('(', ')')

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
        "IS NOT": "2",
        "LIKE": "2",
        "MATCH": "2",
        "IN": "2",
        "NOT IN": "2",
        "EXISTS": "1",
        "IS MISSING": "1",
        "IS NOT MISSING": "1",
        "IS NULL": "1",
        "IS NOT NULL": "1",
        "COLLATE": "2",
        "NOT": "1",
        "AND": "2+",
        "OR": "2+",
        "CASE": "2+",
        "WHEN": "2",
        "ELSE": "1",
        "ANY": "3",
        "EVERY": "3",
        "ANY AND EVERY": "3",
        ".": "0+",
        "$": "1",
        "?": "1+"
    }

def get_operand_to_json(token):
    if token.startswith('$'):
        return [".", "$", token[1:]]
    elif token.isdigit():
        return int(token)
    return ['.', token]

def infix_to_json(query):
    query = ['('] + query.split(' ') + [')']
    opstack = []
    result = []
    output = []
    final_list = []
    level = -1
    for token in query:
        if token not in operators:
            result.append(get_operand_to_json(token))
        elif token == '(':
            opstack.append(token)
            level += 1
        elif token == ')':
            item = opstack.pop()
            while(item != '('):
                if result:
                    result = [item] + result
                    output.append(result)
                    result = []
                else:
                    output = [item] + output
                item = opstack.pop()
            if level > 1:
                output = [output]
            level -= 1
        else:
            while prec[token] > prec[opstack[-1]]:
                    item = opstack.pop()
                    result = [item] + result
                    output.append(result)
                    result = []
            opstack.append(token)
    return final_list

def get_json_query(query="SELECT name.first, name.last FROM students WHERE ( grade = 12 AND gpa >= $GPA ) OR ( a = b AND c > d )"):
    pattern = re.compile(r"SELECT (.*?) FROM (.*?) WHERE (.*)")
    regex_out = re.search(pattern, query)
    select_token, from_token, where_token = regex_out.groups()
    print from_token
    json_txt = []
    # creating select statement
    json_txt.append("SELECT")
    tokens = select_token.split(',')
    json_txt.append(OrderedDict())
    json_txt[1]["WHAT"] = []
    for item in tokens:
        tk_list = ['.']
        if '.' in item:
            tk_list.extend(item.split('.'))
        elif item == '*':
            tk_list.append("*")
        else:
            tk_list.append(item)
        json_txt[1]["WHAT"].append(tk_list)
    # creating where statement
    json_txt[1]["WHERE"] = []
    json_txt[1]["WHERE"] = infix_to_json(where_token)
    return json_txt

if __name__ == '__main__':
    out = get_json_query()
    print json.dumps(out)