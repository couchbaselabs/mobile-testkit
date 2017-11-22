package com.couchbase.CouchbaseLiteServ.server;


import com.couchbase.lite.Document;
import com.couchbase.lite.DocumentChange;
import com.couchbase.lite.DocumentChangeListener;

import java.util.List;
import java.util.Map;

public class DocumentRequestHandler{
    /* ------------ */
    /* - Document - */
    /* ------------ */
    public Document document_create(Args args) {
        String id = args.get("id");
        Map<String, Object> dictionary = args.get("dictionary");

        if (id != null) {
            if (dictionary == null) {
                return new Document(id);
            } else {
                return new Document(id, dictionary);
            }
        } else {
            if (dictionary == null) {
                return new Document();
            } else {
                return new Document(dictionary);
            }
        }
    }

    public String document_getId(Args args) {
        Document document = args.get("document");

        return document.getId();
    }

    public String document_getString(Args args) {
        Document document = args.get("document");
        String property = args.get("property");

        return document.getString(property);
    }

    public void document_setString(Args args) {
        Document document = args.get("document");
        String property = args.get("property");
        String string = args.get("string");

        document.setString(property, string);
    }
}

class MyDocumentChangeListener implements DocumentChangeListener {
    private List<DocumentChange> changes;

    public List<DocumentChange> getChanges(){
        return changes;
    }

    @Override
    public void changed(DocumentChange change) {
        changes.add(change);
    }
}


