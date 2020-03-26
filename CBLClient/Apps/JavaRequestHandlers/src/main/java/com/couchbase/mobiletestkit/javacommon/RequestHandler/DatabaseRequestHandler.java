package com.couchbase.mobiletestkit.javacommon.RequestHandler;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javacommon.RequestHandlerDispatcher;
import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.mobiletestkit.javacommon.util.ZipUtils;
import com.couchbase.lite.Blob;
import com.couchbase.lite.ConcurrencyControl;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.EncryptionKey;
import com.couchbase.lite.Expression;
import com.couchbase.lite.ListenerToken;
import com.couchbase.lite.Meta;
import com.couchbase.lite.MutableDocument;
import com.couchbase.lite.Query;
import com.couchbase.lite.QueryBuilder;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;

public class DatabaseRequestHandler {
    private static final String TAG = "DATABASE";
    /* ------------ */
    /* - Database - */
    /* ------------ */

    public Database create(Args args) throws CouchbaseLiteException {
        String name = args.get("name");
        Log.i(TAG, "database_create name=" + name);
        DatabaseConfiguration config = args.get("config");
        if (config == null) {
            config = new DatabaseConfiguration();
        }
        String dbDir = config.getDirectory();
        /*
        dbDir is obtained from cblite database configuration
        1. dbDir shouldn't be null unless a bad situation happen.
        2. while TestServer app running as a daemon service,
           cblite core sets dbDir "/", which will cause due permission issues.
           set dbDir to wherever the application context points to
        */
        if (dbDir == null || dbDir.equals("/")) {
            config.setDirectory(RequestHandlerDispatcher.context.getFilesDir().getAbsolutePath());
        }
        Log.i(TAG, "database_create directory=" + config.getDirectory());
        return new Database(name, config);
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

    public String getPath(Args args) {
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
                Map<String, Object> doc = document.toMap();
                // looping through the document, replace the Blob with its properties
                for (Map.Entry<String, Object> entry : doc.entrySet()) {
                    if (entry.getValue() != null && entry.getValue() instanceof Map<?, ?>) {
                        if (((Map) entry.getValue()).size() == 0) {
                            continue;
                        }
                        boolean isBlob = false;
                        Map<?, ?> value = (Map<?, ?>) entry.getValue();
                        Map<String, Object> newVal = new HashMap<>();
                        for (Map.Entry<?, ?> item : value.entrySet()) {
                            if (item.getValue() != null && item.getValue() instanceof Blob) {
                                isBlob = true;
                                Blob b = (Blob) item.getValue();
                                newVal.put(item.getKey().toString(), b.getProperties());
                            }
                        }
                        if (isBlob) { doc.put(entry.getKey(), newVal); }
                    }
                }
                documents.put(id, doc);
            }
        }
        return documents;
    }

    public void updateDocument(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String id = args.get("id");
        Map<String, Object> data = args.get("data");
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
                    }
                    catch (CouchbaseLiteException e) {
                        Log.e(TAG, "DB Save failed", e);
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
                    }
                    catch (CouchbaseLiteException e) {
                        Log.e(TAG, "DB Save failed", e);
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
        ConcurrencyControl concurrencyType
            = ((concurrencyControlType != null) && (concurrencyControlType.equals("failOnConflict")))
            ? ConcurrencyControl.FAIL_ON_CONFLICT
            : ConcurrencyControl.LAST_WRITE_WINS;
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
        ConcurrencyControl concurrencyType
            = ((concurrencyControlType != null) && (concurrencyControlType.equals("failOnConflict")))
            ? ConcurrencyControl.FAIL_ON_CONFLICT
            : ConcurrencyControl.LAST_WRITE_WINS;

        database.delete(document, concurrencyType);
    }

    public void deleteDB(Args args) {
        Database database = args.get("database");
        try {
            database.delete();
            Log.i(TAG, "database deleted");
        }
        catch (CouchbaseLiteException ex) {
            Log.e(TAG, "deleteDB() ERROR !!!!!!", ex);
        }
    }

    public void changeEncryptionKey(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String password = args.get("password");
        EncryptionKey encryptionKey;
        if (password.equals("nil")) { encryptionKey = null; }
        else { encryptionKey = new EncryptionKey(password); }
        database.changeEncryptionKey(encryptionKey);
    }

    public void deleteDbByName(Args args) throws CouchbaseLiteException {
        String dbName = args.get("dbName");
        File directory = args.get("directory");
        Database.delete(dbName, directory.getParentFile());
    }

    public boolean exists(Args args) {
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
                for (String id : docIds) {
                    Document document = db.getDocument(id);
                    try {
                        db.delete(document);
                    }
                    catch (CouchbaseLiteException e) {
                        Log.e(TAG, "DB Delete failed", e);
                    }
                }
            }
        });

    }

    public List<String> getDocIds(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        int limit = args.get("limit");
        int offset = args.get("offset");
        Query query = QueryBuilder
            .select(SelectResult.expression(Meta.id))
            .from(DataSource.database(database))
            .limit(Expression.intValue(limit), Expression.intValue(offset));
        List<String> result = new ArrayList<>();
        ResultSet results = query.execute();
        for (Result row : results) {

            result.add(row.getString("id"));
        }
        return result;

    }

    public ListenerToken addChangeListener(Args args) {
        Database database = args.get("database");
        ListenerToken token;
        if (args.contain("docId")) {
            String docId = args.get("docId");
            MyDocumentChangeListener changeListener = new MyDocumentChangeListener();
            token = database.addDocumentChangeListener(docId, changeListener);
        }
        else {
            MyDatabaseChangeListener changeListener = new MyDatabaseChangeListener();
            token = database.addChangeListener(changeListener);
        }
        return token;
    }

    public void removeChangeListener(Args args) {
        Database database = args.get("database");
        ListenerToken token = args.get("changeListenerToken");
        database.removeChangeListener(token);
    }

    public int databaseChangeListenerChangesCount(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public DatabaseChange databaseChangeListenerGetChange(Args args) {
        MyDatabaseChangeListener changeListener = args.get("changeListener");
        int index = args.get("index");
        return changeListener.getChanges().get(index);
    }

    public Database changeGetDatabase(Args args) {
        DatabaseChange change = args.get("change");
        return change.getDatabase();
    }

    public List<String> changeGetDocumentId(Args args) {
        DatabaseChange change = args.get("change");
        return change.getDocumentIDs();
    }

    public void copy(Args args) throws CouchbaseLiteException {
        String dbName = args.get("dbName");
        String dbPath = args.get("dbPath");

        DatabaseConfiguration dbConfig = args.get("dbConfig");
        File oldDbPath = new File(dbPath);
        Database.copy(oldDbPath, dbName, dbConfig);
    }

    public String getPreBuiltDb(Args args) throws IOException {
        String dbPath = args.get("dbPath");
        String dbFileName = new File(dbPath).getName();
        dbFileName = dbFileName.substring(0, dbFileName.lastIndexOf("."));
        Context context = RequestHandlerDispatcher.context;

        ZipUtils zipper = new ZipUtils();
        zipper.unzip(context.getAsset(dbPath), context.getFilesDir());
        return context.getFilesDir().getAbsolutePath() + "/" + dbFileName;
    }

}

class MyDatabaseChangeListener implements DatabaseChangeListener {
    private List<DatabaseChange> changes;

    public List<DatabaseChange> getChanges() { return changes; }

    @Override
    public void changed(DatabaseChange change) { changes.add(change); }
}