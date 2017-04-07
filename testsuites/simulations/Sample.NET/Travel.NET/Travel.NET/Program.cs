using System;
using System.Collections.Generic;
using Couchbase.Lite;

namespace Travel.NET
{
	class MainClass
	{
		public static void Main(string[] args)
		{
			Manager manager = Manager.SharedInstance;
			Database airlineDb = manager.GetDatabase("airline");
			Database routeDb = manager.GetDatabase("route");
			Database airportDb = manager.GetDatabase("airport");
			Database landmarkDb = manager.GetDatabase("landmark");
			Database hotelDb = manager.GetDatabase("hotel");

			var properties = new Dictionary<string, object> {
				{ "title", "Couchbase Mobile"},
				{ "sdk", "C#" }
			};

			Document document = database.CreateDocument();

			document.PutProperties(properties);

			Console.WriteLine($"Document ID :: {document.Id}");
			Console.WriteLine($"Learning {document.GetProperty("title")} with {document.GetProperty("sdk")}");

			string line = Console.ReadLine();
		}
	}
}
