
def verify_change_with_filter(doc_name_pattern):
    pass


def verify_changes(users, expected_num_docs, expected_num_revisions, expected_docs):

    if type(users) is not list:
        users = list(users)

    if type(expected_docs) is not dict:
        raise Exception("Make sure 'expected_docs' is a dictionary")

    for user in users:

        changes = user.get_changes(include_docs=True)
        results = changes["results"]

        changes_results = list()
        for result in results:
            changes_result = dict()
            if not result["id"].startswith("_user"):
                changes_result["id"] = result["doc"]["_id"]
                changes_result["rev"] = result["doc"]["_rev"]
                changes_result["updates"] = result["doc"]["updates"]
                changes_results.append(changes_result)

        # Check expected_num_docs matches number of changes results
        assert expected_num_docs == len(changes_results)

        # Check number of expected num docs matched number of expected doc ids
        assert expected_num_docs == len(expected_docs)

        # Get ids from expected docs
        expected_doc_ids = expected_docs.keys()

        # Assert there are no duplicates in expected doc ids
        assert len(expected_doc_ids) == len(set(expected_doc_ids))

        # Get ids from all changes results
        changes_doc_ids = list()
        for result in changes_results:
            changes_doc_ids.append(result["id"])

        # Assert there are no duplicates in changes doc ids
        assert len(changes_doc_ids) == len(set(changes_doc_ids))

        # Assert the expected doc ids and changes doc ids are the same
        assert set(expected_doc_ids) == set(changes_doc_ids)

        for result in changes_results:
            # Compare revision number for id
            assert expected_docs[result["id"]] == result["rev"]

            # Assert that the revision id prefix matches the number of expected revisions
            rev_id_prefix = result["rev"].split("-")[0]
            assert expected_num_revisions == int(rev_id_prefix)

            # Check number of expected updates matched the updates on the _changes doc
            assert expected_num_revisions == result["updates"]

        print(" -> |{0}| expected (num_docs: {1} num_updates: {2}) _changes (num_docs: {3} updates: {4})".format(
            user.name,
            expected_num_docs,
            expected_num_revisions,
            len(changes_doc_ids),
            changes_results[0]["updates"]
        ))
