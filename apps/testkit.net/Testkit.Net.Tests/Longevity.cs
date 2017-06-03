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
        private readonly Database _dbTwo;
        private readonly Replicator _replicator;
        private readonly double _scenarioRuntimeMinutes = 180;

        public Longevity()
        {
            NetDestkop.Activate();

            _db = new Database("in-for-the-long-haul");
            _dbTwo = new Database("in-for-the-long-haul-2");

            var replicatorConfig = new ReplicatorConfiguration
            {
                Database = _db,
                Target = new ReplicatorTarget(new Uri("blip://localhost:4984/db")),
                //Target = new ReplicatorTarget(_dbTwo),
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
            // Start timing
            var stopWatch = new Stopwatch();
            stopWatch.Start();

            // Create docs
            var numDocs = 1000;
            _db.InBatch(() =>
            {
                for (int i = 0; i < numDocs; i++)
                {
                    var doc = new Document($"doc_{i}");
                    doc["random"].Value = Guid.NewGuid().ToString();
                    _db.Save(doc);
                }
            });

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
                Task.Delay(500).Wait();
            }

            stopWatch.Stop();

            _replicator.Stop();
            _db.Delete();
            _dbTwo.Delete();
        }
    }
}
