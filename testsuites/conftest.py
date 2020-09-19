from utilities.xml_parser import parse_junit_result_xml


def pytest_addoption(parser):
    parser.addoption("--exclude-tests", action="store",
                     help="Value can be 'failed' (or) 'passed' (or) 'failed=<junit_xml_path (or) "
                     "jenkins_build_url>' (or) 'passed=<junit_xml_path or "
                     "jenkins_build_url>' (or) 'file=<filename>'")

    parser.addoption("--include-tests", action="store",
                     help="Value can be 'failed' (or) 'passed' (or) 'failed=<junit_xml_path (or) "
                     "jenkins_build_url>' (or) 'passed=<junit_xml_path or "
                     "jenkins_build_url>' (or) 'file=<filename>'")

    parser.addoption("--rerun-tests", action="store",
                     help="Value can be 'failed' (or) 'passed' (or) 'failed=<junit_xml_path (or) "
                     "jenkins_build_url>' (or) 'passed=<junit_xml_path or "
                     "jenkins_build_url>' (or) 'file=<filename>'")


def pytest_collection_modifyitems(items, config):
    selected_items = []
    deselected_items = []

    exclude_result_option = config.getoption("--exclude-tests")
    include_result_option = config.getoption("--include-tests")
    rerun_result_option = config.getoption("--rerun-tests")
    if exclude_result_option:
        result_option = exclude_result_option
    elif include_result_option:
        result_option = include_result_option
    elif rerun_result_option:
        result_option = rerun_result_option
    if result_option:
        result_option = result_option.split("=")
        result_name = result_option[0]
        if len(result_option) == 2:
            file = result_option[1]
        else:
            file = result_option[0]
        cur_tests = parse_junit_result_xml(file)
        if result_name == "pass":
            cur_tests = cur_tests[0]
        else:
            cur_tests = cur_tests[1]
        for item in items:
            test_nm = item.nodeid.split("::")
            if test_nm[1] in cur_tests:
                selected_items.append(item)
            else:
                deselected_items.append(item)

        if exclude_result_option:
            config.hook.pytest_deselected(items=selected_items)
            items[:] = deselected_items
        else:
            config.hook.pytest_deselected(items=deselected_items)
            items[:] = selected_items
