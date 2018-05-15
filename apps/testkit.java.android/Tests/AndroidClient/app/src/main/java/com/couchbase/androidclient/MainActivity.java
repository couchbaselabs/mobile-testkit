package com.couchbase.androidclient;

import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;

import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.Log;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorConfiguration;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Random;
import java.util.TimerTask;

public class MainActivity extends AppCompatActivity {

  private Database database;
  private Document doc;
  private Replicator replicator;
  private int numOfDocs;
  private long scenarioRunTimeMinutes;
  private String syncGatewayURL;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    numOfDocs = getIntent().getIntExtra("numOfDocs",0);
    scenarioRunTimeMinutes = getIntent().getLongExtra("scenarioRunTimeMinutes",0);
    syncGatewayURL = getIntent().getStringExtra("syncGatewayURL");

    if (syncGatewayURL == null || numOfDocs == 0 || scenarioRunTimeMinutes == 0) {
      Log.e("app", "Did not enter the values for one of them : syncGatewayURL, numOfDocs, scenarioRunTimeMinutes ");
      finish();
      return;
    }

    setContentView(R.layout.activity_main);
    DatabaseConfiguration config = new DatabaseConfiguration(this);

    Log.i("state", "Creating database");
    database = new Database("my-database", config);
    database.addChangeListener(new DatabaseChangeListener() {
      @Override
      public void changed(DatabaseChange change) {
        Log.i("Database change listener", "%s", change);
      }
    });

    Log.i("state", "Replicating data");
    URI uri = null;
    try {
      uri = new URI(syncGatewayURL);
    } catch (URISyntaxException e) {
      e.printStackTrace();
    }
    ReplicatorConfiguration replConfig = new ReplicatorConfiguration(database, uri);
    replConfig.setContinuous(true);

    replicator = new Replicator(replConfig);
    replicator.start();

  }


  @Override
  protected void onStart() {
    int k = 0;
    long startTime, stopTime, minutesCounted = 0;
    super.onStart();

    //Create docs in batch
    database.inBatch(new TimerTask() {
      @Override
      public void run() {

        for (int i = 0; i < numOfDocs; i++) {
          doc = new Document("doc___" + i);
          doc.set("type", "user");
          doc.set("name", "user_" + i);
          database.save(doc);
        }
      }
    });
    startTime = System.currentTimeMillis();

    //update random doc
    Random rand = new Random();
    while (minutesCounted < scenarioRunTimeMinutes) {
      int n = rand.nextInt(numOfDocs);
      doc = database.getDocument("doc___" + n);
      doc.set("name", "user_" + k);
      database.save(doc);
      try {
        Thread.sleep(1000);
      } catch (InterruptedException e) {
        Log.e("app", e.getMessage());
      }
      stopTime = System.currentTimeMillis();
      minutesCounted = ((stopTime - startTime) / 60000);
      k++;
    }

    //Deleting docs
    Log.i("TEST", "before count -> %d", database.getCount());
    Log.i("app", "Deleting docs");
    for (int i = 0; i < numOfDocs - 2; i++) {
      doc = database.getDocument("doc___" + i);
      database.delete(doc);
    }
    Log.i("TEST", "after count -> %d", database.getCount());
    replicator.stop();
    //database.delete();

  }
}
