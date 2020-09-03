import json
import sys

if __name__ == "__main__":
    print(f"File Name: {sys.argv[1]}")
    file_name = sys.argv[1]
    cnt = ""
    data = ""
    with open(file_name, 'r') as fp:
        data = json.load(fp)
# the result is a Python dictionary:
tests = data["report"]["tests"]
test_string = ""
for test in tests:
    test_string += test["name"].split("::")[1].strip() + " and "

print(test_string)
