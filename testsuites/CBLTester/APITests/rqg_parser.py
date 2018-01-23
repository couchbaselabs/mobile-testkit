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
        "BETWEEN": "4",
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
        "AND": "2",
        "OR": "2",
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

def get_operand(token):
    if token.startswith('$'):
        return [".", "$", token[1:]]
    elif token.isdigit():
        return int(token)
    return ['.', token]

def get_prefix_list(query):
    query = query.split()
    query.reverse()
    for index, item in enumerate(query):
        if item == '(':
            query[index] = ')'
        elif item == ')':
            query[index] = '('
    query = ['(' ] + query + [')']

    opstack = []
    result = []
    
    for token in query:
        if token not in operators:
            result.append(get_operand(token))
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
            num_of_pop = operations[token]
            opd = []
            for _ in range(int(num_of_pop)):
                item = opstack.pop()
                if token == "BETWEEN" and item == ['.', 'and']:
                        continue
                opd.append(item)
            eq = [token] + opd
            opstack.append(eq)
    return clear_evaluated_list(opstack.pop())

def clear_evaluated_list(eval_list, prev_op=None):
    result = []
    for item in eval_list:
        if item in logical_operator:
            result.append(item)
            prev_op = item
        else:
            if isinstance(item, list) and item[0] == prev_op:
                    result.extend(clear_evaluated_list(item[1:], prev_op))
            else:
                result.append(item)
    return result

def get_json_query(query="SELECT name.first, name.last FROM students WHERE ( grade = 12 AND gpa >= $GPA ) OR ( a = b AND c > d )"):
    pattern = re.compile(r"SELECT (.*?) FROM (.*?) WHERE (.*)")
    regex_out = re.search(pattern, query)
    select_token, from_token, where_token = regex_out.groups()
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
    json_txt[1]["WHERE"] = prefix_evaluation(get_prefix_list(where_token))
    return json_txt

if __name__ == '__main__':
    query = "SELECT a, b FROM  simple_table_2  t_1   WHERE  ( t_1.int_field1 >= 5050 ) OR ( t_1.int_field1 > 5050 )"
    query = "SELECT * FROM  simple_table_4  t_2  WHERE ( grade = 12 AND gpa >= $GPA  AND adf != fdf ) OR ( a = b AND c > d ) OR ( a = b AND c = a ) OR ( x > y AND y != 0 )"
    #query = "SELECT * FROM  simple_table_4  t_2  WHERE NOT ( t_4.int_field1 BETWEEN 2 and 9999 )"
    out = get_json_query(query)
    print json.dumps(out, indent = 4)
