using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using System.Net;
using Couchbase.Lite.P2P;
using System.Threading.Tasks;

using Couchbase.Lite;
using static Couchbase.Lite.Testing.P2PMethods;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;
using Couchbase.Lite.Sync;

namespace Couchbase.Lite.Testing
{
    public class P2PMethods
    {
        static private MessageEndpointListener _messageEndpointListener;
        static private ReplicatorTcpListener _broadcaster;

        public static void Start_Server([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            int port = (int)postBody["port"];
            _messageEndpointListener = new MessageEndpointListener(new MessageEndpointListenerConfiguration(db, ProtocolType.ByteStream));
            _broadcaster = new ReplicatorTcpListener(_messageEndpointListener, port);
            _broadcaster.Start();
            AddStatus("Start waiting for connection..");
            response.WriteBody(MemoryMap.Store(_broadcaster));
        }

        public static void Stop_Server([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            ReplicatorTcpListener _broadcaster = MemoryMap.Get<ReplicatorTcpListener>(postBody["replicatorTcpListener"].ToString());
            _broadcaster.Stop();
            AddStatus("Stopping the server..");
            response.WriteEmptyBody();
        }

        public static void Configure([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            int port = (int)postBody["port"];
            string targetIP = postBody["host"].ToString();
            string remote_DBName = postBody["serverDBName"].ToString();
            string replicationType = postBody["replicationType"].ToString();
            string endPointType = postBody["endPointType"].ToString();
            string filter_callback_func = postBody["filter_callback_func"].ToString();
            Boolean push_filter = Convert.ToBoolean(postBody["push_filter"].ToString());
            Boolean pull_filter = Convert.ToBoolean(postBody["pull_filter"].ToString());
            ReplicatorConfiguration config = null;

            Uri host = new Uri("ws://" + targetIP + ":" + port);
            var dbUrl = new Uri(host, remote_DBName);
            AddStatus("Connecting " + host + "...");
            if (endPointType == "URLEndPoint")
            {
                var _endpoint = new URLEndpoint(dbUrl);
                config = new ReplicatorConfiguration(db, _endpoint);
                
            }
            else{
                TcpMessageEndpointDelegate endpointDelegate = new TcpMessageEndpointDelegate();
                var _endpoint = new MessageEndpoint(dbUrl.AbsoluteUri, dbUrl, ProtocolType.ByteStream, endpointDelegate);
                config = new ReplicatorConfiguration(db, _endpoint);
            }

            var replicatorType = replicationType.ToLower();
            if (replicatorType == "push")
            {
                    config.ReplicatorType = ReplicatorType.Push;
            }
            else if (replicatorType == "pull")
            {
                    config.ReplicatorType = ReplicatorType.Pull;
            }
            else
            {
                    config.ReplicatorType = ReplicatorType.PushAndPull;
            }
            if (postBody.ContainsKey("continuous"))
            {
                config.Continuous = Convert.ToBoolean(postBody["continuous"]);
            }
            if (postBody.ContainsKey("documentIDs"))
            {
                List<object> documentIDs = (List<object>)postBody["documentIDs"];
                config.DocumentIDs = documentIDs.Cast<string>().ToList();
            }
            if (postBody["push_filter"].Equals(true))
            {
                if (filter_callback_func == "boolean")
                {
                    config.PushFilter = _replicator_boolean_filter_callback;
                }
                else if (filter_callback_func == "deleted")
                {
                    config.PushFilter = _replicator_deleted_filter_callback;
                }
                else if (filter_callback_func == "access_revoked")
                {
                    config.PushFilter = _replicator_access_revoked_filter_callback;
                }
                else
                {
                    config.PushFilter = _default_replicator_filter_callback;
                }
            }

            if (postBody["pull_filter"].Equals(true))
            {
                if (filter_callback_func == "boolean")
                {
                    config.PullFilter = _replicator_boolean_filter_callback;
                }
                else if (filter_callback_func == "deleted")
                {
                    config.PullFilter = _replicator_deleted_filter_callback;
                }
                else if (filter_callback_func == "access_revoked")
                {
                    config.PullFilter = _replicator_access_revoked_filter_callback;
                }
                else
                {
                    config.PullFilter = _default_replicator_filter_callback;
                }

            }
            Replicator replicator = new Replicator(config);
            response.WriteBody(MemoryMap.Store(replicator));

        }

        private static bool _replicator_boolean_filter_callback(Document document, DocumentFlags flags)
        {
            if (document.Contains("new_field_1"))
            {
                return document.GetBoolean("new_field_1");
            }
            return true;
        }

        private static bool _default_replicator_filter_callback(Document document, DocumentFlags flags)
        {
            return true;
        }

        private static bool _replicator_deleted_filter_callback(Document document, DocumentFlags flags)
        {
            return !flags.HasFlag(DocumentFlags.Deleted);
        }

        private static bool _replicator_access_revoked_filter_callback(Document document, DocumentFlags flags)
        {
            return !flags.HasFlag(DocumentFlags.AccessRemoved);
        }


        public static void Start_Client([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            Replicator replicator = MemoryMap.Get<Replicator>(postBody["replicator"].ToString());
            replicator.Start();
            response.WriteEmptyBody();
        }
            static private void ResetStatus()
        {
            // Console.Clear();
            Console.WriteLine("Status is getting reset");
        }

        static public void AddStatus(string newStatus)
        {
            Console.WriteLine(newStatus);
        }
    }
}
