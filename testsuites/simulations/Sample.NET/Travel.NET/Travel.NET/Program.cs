using System;
using System.Threading;

using Couchbase.Lite;
using Couchbase.Lite.Auth;
using System.Diagnostics;

namespace Travel.NET
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            var syncGatewayUrl = new Uri("http://localhost:4984/db/");

            Manager manager = Manager.SharedInstance;
            Database airlineDb = manager.GetDatabase("airline");
            Database routeDb = manager.GetDatabase("route");
            Database airportDb = manager.GetDatabase("airport");
            Database landmarkDb = manager.GetDatabase("landmark");
            Database hotelDb = manager.GetDatabase("hotel");

            // airline -     187
            // hotel -       917
            // airport -    1968
            // route -     24024
            // landmark -   4495
            // ------------------
            //             31591
            var dbObjs = new[] {
                new {Database = airlineDb, UserName = "airline", Password = "pass", ExpectedDocs = 187},
                new {Database = routeDb, UserName = "route", Password = "pass", ExpectedDocs = 24024},
                new {Database = airportDb, UserName = "airport", Password = "pass", ExpectedDocs = 1968},
                new {Database = landmarkDb, UserName = "landmark", Password = "pass", ExpectedDocs = 4495},
                new {Database = hotelDb, UserName = "hotel", Password = "pass", ExpectedDocs = 917},
            };

            // Start continuous push / pull replications for each database
            foreach (var dbObj in dbObjs)
            {
                IAuthenticator replicationAuth = AuthenticatorFactory.CreateBasicAuthenticator(dbObj.UserName, dbObj.Password);

                Replication pullReplication = dbObj.Database.CreatePullReplication(syncGatewayUrl);
                pullReplication.Authenticator = replicationAuth;
                pullReplication.Continuous = true;
                pullReplication.Start();

                Replication pushReplication = dbObj.Database.CreatePushReplication(syncGatewayUrl);
                pushReplication.Authenticator = replicationAuth;
                pushReplication.Continuous = true;
                pushReplication.Start();
            }

            // Wait for replication to stop
            var sw = Stopwatch.StartNew();
            var timeout = TimeSpan.FromSeconds(60);
            var timeoutSeconds = timeout.TotalSeconds;
            // Poll until all dbs have the expected number of docs
            while (true)
            {

                var elapsedSeconds = sw.Elapsed.TotalSeconds;
                Console.WriteLine($"Elapsed: {elapsedSeconds}s, Timeout: {timeoutSeconds}s");
                if (elapsedSeconds > timeoutSeconds)
                {
                    // If timeout has been hit, and not all of the docs have been found, throw exception
                    throw new Exception("Could not find all docs before timeout");
                }

                Console.WriteLine("Scanning local databases for expected docs ...");

                var dbsWithExpectedDocs = 0;
                foreach (var dbObj in dbObjs)
                {

                    Query query = dbObj.Database.CreateAllDocumentsQuery();
                    QueryEnumerator queryRows = query.Run();
                    int docCount = queryRows.Count;
                    Console.WriteLine($"{dbObj.UserName}: {docCount}");

                    // Check that each db has the expected number of docs
                    if (docCount == dbObj.ExpectedDocs)
                    {
                        Console.WriteLine($" Found all expected docs for '{dbObj.UserName}' ({docCount})");
                        dbsWithExpectedDocs += 1;
                    }
                    else
                    {
                        Console.WriteLine($"Missing docs for '{dbObj.UserName}'. (Found: {docCount}, Expected: {dbObj.ExpectedDocs})");
                    }
                }

                if (dbsWithExpectedDocs == dbObjs.Length)
                {
                    // All docs were found! Exit the loop
                    Console.WriteLine("Found all docs");
                    break;
                }

                // Docs not found
                Console.WriteLine("Missing docs. Will retry in 5 seconds ...");
                Thread.Sleep(5000);

            }

            var line = Console.ReadLine();

            // TODO: Add / updates / push / SDK validation

        }
    }
}
