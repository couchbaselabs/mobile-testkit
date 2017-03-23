import pytest
from keywords import document
from keywords import attachment

ATTACHMENT_ONE = attachment.generate_png_100_100()
ATTACHMENT_TWO = attachment.generate_png_100_100()
ATTACHMENTS = ATTACHMENT_ONE + ATTACHMENT_TWO

@pytest.mark.parametrize("doc_id, content, attachments, expiry, channels, expected_doc", [
    (None, None, None, None, None, {
        "channels": []
    }),
    ("test_id", None, None, None, None, {
        "_id": "test_id",
        "channels": []
    }),
    ("test_id", {"foo": "bar"}, None, None, None, {
        "_id": "test_id",
        "content": {"foo": "bar"},
        "channels": []
    }),
    ("test_id", None, ATTACHMENTS, None, None, {
        "_id": "test_id",
        "_attachments": {
            ATTACHMENTS[0].name: {"data": ATTACHMENTS[0].data},
            ATTACHMENTS[1].name: {"data": ATTACHMENTS[1].data}
        },
        "channels": []
    }),
    ("test_id", None, None, 10, None, {
        "_id": "test_id",
        "_exp": 10,
        "channels": []
    }),
    ("test_id", None, None, None, ["A"], {
        "_id": "test_id",
        "channels": ["A"]
    })
])
def test_document(doc_id, content, attachments, expiry, channels, expected_doc):
    doc = document.create_doc(doc_id=doc_id, content=content, attachments=attachments, expiry=expiry, channels=channels)
    assert doc == expected_doc


def test_document_attachment_not_list():
    with pytest.raises(TypeError):
        document.create_doc(None, None, ATTACHMENTS[0], None, None)


def test_document_channels_not_list():
    with pytest.raises(TypeError):
        document.create_doc(None, None, None, None, "B")
