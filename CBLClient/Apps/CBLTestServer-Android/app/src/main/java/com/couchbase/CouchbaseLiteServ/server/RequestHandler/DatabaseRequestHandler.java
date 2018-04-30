package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.content.Context;
import android.util.Log;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.ConcurrencyControl;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.lite.Expression;
import com.couchbase.lite.ListenerToken;
import com.couchbase.lite.Meta;
import com.couchbase.lite.MutableDocument;
import com.couchbase.lite.Query;
import com.couchbase.lite.QueryBuilder;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;
import com.couchbase.lite.EncryptionKey;

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
        DatabaseConfiguration config = args.get("config");
        if (config == null) {
            Context context = MainActivity.getAppContext();
            config = new DatabaseConfiguration(context);
        }
        return new Database(name, config);
    }

    public ListenerToken addChangeListener(Args args) {
        Database database = args.get("database");
        MyDatabaseChangeListener changeListener = new MyDatabaseChangeListener();
        return database.addChangeListener(changeListener);
    }

    public void removeChangeListener(Args args) {
        Database database = args.get("database");
        ListenerToken changeListener = args.get("changeListener");
        database.removeChangeListener(changeListener);
    }

    public Database create(String name) throws CouchbaseLiteException {
        return new Database(name, null);
    }

    public long getCount(Args args) {
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

    public String getPath(Args args) throws CouchbaseLiteException {
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

    public void updateDocument(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        MutableDocument document = args.get("document");
        String id = document.getId();
        Map<String, Object> data = (Map<String, Object>) document.getValue(id);
        MutableDocument updateDoc = database.getDocument(id).toMutable();
        updateDoc.setData(data);
        database.save(updateDoc);
    }

    public void updateDocuments(Args args) throws CouchbaseLiteException {
        final Database database = args.get("database");
        final Map<String, Map<String, Object>> documents = args.get("documents");
        database.inBatch(new Runnable() {
            @Override
            public void run() {
                for (Map.Entry<String, Map<String, Object>> entry : documents.entrySet()) {
                    String id = entry.getKey();
                    Map<String, Object> data = entry.getValue();
                    MutableDocument updatedDoc = database.getDocument(id).toMutable();
                    updatedDoc.setData(data);
                    try {
                        database.save(updatedDoc);
                    } catch (CouchbaseLiteException e) {
                        e.printStackTrace();
                    }
                }
            }
        });
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

    public void saveWithConcurrency(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        MutableDocument document = args.get("document");
        String concurrencyControlType = args.get("concurrencyControlType");
        ConcurrencyControl concurrencyType;
        if (concurrencyControlType == null)
        {
            concurrencyType = ConcurrencyControl.LAST_WRITE_WINS;
        }
        if(concurrencyControlType.equals("failOnConflict"))
            concurrencyType = ConcurrencyControl.FAIL_ON_CONFLICT;
        else
            concurrencyType = ConcurrencyControl.LAST_WRITE_WINS;
        database.save(document, concurrencyType);
    }

    public void delete(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Document document = args.get("document");
        database.delete(document);
   }

    public void deleteWithConcurrency(Args args) throws CouchbaseLiteException {
      Database database = args.get("database");
      Document document = args.get("document");
      String concurrencyControlType = args.get("concurrencyControlType");
      ConcurrencyControl concurrencyType;
      if (concurrencyControlType == null)
      {
        concurrencyType = ConcurrencyControl.LAST_WRITE_WINS;
      }
      if(concurrencyControlType.equals("failOnConflict"))
        concurrencyType = ConcurrencyControl.FAIL_ON_CONFLICT;
      else
        concurrencyType = ConcurrencyControl.LAST_WRITE_WINS;
      database.delete(document, concurrencyType);
    }

    public void deleteDB(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        try {
            database.delete();
        }catch (CouchbaseLiteException ex){
            Log.e("deleteDB", "deleteDB() ERROR !!!!!!");
            ex.printStackTrace();
        }
        System.out.println("database delete ");
   }

    public void changeEncryptionKey(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String password = args.get("password");
        EncryptionKey encryptionKey;
        if(password.equals("nil"))
          encryptionKey = null;
        else
          encryptionKey = new EncryptionKey(password);
        database.changeEncryptionKey(encryptionKey);
    }

   public void deleteDbByName(Args args) throws CouchbaseLiteException {
        String dbName = args.get("dbName");
        File directory = args.get("directory");
        Database.delete(dbName, directory.getParentFile());
   }

    public boolean exists(Args args){
        String name = args.get("name");
        File directory = new File(args.get("directory").toString());
        return Database.exists(name, directory);
    }

    public void deleteBulkDocs(Args args) throws CouchbaseLiteException {
        final Database db = args.get("database");
        final List<String> docIds = args.get("doc_ids");
        db.inBatch(new Runnable() {
            @Override
            public void run() {
                for(String id : docIds) {
                    Document document = db.getDocument(id);
                    try {
                        db.delete(document);
                    } catch (CouchbaseLiteException e) {
                        e.printStackTrace();
                    }
                }
                }
        });

    }
/*    method dropped in DB022
    public boolean contains(Args args) {
       Database database = args.get("database");
       String id = args.get("id");
       return database.contains(id);
    }*/

    public List<String> getDocIds(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        int limit = args.get("limit");
        int offset = args.get("offset");
        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .limit(Expression.intValue(limit), Expression.intValue(offset));
        List<String> result = new ArrayList<String>();
        ResultSet results = query.execute();
        for (Result row : results){

            result.add(row.getString("id"));
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

    public int databaseChangeListenerChangesCount(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public DatabaseChange databaseChangeListenerGetChange(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        int index = args.get("index");
        return changeListener.getChanges().get(index);
    }

    public Database changeGetDatabase(Args args){
        DatabaseChange change = args.get("change");
        return change.getDatabase();
    }

    public List<String> changeGetDocumentId(Args args) {
        DatabaseChange change = args.get("change");
        return change.getDocumentIDs();
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