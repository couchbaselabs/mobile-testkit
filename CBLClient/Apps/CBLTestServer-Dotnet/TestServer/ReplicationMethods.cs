// 
//  ReplicationMethods.cs
// 
//  Author:
//   Jim Borden  <jim.borden@couchbase.com>
// 
//  Copyright (c) 2017 Couchbase, Inc All rights reserved.
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
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using Couchbase.Lite.Sync;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class ReplicationMethods
    {

        public static void Create([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "config", repConf => response.WriteBody(MemoryMap.New<Replicator>(repConf)));
        }

        public static void GetConfig([NotNull] NameValueCollection args,
                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                     [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep => response.WriteBody(rep.Config)); 
        }

        public static void GetActivityLevel([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                ReplicatorActivityLevel activityLevel = rep.Status.Activity;
                response.WriteBody(activityLevel.ToString().ToLower());
            });
        }

        public static void GetCompleted([NotNull] NameValueCollection args,
                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                     [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                response.WriteBody(rep.Status.Progress.Completed);
            });
        }

        public static void GetError([NotNull] NameValueCollection args,
                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                     [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                Exception ex = rep.Status.Error;
                if (ex != null)
                {
                    response.WriteBody(ex.ToString());
                }
                response.WriteEmptyBody();
            });
        }

        public static void GetTotal([NotNull] NameValueCollection args,
                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                     [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep => response.WriteBody(rep.Status.Progress.Total));
        }

        public static void IsContinuous([NotNull] NameValueCollection args,
                                        [NotNull] IReadOnlyDictionary<string, object> postBody,
                                        [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Continuous));
        }

        public static void ToString([NotNull] NameValueCollection args,
                                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                                             [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep => response.WriteBody(rep.ToString()));
        }

        public static void StartReplication([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", r =>
            {
                r.Start();
                response.WriteEmptyBody();
            });
        }

        public static void StopReplication([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", r =>
            {
                r.Stop();
                response.WriteEmptyBody();
            });
        }

        public static void Status([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep => response.WriteBody(rep.Status.ToString()));
        }

        internal static void AddDocumentReplicationChangeListener([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                var listener = new DocumentReplicationListenerProxy();
                rep.AddDocumentReplicationListener(listener.HandleChange);
                response.WriteBody(MemoryMap.Store(listener));
            });
        }

        internal static void AddChangeListener([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                var listener = new ReplicationChangeListenerProxy();
                rep.AddChangeListener(listener.HandleChange);
                response.WriteBody(MemoryMap.Store(listener));
            });
        }

        internal static void RemoveChangeListener([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                var listener = (ListenerToken)postBody["changeListener"];
                rep.RemoveChangeListener(listener);
            });
        }

        internal static void ChangeListenerChangesCount([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ReplicationChangeListenerProxy>(postBody, "changeListener", changeListener =>
            {
                response.WriteBody(changeListener.Changes.Count);
            });
        }

        internal static void ChangeListenerChanges([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ReplicationChangeListenerProxy>(postBody, "changeListener", changeListener =>
            {
                response.WriteBody(MemoryMap.Store(changeListener.Changes));
            });
        }


        internal static void AddReplicatorEventChangeListener([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                var listener = new DocumentReplicationListenerProxy();
                rep.AddDocumentReplicationListener(listener.HandleChange);
                response.WriteBody(MemoryMap.Store(listener));
            });
        }

        internal static void RemoveReplicatorEventListener([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", rep =>
            {
                var listener = (ListenerToken)postBody["changeListener"];
                rep.RemoveChangeListener(listener);
            });
        }

        internal static void ReplicatorEventChangesCount([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<DocumentReplicationListenerProxy>(postBody, "changeListener", changeListener =>
            {
                response.WriteBody(changeListener.Changes.Count);
            });
        }

        internal static void ReplicatorEventGetChanges([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<DocumentReplicationListenerProxy>(postBody, "changeListener", changeListener =>
            {
                response.WriteBody(MemoryMap.Store(changeListener.Changes));
            });
        }

        public static void ResetCheckpoint([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replicator", r =>
            {
                r.ResetCheckpoint();
                response.WriteEmptyBody();
            });
        }
    }

    internal sealed class ReplicationChangeListenerProxy
    {
        #region Variables

        [NotNull]
        private readonly List<ReplicatorStatusChangedEventArgs> _changes = new List<ReplicatorStatusChangedEventArgs>();

        #endregion

        #region Properties

        [NotNull]
        public IReadOnlyList<ReplicatorStatusChangedEventArgs> Changes => _changes;

        #endregion

        #region Public Methods

        public void HandleChange(object sender, ReplicatorStatusChangedEventArgs args)
        {
            _changes.Add(args);
        }

        #endregion
    }

    internal sealed class DocumentReplicationListenerProxy
    {
        #region Variables

        [NotNull]
        private readonly List<DocumentReplicationEventArgs> _changes = new List<DocumentReplicationEventArgs>();

        #endregion

        #region Properties

        [NotNull]
        public IReadOnlyList<DocumentReplicationEventArgs> Changes => _changes;

        #endregion

        #region Public Methods

        public void HandleChange(object sender, DocumentReplicationEventArgs args)
        {
            _changes.Add(args);
        }

        #endregion
    }
}


