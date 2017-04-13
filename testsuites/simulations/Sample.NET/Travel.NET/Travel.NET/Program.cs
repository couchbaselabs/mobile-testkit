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

            Replication airlinePuller = airlineDb.CreatePullReplication(syncGatewayUrl);
            var airlineAuth = AuthenticatorFactory.CreateBasicAuthenticator("airline", "pass");
            airlinePuller.Authenticator = airlineAuth;
            airlinePuller.Continuous = true;
            airlinePuller.Start();

            Replication routePuller = routeDb.CreatePullReplication(syncGatewayUrl);
            var routeAuth = AuthenticatorFactory.CreateBasicAuthenticator("route", "pass");
            routePuller.Authenticator = routeAuth;
            routePuller.Continuous = true;
            routePuller.Start();

            Replication airportPuller = airportDb.CreatePullReplication(syncGatewayUrl);
            var airportAuth = AuthenticatorFactory.CreateBasicAuthenticator("airport", "pass");
            airportPuller.Authenticator = airportAuth;
            airportPuller.Continuous = true;
            airportPuller.Start();

            Replication landmarkPuller = landmarkDb.CreatePullReplication(syncGatewayUrl);
            var landmarkAuth = AuthenticatorFactory.CreateBasicAuthenticator("landmark", "pass");
            landmarkPuller.Authenticator = landmarkAuth;
            landmarkPuller.Continuous = true;
            landmarkPuller.Start();

            Replication hotelPuller = hotelDb.CreatePullReplication(syncGatewayUrl);
            var hotelAuth = AuthenticatorFactory.CreateBasicAuthenticator("hotel", "pass");
            hotelPuller.Authenticator = hotelAuth;
            hotelPuller.Continuous = true;
            hotelPuller.Start();

            // TODO: Verify number of docs for each db

            string line = Console.ReadLine();
        }
    }
}
