import subprocess


def print_sg_coverage():

    markers = [
        'oidc',
        'session',
        'basicauth',
        'facebook',
        'role',
        'access',
        'channel',
        'bulkops',
        'backfill',
        'conflicts',
        'ttl',
        'onlineoffline',
        'view',
        'attachments',
        'sgreplicate',
        'webhooks',
        'bucketshadow',
        'changes',
        'rollback',
        'failover',
        'rebalance',
        'xdcr'
    ]

    for marker in markers:
        # Get number of tests testsuites/syncgateway/functional/tests/
        # directory with marker attribute
        output_tests = subprocess.check_output(
            'pytest -m {} testsuites/syncgateway/functional/tests/ --collect-only | grep Function | wc -l'.format(marker),
            shell=True
        )
        test_number = int(output_tests.strip())

        # Get number of tests in testsuites/syncgateway/functional/topology_specific_tests/
        # directory with marker attribute
        output_topospecific_tests = subprocess.check_output(
            'pytest -m {} testsuites/syncgateway/functional/topology_specific_tests/ --collect-only | grep Function | wc -l'.format(marker),
            shell=True
        )
        topospecific_test_number = int(output_topospecific_tests.strip())

        print('Functional Area: {}, Number of Tests: {}'.format(
            marker, test_number + topospecific_test_number
        ))


if __name__ == "__main__":
    print_sg_coverage()
