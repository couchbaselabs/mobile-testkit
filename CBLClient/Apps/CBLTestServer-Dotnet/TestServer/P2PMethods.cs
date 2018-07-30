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

        public static void Start_Client_UEP([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            string targetIP = postBody["host"].ToString();
            string port = "5000";
            string remote_DBName = postBody["serverDBName"].ToString();

            ///string username = postBody["username"].ToString();
            //string password = postBody["password"].ToString();

            Uri host = new Uri("ws://" + targetIP + ":" + port); //sgPort = "4984";
            var dbUrl = new Uri(host, remote_DBName);
            AddStatus("Connecting " + host + "...");
            var config = new ReplicatorConfiguration(db, new URLEndpoint(dbUrl))
            {
                ReplicatorType = ReplicatorType.PushAndPull,
                Continuous = true //,
                                  // Authenticator = new BasicAuthenticator(username, password)
            };
            Replicator _replicator = new Replicator(config);
            _replicator.Start();
            response.WriteBody(MemoryMap.Store(_replicator));
            //AddStatus("Replicator started...");
            //_replicator.AddChangeListener(ReplicationStatusUpdate);
        }

        public static void Start_Server([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            _messageEndpointListener = new MessageEndpointListener(new MessageEndpointListenerConfiguration(db, ProtocolType.ByteStream));
            _broadcaster = new ReplicatorTcpListener(_messageEndpointListener);
            _broadcaster.Start();
            AddStatus("Start waiting for connection..");
            response.WriteEmptyBody();
        }

        public static void Start_Client_MEP([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            string port = "5000";
            string targetIP = postBody["host"].ToString();
            string remote_DBName = postBody["serverDBName"].ToString();

            //string username = postBody["username"].ToString();
            //string password = postBody["password"].ToString();

            Uri host = new Uri("ws://" + targetIP + ":" + port); //sgPort = "4984";
            var dbUrl = new Uri(host, remote_DBName);
            AddStatus("Connecting " + host + "...");
            TcpMessageEndpointDelegate endpointDelegate = new TcpMessageEndpointDelegate();
            var _messageEndpoint = new MessageEndpoint("something", host, ProtocolType.ByteStream, endpointDelegate);
            var config = new ReplicatorConfiguration(db, _messageEndpoint)
            {
                ReplicatorType = ReplicatorType.PushAndPull,
                Continuous = true//,
                //Authenticator = new BasicAuthenticator(userName, userPw)
            };
            Replicator _replicator = new Replicator(config);
            _replicator.Start();
            response.WriteBody(MemoryMap.Store(_replicator));
            //AddStatus("Replicator started...");
            //_replicator.AddChangeListener(ReplicationStatusUpdate);

        }

        /*static private void ReplicationStatusUpdate(object sender, ReplicatorStatusChangedEventArgs args)
        {
            //The replication is finished or hit a fatal error.
            if (args.Status.Activity == ReplicatorActivityLevel.Stopped)
            {
                AddStatus("Replication is stopped");
            }//The replicator is offline as the remote host is unreachable.
            else if (args.Status.Activity == ReplicatorActivityLevel.Offline)
            {
                AddStatus("Replication is offline");
            } //The replicator is connecting to the remote host.
            else if (args.Status.Activity == ReplicatorActivityLevel.Connecting)
            {
                AddStatus("Replication is connecting");
            } //The replication caught up with all the changes available from the server. 
              //The IDLE state is only used in continuous replications.
            else if (args.Status.Activity == ReplicatorActivityLevel.Idle)
            {
                AddStatus("Replication is idle");
            } //The replication is actively transferring data.
            else if (args.Status.Activity == ReplicatorActivityLevel.Busy)
            {
                AddStatus("Replication is busy");
            }

            AddStatus("Replication total: " + args.Status.Progress.Total);
            AddStatus("Replication completed: " + args.Status.Progress.Completed);

            if (args.Status.Error != null)
            {
                AddStatus($"Error :: {args.Status.Error}");
            }
        } */

        static private void ResetStatus()
        {
            Console.Clear();
            Console.WriteLine("Status");
        }

        static public void AddStatus(string newStatus)
        {
            Console.WriteLine(newStatus);
        }
    }
}