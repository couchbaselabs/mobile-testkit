using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

using Couchbase.Lite.Sync;

using JetBrains.Annotations;

using Newtonsoft.Json;

using TestClient.Orchestration;

namespace TestClient
{
    class Program
    {
        public const string ServerUrl = "http://192.168.1.5:55555/";
        public const string SyncGatewayOrchestrationUrl = "http://192.168.1.2:55555/";

        static async Task Main(string[] args)
        {
            Console.WriteLine("Press any key to start...");
            Console.ReadKey(true);

            var directory = Path.GetDirectoryName(typeof(Program).Assembly.Location);
            var configText = File.ReadAllText(Path.Combine(directory, "Orchestration", "GatewayConfig.json"));
            using (var sgWrapper = new RemoteProxySyncGateway(null, configText)) {
                var sg = sgWrapper.AsSyncGateway();
                var sessionInfo =
                    await sg.Admin.PostSessionAsync("seekrit", new Dictionary<string, string> { ["name"] = "pupshaw" });
                sg.Session = sessionInfo.SessionId;
                await sg.Public.PostBulkDocsAsync("seekrit", CreateDocuments()).ConfigureAwait(false);
                using (var db = new RemoteProxyDatabase("client")) {
                    
                    var repl = new RemoteProxyReplication(db, sgWrapper.GetReplicationUrl("seekrit").AbsoluteUri, false, "pull",
                        RemoteProxyReplication.BasicAuthentication("pupshaw", "frank"));
                    await repl.StartAsync().ConfigureAwait(false);
                    Console.WriteLine("Press any key to continue...");
                    Console.ReadKey(true);
                }
            }

            await RemoteProxyDatabase.DeleteAsync("client", null).ConfigureAwait(false);
        }

        [NotNull]
        private static Dictionary<string, object> CreateDocuments(int count = 100)
        {
            var retVal = new List<Dictionary<string, object>>();
            var random = new Random();
            for (var i = 0; i < count; i++) {
                var docId = $"doc{i}";
                retVal.Add(new Dictionary<string, object>
                {
                    ["value"] = random.Next().ToString(),
                    ["_id"] = docId
                });
            }

            return new Dictionary<string, object>
            {
                ["docs"] = retVal
            };
        }
    }
}
