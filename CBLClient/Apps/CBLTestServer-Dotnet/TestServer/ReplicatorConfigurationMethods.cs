// 
//  ReplicatorConfigurationMethods.cs
// 
//  Author:
//   Prasanna Gholap  <prasanna.gholap@couchbase.com>
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
// 
//  http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// 

using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;
using System.Linq;
using System.Security.Cryptography.X509Certificates;

using Couchbase.Lite.Sync;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    public class ReplicatorConfigurationMethods
    {
        public static void Create([NotNull] NameValueCollection args,
                                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                     [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "sourceDb", sdb =>
            {
                if (postBody["targetURI"] != null)
                {
                    var targetUrl = (URLEndpoint)postBody["targetURI"];
                    var replicationConfig = MemoryMap.New<ReplicatorConfiguration>(sdb, targetUrl);
                    response.WriteBody(replicationConfig);
                }
                else if (postBody["targetDb"] != null)
                {
                    With<Database>(postBody, "targetDB", tdb =>
                    {
                        DatabaseEndpoint dbEndPoint = new DatabaseEndpoint(tdb);
                        response.WriteBody(MemoryMap.New<ReplicatorConfiguration>(sdb, dbEndPoint));
                    });
                }
                else
                {
                    throw new ArgumentException("Invalid value for replication_type");
                }
            });
        }


        public static void Configure([NotNull] NameValueCollection args,
                                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                     [NotNull] HttpListenerResponse response)
        {
            ReplicatorConfiguration config = null;
            Assembly _assembly;
            Stream _imageStream;
            StreamReader _textStreamReader;

            With<Database>(postBody, "source_db", sdb =>
            {
                if (postBody.ContainsKey("target_url"))
                {
                    Uri uri = new Uri(postBody["target_url"].ToString());
                    URLEndpoint targetUrl = new URLEndpoint(uri);
                    config = new ReplicatorConfiguration(sdb, targetUrl);
                }
                else if (postBody.ContainsKey("target_db"))
                {
                    With<Database>(postBody, "target_db", tdb =>
                    {
                        DatabaseEndpoint dbEndPoint = new DatabaseEndpoint(tdb);
                        config = new ReplicatorConfiguration(sdb, dbEndPoint);
                    });
                }
                else
                {
                    throw new Exception("Illegal arguments provided");
                }
                if (postBody.ContainsKey("continuous"))
                {
                    config.Continuous = Convert.ToBoolean(postBody["continuous"]);
                }
                if (postBody.ContainsKey("channels"))
                {
                    List<object> channels = (List<object>)postBody["channels"];
                    config.Channels = channels.Cast<string>().ToList();
                }
                if (postBody.ContainsKey("documentIDs"))
                {
                    List<object> documentIDs = (List<object>)postBody["documentIDs"];
                    config.DocumentIDs = documentIDs.Cast<string>().ToList();
                }
                if (postBody.ContainsKey("authenticator"))
                {
                    Authenticator authenticator = MemoryMap.Get<Authenticator>(postBody["authenticator"].ToString());
                    config.Authenticator = authenticator;
                }

                if (postBody.ContainsKey("headers"))
                {
                    Dictionary<String, String> headers = new Dictionary<string, string>();
                    Dictionary<String, object> header_object = (Dictionary<String, Object>)postBody["headers"];
                    foreach (KeyValuePair<string, object> keyValuePair in header_object)
                    {
                        headers.Add(keyValuePair.Key, keyValuePair.Value.ToString());
                    }
                    config.Headers = headers;
                }

                if (postBody.ContainsKey("pinnedservercert"))
                {
                    var cert_file = postBody["pinnedservercert"].ToString();
                    _assembly = Assembly.GetExecutingAssembly();
                    _textStreamReader = new StreamReader(_assembly.GetManifestResourceStream("TestServer." + cert_file + ".pem"));
    
                    byte[] cert = System.Text.Encoding.UTF8.GetBytes(_textStreamReader.ReadToEnd());
                    config.PinnedServerCertificate = new X509Certificate2(cert);
                }

                if (postBody.ContainsKey("replication_type"))
                {
                    var replicatorType = postBody["replication_type"].ToString().ToLower();
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
                }
                response.WriteBody(MemoryMap.Store(config));
            });
        }

        public static void GetAuthenticator([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Authenticator));
        }

        public static void GetChannels([NotNull] NameValueCollection args,
                                    [NotNull] IReadOnlyDictionary<string, object> postBody,
                                    [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Channels));
        }

        public static void GetDatabase([NotNull] NameValueCollection args,
                                       [NotNull] IReadOnlyDictionary<string, object> postBody,
                                       [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Database));
        }

        public static void GetDocumentIDs([NotNull] NameValueCollection args,
                                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                                          [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.DocumentIDs));
        }

        public static void GetPinnedServerCertificate([NotNull] NameValueCollection args,
                                                      [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                      [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.PinnedServerCertificate));
        }

        public static void GetReplicatorType([NotNull] NameValueCollection args,
                                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.ReplicatorType.ToString()));
        }

        public static void GetTarget([NotNull] NameValueCollection args,
                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                     [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Target.ToString()));
        }

        public static void IsContinuous([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Continuous));
        }

        public static void SetAuthenticator([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                With<Authenticator>(postBody, "authenticator", auth => {
                    repConf.Authenticator = auth;
                    response.WriteEmptyBody();
                });
            });
        }

        public static void SetChannels([NotNull] NameValueCollection args,
                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                     [NotNull] HttpListenerResponse response)
        {
            IList<string> channels = (IList<string>)postBody["channels"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.Channels = channels;
            });
        }

        public static void SetContinuous([NotNull] NameValueCollection args,
             [NotNull] IReadOnlyDictionary<string, object> postBody,
             [NotNull] HttpListenerResponse response)
        {
            Boolean continuous = (Boolean)postBody["continuous"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.Continuous = continuous;
            });
        }

        public static void SetDocumentIDs([NotNull] NameValueCollection args,
             [NotNull] IReadOnlyDictionary<string, object> postBody,
             [NotNull] HttpListenerResponse response)
        {
            IList<string> documentIds = (IList<string>)postBody["documentIds"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.DocumentIDs = documentIds;
            });
        }

        public static void SetReplicatorType([NotNull] NameValueCollection args,
                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                     [NotNull] HttpListenerResponse response)
        {
            var replicatorType = postBody["replication_type"].ToString().ToLower();
            ReplicatorType replType = new ReplicatorType();

            if (replicatorType == "push")
            {
                replType = ReplicatorType.Push;
            }
            else if (replicatorType == "pull")
            {
                replType = ReplicatorType.Pull;
            }
            else
            {
                replType = ReplicatorType.PushAndPull;
            }
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.ReplicatorType = replType;
            });
        }

        //public static void setPinnedServerCertificate([NotNull] NameValueCollection args,
        //                                              [NotNull] IReadOnlyDictionary<string, object> postBody,
        //                                              [NotNull] HttpListenerResponse response)
        //{
        //    Byte cert = (Byte)postBody["cert"];
        //    IList<string> documentIds = (IList<string>)postBody["documentIds"];
        //    With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
        //    {
        //        repConf.PinnedServerCertificate = cert;
        //    });
        //}
    }
}
