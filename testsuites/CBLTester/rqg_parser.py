'''
Created on 16-Jan-2018

@author: hemant
'''
from collections import OrderedDict
import re
import json


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
        "IS-NOT": 1,
        "IS-NULL": 1,
        "EXIST": 1,
        '(': 2,
        ')': 2}

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
                    "EXIST")

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
        return [".", "$", token[1:]]
#         return "".join([".", "$", token[1:]])
    elif token.isdigit():
        return int(token)
    return ['.', token]
#     return "".join(['.', token])


def get_prefix_list(query):
    between_pattern = re.compile("BETWEEN ([0-9]+) and ([0-9]+)")
    between_match = re.search(between_pattern, query)

    if between_match:
        num1, num2 = between_match.groups()
        target_pattern = "BETWEEN {} and {}".format(num1, num2)
        replacement_pattern = "BETWEEN {} {}".format(num1, num2)
        query = re.sub(target_pattern, replacement_pattern, query)

    query = query.split()
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
                result.append(get_operand(token))
            else:
#                 result.append('[{}]'.format(get_operand(token)))
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
            num_of_pop = int(operations[token])
            opd = []
            if token == 'IN':
                var = opstack.pop()
                while opstack[-1] != ['.', ']']:
                    item = opstack.pop()
                    if item == ['.', '['] or item == ['.', ',']:
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
    return clear_evaluated_list(opstack.pop())

def clear_evaluated_list(eval_list, prev_op=None):
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
    return result

def get_json_query(query="SELECT name.first, name.last FROM students WHERE grade = 12 AND gpa >= $GPA"):
    #removing extra white spaces from the query string
    query = ' '.join(query.split())

    query = multiple_replace(query, trans_op)
    pattern = re.compile(r"SELECT (.*?) FROM (.*?) WHERE (.*)")
    regex_out = re.search(pattern, query)
    select_token, from_token, where_token = regex_out.groups()
    json_txt = []
    # creating select statement
    json_txt.append("SELECT")
    json_txt.append(OrderedDict())
    json_txt[1]["DISTINCT"] = False
    if 'DISTINCT' in select_token.strip():
        out = re.search("DISTINCT\((.*?)\)", select_token)
        select_token = out.groups()[0]
        json_txt[1]["DISTINCT"] = True
    tokens = select_token.split(',')
    json_txt[1]["WHAT"] = []
    for item in tokens:
        # tk_list = ['.']
        tk_list = []
        if '.' in item:
            tk_list.extend(item.split('.'))
        elif item == '*':
            tk_list.append(".")
        else:
            tk_list.append([".", item])
        json_txt[1]["WHAT"].append(tk_list)

    # creating from statement
    json_txt[1]["FROM"] = []
    for db in from_token.strip().split(' '):
        json_txt[1]["FROM"].append([".", db])
    # creating where statement
    json_txt[1]["WHERE"] = []
    json_txt[1]["WHERE"] = prefix_evaluation(get_prefix_list(where_token.strip()))
    return json_txt

def multiple_replace(text, a_dict):
    rx = re.compile('|'.join(map(re.escape, a_dict)))
    def one_xlat(match):
        return a_dict[match.group(0)]
    return rx.sub(one_xlat, text)

if __name__ == '__main__':
    # query = "SELECT a, b FROM  simple_table_2  t_1   WHERE  ( t_1.int_field1 >= 5050 ) OR ( t_1.int_field1 > 5050 )"
    #query = "SELECT * FROM  simple_table_4  t_2  WHERE ( grade = 12 AND gpa >= $GPA  AND adf != fdf ) OR ( a = b AND c > d AND b < c ) OR ( a = b AND c = a ) OR ( x > y AND y != 0 )"
#     query = "SELECT * FROM  simple_table_4  t_2  WHERE NOT ( t_4.int_field1 BETWEEN 2 and 9999 )"
#     query = "SELECT * FROM simple_table_2 t_1 WHERE  t_1.int_field1 IS NOT NULL"
#     query = "SELECT DISTINCT(t_2.int_field1) FROM  simple_table_4  t_2   WHERE  ((t_2.int_field1 IS NOT NULL) OR (t_2.int_field1 IS NULL)) OR ((t_2.decimal_field1  IN [  19 , 37 , 46 , 49 , 52  ]) OR (t_2.int_field1 IS NOT NULL))"
#     query = "SELECT DISTINCT(t_2.decimal_field1) FROM  simple_table_4  t_2   WHERE  ( t_2.decimal_field1  IN [  19 , 37 , 46 , 49 , 52  ] ) OR ( t_2.decimal_field1 >= 4770 ) "
#     out = get_json_query(query)
#     print json.dumps(out, indent=4)
    fh = open("n1ql_queries_in_JSON.txt", "w")
    for query in open("n1ql_ready_queries.txt"):
        try:
            fh.write(json.dumps(get_json_query(query), indent=4))
            fh.write("\n")
        except Exception,err:
            print "Error for Query: {}\n{}\n".format(query, str(err))
    fh.close()
