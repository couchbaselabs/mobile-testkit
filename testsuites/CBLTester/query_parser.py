import re


def parse_query(query):
    cbl_where = {}
    pattern = "SELECT (.*) FROM (.*) WHERE (.*)$"
    # operations/number of operands
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

    m = re.match(pattern, query)

    what = m.group(1)
    frm = m.group(2)
    where = m.group(3)

    if what == "*":
        what_field = "[.]"
    else:
        what_field = "[.{}]".format(what)

    cbl_where["WHAT"] = "[{}]".format(what_field)

    # Get the indexes of operands
    operand_indexes = {}
    for i, j in enumerate(where.split(" ")):
        if j in operations:
            operand_indexes[j] = i

    print operand_indexes

    # where has to be recursively parsed for operations/operands
    for op in operations:
        if op in where:
            where_operators = where.split(" ")
            operand1 = where_operators[0]
            operand2 = where_operators[2]
            operand = op

    cbl_where["WHERE"] = ["{}".format(operand), "[.{}]".format(operand1), "[.{}]".format(operand2)]
    cbl_where["FROM"] = "['DB': '{}']".format(frm)
    cbl_select = ["SELECT", cbl_where]
    return cbl_select


query = "SELECT * FROM BUCKET_NAME WHERE NUMERIC_FIELD <= NUMERIC_VALUE"
print parse_query(query)
