using System;
using Couchbase.Lite;
using Couchbase.Lite.Auth;

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

            var dbObjs = new[] {
                new {Database = airlineDb, UserName = "airline", Password = "pass"},
                new {Database = routeDb, UserName = "route", Password = "pass"},
                new {Database = airportDb, UserName = "airport", Password = "pass"},
                new {Database = landmarkDb, UserName = "landmark", Password = "pass"},
                new {Database = hotelDb, UserName = "hotel", Password = "pass"},
            };

            // Start pull replications for each database
            foreach (var dbObj in dbObjs)
            {
                Replication replication = dbObj.Database.CreatePullReplication(syncGatewayUrl);
                IAuthenticator replicationAuth = AuthenticatorFactory.CreateBasicAuthenticator(dbObj.UserName, dbObj.Password);
                replication.Authenticator = replicationAuth;
                replication.Continuous = true;
                replication.Start();
            }

            // Wait for replication to stop
            string line = Console.ReadLine();

            // See how many docs are in each database
            int totalDocs = 0;
            foreach (var dbObj in dbObjs)
            {
                Query query = dbObj.Database.CreateAllDocumentsQuery();
                QueryEnumerator queryRows = query.Run();
                int docCount = queryRows.Count;
                Console.WriteLine($"{dbObj.UserName}: {docCount}");
                totalDocs += docCount;
            }

            if (totalDocs != 31591)
            {
                throw new Exception("Unexpected number of docs!");
            }

            line = Console.ReadLine();
        }
    }
}
