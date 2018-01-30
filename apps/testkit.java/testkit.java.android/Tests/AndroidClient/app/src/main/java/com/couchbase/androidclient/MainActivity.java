package com.couchbase.androidclient;

import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;

import com.couchbase.lite.BasicAuthenticator;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.MutableDocument;
import com.couchbase.lite.URLEndpoint;
import com.couchbase.lite.internal.support.Log;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorConfiguration;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Random;
import java.util.TimerTask;

public class MainActivity extends AppCompatActivity {

    private Database database;
    private Replicator replicator;
    private Replicator pullReplicator;
    private int numOfDocs;
    private long scenarioRunTimeMinutes;
    private String syncGatewayURL;
    final static String TAG = "System Testing App";
    final static int BATCH_SIZE = 1000;
    final static int ITERATION = 1000;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        /*numOfDocs = getIntent().getIntExtra("numOfDocs",0);
        scenarioRunTimeMinutes = getIntent().getLongExtra("scenarioRunTimeMinutes",0);
        syncGatewayURL = getIntent().getStringExtra("syncGatewayURL");*/
        numOfDocs = 1000000;
        scenarioRunTimeMinutes = 60;
        syncGatewayURL = "ws://192.168.0.177:4985/db/";
        if (syncGatewayURL == null || numOfDocs == 0 || scenarioRunTimeMinutes == 0) {
            Log.e("app", "Did not enter the values for one of them : syncGatewayURL, numOfDocs, scenarioRunTimeMinutes ");
            finish();
            return;
        }

        setContentView(R.layout.activity_main);
        DatabaseConfiguration config = new DatabaseConfiguration.Builder(this).build();

        Log.i("state", "Creating database");
        try {
            database = new Database("my-database", config);
        } catch (CouchbaseLiteException e) {
            e.printStackTrace();
        }
        // Commenting out as Hideki asked for it.
        /*database.addChangeListener(new DatabaseChangeListener() {
            @Override
            public void changed(DatabaseChange change) {
                Log.i("Database change listener", "%s", change);
            }
        });*/

        Log.i("state", "Replicating data");
        URI uri = null;
        try {
            uri = new URI(syncGatewayURL);
        } catch (URISyntaxException e) {
            e.printStackTrace();
        }
        ReplicatorConfiguration.Builder replBuilder = new ReplicatorConfiguration.Builder(database, new URLEndpoint(uri));
        replBuilder.setContinuous(true);
        BasicAuthenticator authenticator = new BasicAuthenticator("travel-sample", "password");
        replBuilder.setAuthenticator(authenticator);
        replBuilder.setReplicatorType(ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL);
        ReplicatorConfiguration replConfig = replBuilder.build();

        replicator = new Replicator(replConfig);
        replicator.start();
    }


    @Override
    protected void onStart() {
        int k = 0;
        long startTime, stopTime, minutesCounted = 0;
        super.onStart();

        //Create docs in batch
        /*try {
            for (int j = 0; j <  numOfDocs / 1000; j++ ) {
                final int finalJ = j;
                database.inBatch(new TimerTask() {
                    @Override
                    public void run() {
                        for (int i = 0; i < numOfDocs / 1000; i++) {
                            int k = finalJ * 1000 + i;
                            MutableDocument doc = new MutableDocument("doc___" + finalJ * 1000 + i);
                            doc.setString("type", "user");
                            doc.setString("name", "user_" + i);
                            try {
                                database.save(doc);
                            } catch (CouchbaseLiteException e) {
                                e.printStackTrace();
                            }
                        }
                    }
                });
            }
        } catch (CouchbaseLiteException e) {
            e.printStackTrace();
        }*/
        Log.i(TAG, "### insert documents start");
        for(int i = 0; i < ITERATION; i++){
            Log.i(TAG, "batch save start: i = " + i);
            final int I = i;
            try {
                database.inBatch(new Runnable() {
                    @Override
                    public void run() {
                        for (int j = 0; j < BATCH_SIZE; j++) {
                            int index = I * BATCH_SIZE + j;
                            MutableDocument doc = new MutableDocument("doc___" + index);
                            doc.setString("type", "user");
                            doc.setString("name", "user_" + index);
                            try {
                                database.save(doc);
                            } catch (CouchbaseLiteException e) {
                                Log.e(TAG, "Database save  operation failed, index -> " + index, e);
                                throw new RuntimeException("Database save  operation failed, index -> " + index, e);
                            }
                        }
                    }
                });
                Log.i(TAG, "batch save end: i = " + i);
                Log.i(TAG, "database size = " + database.getCount());
            } catch (CouchbaseLiteException e) {
                Log.e(TAG, "Database batch operation failed", e);
                throw new RuntimeException("Database batch operation failed", e);
            }
        }

        startTime = System.currentTimeMillis();

        //update random doc
        Random rand = new Random();
        while (minutesCounted < scenarioRunTimeMinutes) {
            int n = rand.nextInt(numOfDocs);
            MutableDocument doc = database.getDocument("doc___" + n).toMutable();
            doc = doc.setString("name", "New_user_" + k);
            try {
                database.save(doc);
            } catch (CouchbaseLiteException e) {
                e.printStackTrace();
            }
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                Log.e("app", e.getMessage());
            }
            stopTime = System.currentTimeMillis();
            minutesCounted = ((stopTime - startTime) / 60000);
            k++;
        }
        System.out.println("no. of doc updated:" + k);


        //Deleting docs
        Log.i("TEST", "before count -> %d", database.getCount());
        Log.i("app", "Deleting docs");
        for (int i = 0; i < numOfDocs - 2; i++) {
            Document doc = database.getDocument("doc___" + i);
            try {
                database.delete(doc);
            } catch (CouchbaseLiteException e) {
                e.printStackTrace();
            }
        }
        Log.i("TEST", "after count -> %d", database.getCount());
        replicator.stop();
        try {
            database.delete();
        } catch (CouchbaseLiteException e) {
            e.printStackTrace();
        }

    }
}
