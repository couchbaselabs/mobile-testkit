package com.couchbase.CouchbaseLiteServ.server;

import android.content.Context;

import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.DocumentChangeListener;
import com.couchbase.CouchbaseLiteServ.MainActivity;

import java.io.File;
import java.util.List;

public class DatabaseRequestHandler {
    /* ------------ */
    /* - Database - */
    /* ------------ */

    public Database database_create(Args args) throws CouchbaseLiteException {
        String name = args.get("name");
        Context context = MainActivity.getAppContext();
        DatabaseConfiguration databaseConfig = new DatabaseConfiguration(context);
        return new Database(name, databaseConfig);
    }

    public Database database_create(String name) throws CouchbaseLiteException {
        return new Database(name, null);
    }

    public int database_docCount(Args args) {
        Database database = args.get("database");
        return database.getCount();
    }

    public void database_close(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.close();
    }

    public void database_compact(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.compact();
    }

    public File database_path(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        return database.getPath();
    }

    public String database_getName(Args args) {
        Database database = args.get("database");
        return database.getName();
    }

    public Document database_getDocument(Args args) {
        Database database = args.get("database");
        String id = args.get("id");
        return database.getDocument(id);
    }

    public void database_purgeDoc(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Document document = args.get("document");
        database.purge(document);
    }
    public void database_addDocuments(Args args) {
        Database database = args.get("database");
        throw new UnsupportedOperationException("Not supported yet.");
    }

    public void database_save(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Document document = args.get("document");
        database.save(document);
    }

    public void database_delete(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Document document = args.get("document");
        database.delete(document);
    }

    public void database_deleteDB(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.delete();
    }

    public boolean database_exists(Args args){
        return false;
    }
    public boolean database_contains(Args args) {
        Database database = args.get("database");
        String id = args.get("id");
        return database.contains(id);
    }

    public void database_addChangeListener(Args args) {
        Database database = args.get("database");
        if (args.contain("docId")) {
            String docId = args.get("docId");
            MyDocumentChangeListener changeListener = new MyDocumentChangeListener();
            database.addChangeListener(docId, changeListener);
        } else {
            MyDatabaseChangeListener changeListener = new MyDatabaseChangeListener();
            database.addChangeListener(changeListener);
        }
    }

    public void database_removeChangeListener(Args args) {
        Database database = args.get("database");
        if (args.contain("docId")){
            String docId = args.get("docId");
            DocumentChangeListener changeListener = args.get("changeListener");
            database.removeChangeListener(docId, changeListener);
        } else{
            DatabaseChangeListener changeListener = args.get("changeListener");
            database.removeChangeListener(changeListener);
        }
    }

    public int databaseChangeListener_changesCount(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public DatabaseChange databaseChangeListener_getChange(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        int index = args.get("index");
        return changeListener.getChanges().get(index);
    }

    public List<String> databaseChange_getDocumentId(Args args) {
        DatabaseChange change = args.get("change");
        return change.getDocumentIDs();
    }

    public void changeEncryptionkey(Args args){
        Database database = args.get("database");
        String key = args.get("key");
    }

}

class MyDatabaseChangeListener implements DatabaseChangeListener{
    private List<DatabaseChange> changes;

    public List<DatabaseChange> getChanges(){
        return changes;
    }

    @Override
    public void changed(DatabaseChange change) {
        changes.add(change);
    }
}
