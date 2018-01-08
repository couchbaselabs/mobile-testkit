package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.content.Context;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.DocumentChangeListener;
import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.lite.Meta;
import com.couchbase.lite.MutableDocument;
import com.couchbase.lite.Query;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class DatabaseRequestHandler {
    /* ------------ */
    /* - Database - */
    /* ------------ */

    public Database create(Args args) throws CouchbaseLiteException {
        String name = args.get("name");
        Context context = MainActivity.getAppContext();
        DatabaseConfiguration databaseConfig = new DatabaseConfiguration(context);
        return new Database(name, databaseConfig);
    }

    public Database create(String name) throws CouchbaseLiteException {
        return new Database(name, null);
    }

    public int getCount(Args args) {
        Database database = args.get("database");
        return database.getCount();
    }

    public void close(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.close();
    }

    public void compact(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.compact();
    }

    public File getPath(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        return database.getPath();
    }

    public String getName(Args args) {
        Database database = args.get("database");
        return database.getName();
    }

    public Document getDocument(Args args) {
        Database database = args.get("database");
        String id = args.get("id");
        return database.getDocument(id);
    }

    public List<String> getIndexes(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        return database.getIndexes();
    }

    public Map<String, Map<String, Object>> getDocuments(Args args) {
        Database database = args.get("database");
        List<String> ids = args.get("ids");
        Map<String, Map<String, Object>> documents = new HashMap<>();
        for (String id : ids) {
            Document document = database.getDocument(id);
            if (document != null) {
                documents.put(id, document.toMap());
            }
        }
        return documents;
    }

    public void purge(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        MutableDocument document = args.get("document");
        database.purge(document);
   }

   public void saveDocuments(Args args) throws CouchbaseLiteException {
        final Database database = args.get("database");
        final Map<String, Map<String, Object>> documents = args.get("documents");

        database.inBatch(new Runnable() {
            @Override
            public void run() {
                for (Map.Entry<String, Map<String, Object>> entry : documents.entrySet()) {
                    String id = entry.getKey();
                    Map<String, Object> data = entry.getValue();
                    MutableDocument document = new MutableDocument(id, data);
                    try {
                        database.save(document);
                    } catch (CouchbaseLiteException e) {
                        e.printStackTrace();
                    }
                }
            }
        });
   }

    public void save(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        MutableDocument document = args.get("document");
        database.save(document);
   }

    public void delete(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Document document = args.get("document");

        database.delete(document);
   }

    public void deleteDB(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        database.delete();
   }

   public void deleteDbByName(Args args) throws CouchbaseLiteException {
        String dbName = args.get("dbName");
        File directory = args.get("directory");
        Database.delete(dbName, directory.getParentFile());
   }

    public boolean exists(Args args){
        String name = args.get("name");
        File directory = args.get("directory");
        return Database.exists(name, directory.getParentFile());
    }

    public boolean contains(Args args) {
       Database database = args.get("database");
       String id = args.get("id");
       return database.contains(id);
    }

    public List<String> getDocIds(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Query query = Query
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database));
        List<String> result = new ArrayList<String>();
        ResultSet results = query.execute();
        for (Result row : results){

            result.add(row.getString("_id"));
        }
        Collections.sort(result);
        return result;

    }

//    public void addChangeListener(Args args) {
//        Database database = args.get("database");
//        if (args.contain("docId")) {
//            String docId = args.get("docId");
//            MyDocumentChangeListener changeListener = new MyDocumentChangeListener();
//            database.addChangeListener(docId, changeListener);
//        } else {
//            MyDatabaseChangeListener changeListener = new MyDatabaseChangeListener();
//            database.addChangeListener(changeListener);
//        }
//    }

//    public void removeChangeListener(Args args) {
//        Database database = args.get("database");
//        if (args.contain("docId")){
//        String docId = args.get("docId");
//        DocumentChangeListener changeListener = args.get("changeListener");
//        database.removeChangeListener(docId, changeListener);
//        } else{
//            DatabaseChangeListener changeListener = args.get("changeListener");
//            database.removeChangeListener(changeListener);
//        }
//    }

    public int databaseChangeListener_changesCount(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public DatabaseChange databaseChangeListener_getChange(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        int index = args.get("index");
        return changeListener.getChanges().get(index);
    }

    public Database databaseChange_getDatabase(Args args){
        DatabaseChange change = args.get("change");
        return change.getDatabase();
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