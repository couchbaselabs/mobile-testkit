using System;
using System.Threading.Tasks;

using Couchbase.Lite;
using Couchbase.Lite.Support;

using Xunit;
using Couchbase.Lite.Sync;
using System.Diagnostics;

namespace Testkit.Net.Tests
{

    public class Longevity
    {
        private readonly Database _db;
        private readonly Replicator _replicator;
        private readonly double _scenarioRuntimeMinutes;

        public Longevity(string syncGatewayUrl, double scenarioRuntimeMinutes)
        {
            _scenarioRuntimeMinutes = scenarioRuntimeMinutes;

            NetDestkop.Activate();

            _db = new Database("in-for-the-long-haul");

            Console.WriteLine($"Running Scenario for: {_scenarioRuntimeMinutes}");
            Console.WriteLine($"Replicating with Sync Gateway: {syncGatewayUrl}");
            var replicatorConfig = new ReplicatorConfiguration
            {
                Database = _db,
                Target = new ReplicatorTarget(new Uri($"{syncGatewayUrl}")),
                Continuous = true,
                ReplicatorType = ReplicatorType.PushAndPull
            };
            _replicator = new Replicator(replicatorConfig);
            _replicator.StatusChanged += (sender, args) =>
            {
                Console.WriteLine($"Replication Activity: {args.Status.Activity}");
                Console.WriteLine($"Replication Completed: {args.Status.Progress.Completed}");
                Console.WriteLine($"Replication Total: {args.Status.Progress.Total}");
            };
            _replicator.Start();
        }

        [Fact]
        public void Run()
        {
            // Create docs
            var numDocs = 100000;
            Console.WriteLine($"Saving: {numDocs} docs");
            _db.InBatch(() =>
            {
                for (int i = 0; i < numDocs; i++)
                {
                    var doc = new Document($"doc_{i}");
                    doc["random"].Value = Guid.NewGuid().ToString();
                    _db.Save(doc);
                }
            });

            // Update docs
            var stopWatch = new Stopwatch();
            stopWatch.Start();
            var r = new Random();
            while (true)
            {
                double totalMin = stopWatch.Elapsed.TotalMinutes;
                Console.WriteLine($"Scenario runtime: {totalMin} min");

                if (totalMin > _scenarioRuntimeMinutes)
                {
                    // We have reached the total time we would like to run
                    // for. Exit
                    break;
                }

                // Update a random doc
                int rInt = r.Next(0, numDocs);
                Document doc = _db.GetDocument($"doc_{rInt}");
                doc["random"].Value = Guid.NewGuid().ToString();
                _db.Save(doc);

                // Sleep between each update
                Task.Delay(100).Wait();
            }

            // Delete docs
            Console.WriteLine($"Deleting: {numDocs} docs");
            for (int i = 0; i < numDocs; i++)
            {
                var doc = _db.GetDocument($"doc_{i}");
                _db.Delete(doc);
            }

            stopWatch.Stop();
            _replicator.Stop();
            _db.Delete();
        }
    }
}
