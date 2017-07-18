using System;
using System.Threading.Tasks;

using Couchbase.Lite;
using Couchbase.Lite.Support;
using Couchbase.Lite.Logging;

using Xunit;
using Couchbase.Lite.Sync;
using System.Diagnostics;
using System.Collections.Generic;
using System.Reflection;
using System.Linq;
using Microsoft.Extensions.Logging;

namespace Testkit.Net.Desktop
{

    public class Longevity
    {
        private readonly Database _db;
        private readonly Replicator _replicator;
        private readonly double _scenarioRuntimeMinutes;
        private readonly int _maxDocs;

        public Longevity(string syncGatewayUrl, double scenarioRuntimeMinutes, int maxDocs)
        {
            _scenarioRuntimeMinutes = scenarioRuntimeMinutes;
            _maxDocs = maxDocs;

            NetDestkop.Activate();
            Log.SetLiteCoreLogLevels(new Dictionary<string, LogLevel>
            {
                ["Sync"] = LogLevel.Debug,
                ["DB"] = LogLevel.Debug,
                ["SQL"] = LogLevel.Debug,
            });

            var nativeClass = Type.GetType("LiteCore.Interop.NativePrivate, Couchbase.Lite");
            var method = nativeClass.GetTypeInfo().DeclaredMethods.Where((arg) => arg.Name == "c4log_warnOnErrors").First();
            method.Invoke(null, new object[] { true });

            _db = new Database("in-for-the-long-haul");

            Console.WriteLine($"Running Scenario for {_scenarioRuntimeMinutes}min ...");
            Console.WriteLine($"Replicating with Sync Gateway: {syncGatewayUrl}");
            var replicatorConfig = new ReplicatorConfiguration(_db, new Uri($"{syncGatewayUrl}"))
            {
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
            Console.WriteLine($"Saving: {_maxDocs} docs");
            _db.InBatch(() =>
            {
                for (int i = 0; i < _maxDocs; i++)
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


                if (totalMin > _scenarioRuntimeMinutes)
                {
                    // We have reached the total time we would like to run
                    // for. Exit
                    break;
                }

                // Update a random doc
                int rInt = r.Next(0, _maxDocs);
                Document doc = _db.GetDocument($"doc_{rInt}");

                Console.WriteLine($"Updating doc: {doc.Id}");

                doc["random"].Value = Guid.NewGuid().ToString();
                _db.Save(doc);

                // Sleep between each update
                Task.Delay(100).Wait();
            }

            // Delete docs
            Console.WriteLine($"Deleting: {_maxDocs} docs");
            for (int i = 0; i < _maxDocs; i++)
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
