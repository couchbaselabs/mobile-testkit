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

        public static void Start_Client([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            ResetStatus();
            Database db = MemoryMap.Get<Database>(postBody["database"].ToString());
            // string port = "5000";
            int port = (int)postBody["port"];
            string targetIP = postBody["host"].ToString();
            string remote_DBName = postBody["serverDBName"].ToString();
            //Boolean continuous = Convert.ToBoolean(postBody["continuous"]);
            string replicationType = postBody["replicationType"].ToString();
            string endPointType = postBody["endPointType"].ToString();
            // List<object> documentIDs = (List<object>)postBody["documentIDs"];
            // var _endpoint = null;
            ReplicatorConfiguration config = null;

            Uri host = new Uri("ws://" + targetIP + ":" + port); //sgPort = "4984";
            var dbUrl = new Uri(host, remote_DBName);
            AddStatus("Connecting " + host + "...");
            if (endPointType == "URLEndPoint")
            {
                var _endpoint = new URLEndpoint(dbUrl);
                config = new ReplicatorConfiguration(db, _endpoint);
                
            }
            else{
                TcpMessageEndpointDelegate endpointDelegate = new TcpMessageEndpointDelegate();
                var _endpoint = new MessageEndpoint("something", host, ProtocolType.ByteStream, endpointDelegate);
                config = new ReplicatorConfiguration(db, _endpoint);
            }


            // config = new ReplicatorConfiguration(db, _endpoint);

                //ReplicatorType = ReplicatorType.PushAndPull,
                //Continuous = true//,
                //Authenticator = new BasicAuthenticator(userName, userPw)
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