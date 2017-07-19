package com.couchbase.androidclient;

import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import com.couchbase.lite.*;
import java.util.Date;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.TimerTask;
import java.util.Random;

public class MainActivity extends AppCompatActivity {

    private Database database;
    private Document doc;
    private Replicator replicator;
    private int numOfDocs = 4;
    private int scenarioRunTimeMinutes = 1;
    private String syncGatewayURL = "blip://192.168.33.11:4984/db/";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        /*syncGatewayURL = System.getProperty("syncGatewayURL");
        numOfDocs = Integer.parseInt(System.getProperty("numOfDocs"));
        scenarioRunTimeMinutes = Integer.parseInt(System.getProperty("scenarioRunTimeMinutes"));*/

        numOfDocs = getIntent().getIntExtra("numOfDocs",4);
        scenarioRunTimeMinutes = getIntent().getIntExtra("scenarioRunTimeMinutes",1);
        syncGatewayURL = getIntent().getStringExtra("syncGatewayURL");

        setContentView(R.layout.activity_main);
        DatabaseConfiguration config = new DatabaseConfiguration(this);

        Log.i("state","Creating database");
        Log.i("app","printing  check --- : ");
        Log.i("app"," printing  1 --- : + %s 2 : %s 3 : %s", numOfDocs ,  scenarioRunTimeMinutes , syncGatewayURL);
        database = new Database("my-database", config);
        database.addChangeListener(new DatabaseChangeListener() {
            @Override
            public void changed(DatabaseChange change) {
                Log.i("Database change listener", "%s",change);
            }
        });

        Log.i("state","Replicating data");
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
        super.onStart();
        Log.i("app"," printing  1 --- : " + numOfDocs + "2 :"+ scenarioRunTimeMinutes + "3 :"+syncGatewayURL);
        //Create docs in batch
        database.inBatch(new TimerTask() {
            @Override
            public void run() {

                for (int i = 0; i < numOfDocs; i++) {
                    doc = new Document("doc___"+i);
                    doc.set("type", "user");
                    doc.set("name", String.format("user_"+ i));
                    database.save(doc);
                    Log.i("app", "doc is "+ "doc___"+i+", "+String.format("saved user document %s", doc.getString("name")));
                }
            }
        });

        int minutesCounted=0,k=0;
        long startTime,stopTime;
        startTime = System.currentTimeMillis();
        //update random doc
        Random rand = new Random();
        while(minutesCounted < scenarioRunTimeMinutes){
            int n = rand.nextInt(numOfDocs);
            doc = database.getDocument("doc___" + n);
            Log.i("app","id of  doc is"+doc.getId());
            Log.i("app","updating doc  "+"doc___" + n+String.format("user_"+k));
            doc.set("name", String.format("user_"+k));
            database.save(doc);
            Log.i("app","document name is "+doc.getString("name"));
            try {
                Thread.sleep(1000);
            }
            catch(InterruptedException e){
                Log.e("app",e.getMessage());
            }
            stopTime = System.currentTimeMillis();
            minutesCounted = new Long((stopTime - startTime)/60000).intValue();

            Log.i("app"," minutesCounter = "+minutesCounted);
            k++;
        }

       //Deleting docs

        Log.i("TEST", "before count -> %d",database.getCount());

        Log.i("app","Deleting docs");
        for(int i=0;i<numOfDocs-2;i++){
            doc = database.getDocument("doc___" + i);
            Log.i("app","id of  doc is"+doc.getId());
            Log.i("app","document name is "+doc.getString("name"));
            database.delete(doc);
            //database.purge(doc);
            Log.i("app","Deleting doc -- doc___"+i);
        }

        Log.i("TEST", "after count -> %d",database.getCount());


        //replicator.stop();
        //database.delete();

    }
}
