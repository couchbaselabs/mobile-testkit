using System;
using System.Threading;

using Couchbase.Lite;
using Couchbase.Lite.Auth;
using System.Diagnostics;

namespace Travel.NET
{
    class TestDatabase
    {
        public Database Database { get; }
        public string UserName { get; }
        public string Password { get; }
        public int ExpectedNumDocs { get; }

        public TestDatabase(Database db, string userName, string password, int expectedNumDocs)
        {
            Database = db;
            UserName = userName;
            Password = password;
            ExpectedNumDocs = expectedNumDocs;
        }
    }

    class MainClass
    {
        private static void WaitForImport(TestDatabase[] testDbs, TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            double timeoutSeconds = timeout.TotalSeconds;
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
                foreach (var testDb in testDbs)
                {

                    Query query = testDb.Database.CreateAllDocumentsQuery();
                    QueryEnumerator queryRows = query.Run();
                    int docCount = queryRows.Count;
                    // Check that each db has the expected number of docs
                    if (docCount == testDb.ExpectedNumDocs)
                    {
                        Console.WriteLine($" Found all expected docs for '{testDb.UserName}' ({docCount})");
                        dbsWithExpectedDocs += 1;
                    }
                    else
                    {
                        Console.WriteLine($"Missing docs for '{testDb.UserName}'. (Found: {docCount}, Expected: {testDb.ExpectedNumDocs})");
                    }
                }

                if (dbsWithExpectedDocs == testDbs.Length)
                {
                    // All docs were found! Exit the loop
                    Console.WriteLine("Found all docs");
                    break;
                }

                // Docs not found
                Console.WriteLine("Missing docs. Will retry in 5 seconds ...\n");
                Thread.Sleep(5000);
            }
        }

        private static void TouchAllDocs(TestDatabase[] testDbs)
        {
            foreach (var testDb in testDbs)
            {
                Query query = testDb.Database.CreateAllDocumentsQuery();
                QueryEnumerator queryRows = query.Run();
                int docCount = queryRows.Count;

                foreach (QueryRow row in queryRows)
                {
                    Document doc = testDb.Database.GetExistingDocument(row.DocumentId);
                    Console.WriteLine($"Touching: {row.DocumentId}");
                    doc.Update((UnsavedRevision newRevision) =>
                    {
                        var properties = newRevision.Properties;
                        properties["lite_touched"] = true;
                        return true;
                    });
                }
            }
        }

        private static void WaitForSDKUpdates(TestDatabase[] testDbs, TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            double timeoutSeconds = timeout.TotalSeconds;
            while (true)
            {
                var elapsedSeconds = sw.Elapsed.TotalSeconds;
                Console.WriteLine($"Elapsed: {elapsedSeconds}s, Timeout: {timeoutSeconds}s");
                if (elapsedSeconds > timeoutSeconds)
                {
                    // If timeout has been hit, and not all of the docs have been found, throw exception
                    throw new Exception("Could not find all updates before timeout");
                }


                int dbsWithExpectedDocs = 0;
                Console.WriteLine("Scanning local databases for expected updates ...");
                foreach (var testdb in testDbs)
                {
                    int sdkUpdatedCount = 0;
                    Query query = testdb.Database.CreateAllDocumentsQuery();
                    QueryEnumerator queryRows = query.Run();
                    foreach (var row in queryRows)
                    {
                        var docProps = row.Document.Properties;
                        if (docProps.ContainsKey("sdk_touched"))
                        {
                            sdkUpdatedCount += 1;
                        }
                    }

                    // Check to see if all of the sdk updates replicated
                    if (sdkUpdatedCount == testdb.ExpectedNumDocs)
                    {
                        Console.WriteLine($" Found all expected SDK updates for '{testdb.UserName}' ({sdkUpdatedCount})");
                        dbsWithExpectedDocs += 1;
                    }
                    else
                    {
                        Console.WriteLine($"Missing updates for '{testdb.UserName}'. (Found: {sdkUpdatedCount}, Expected: {testdb.ExpectedNumDocs})");
                    }
                }

                if (dbsWithExpectedDocs == testDbs.Length)
                {
                    // All docs were found! Exit the loop
                    Console.WriteLine("Found all sdk updates!\n");
                    break;
                }

                Console.WriteLine("Could not find all expected updates. Retrying ...\n");
                Thread.Sleep(5000);
            }
        }

        public static void Main(string[] args)
        {
            var syncGatewayUrl = new Uri("http://localhost:4984/db/");

            Manager manager = Manager.SharedInstance;
            Database airlineDb = manager.GetDatabase("airline");
            Database routeDb = manager.GetDatabase("route");
            Database airportDb = manager.GetDatabase("airport");
            Database landmarkDb = manager.GetDatabase("landmark");
            Database hotelDb = manager.GetDatabase("hotel");

            // Total docs: 31591
            var testDbs = new TestDatabase[] {
                new TestDatabase(airlineDb, "airline", "pass", 187),
                new TestDatabase(routeDb, "route", "pass", 24024),
                new TestDatabase(airportDb, "airport", "pass", 1968),
                new TestDatabase(landmarkDb, "landmark", "pass", 4495),
                new TestDatabase(hotelDb, "hotel", "pass", 917),
            };

            // Start continuous push / pull replications for each database
            foreach (var testDb in testDbs)
            {
                IAuthenticator replicationAuth = AuthenticatorFactory.CreateBasicAuthenticator(testDb.UserName, testDb.Password);

                Replication pullReplication = testDb.Database.CreatePullReplication(syncGatewayUrl);
                pullReplication.Authenticator = replicationAuth;
                pullReplication.Continuous = true;
                pullReplication.Start();

                Replication pushReplication = testDb.Database.CreatePushReplication(syncGatewayUrl);
                pushReplication.Authenticator = replicationAuth;
                pushReplication.Continuous = true;
                pushReplication.Start();
            }

            // Wait for replication to stop
            var timeout = TimeSpan.FromMinutes(20);

            // Poll until all dbs have the expected number of docs
            WaitForImport(testDbs, timeout);

            // Update each doc via Lite
            TouchAllDocs(testDbs);

            // Run python script to update all the docs via the SDK
            Console.WriteLine("\nWaiting for SDK to perform updates ...");
            var line = Console.ReadLine();

            // Wait for replication to stop
            WaitForSDKUpdates(testDbs, timeout);
        }
    }
}


