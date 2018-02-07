using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using System.Net;
using System.Threading.Tasks;
using Couchbase.Lite;

using static Couchbase.Lite.Conflict;


using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

namespace Couchbase.Lite.Testing
{
    internal static class ConflictMethods
    {
        public static void Resolver([NotNull] NameValueCollection args,
                                    [NotNull] IReadOnlyDictionary<string, object> postBody,
                                    [NotNull] HttpListenerResponse response)
        {
            var conflictType = postBody["conflict_type"].ToString();
            if (conflictType == "mine")
            {
                var conflictID = MemoryMap.New<ReplicationMine>();
                response.WriteBody(conflictID);                    
            }
            else if (conflictType == "theirs")
            {
                var conflictID = MemoryMap.New<ReplicationTheirs>();
                response.WriteBody(conflictID);
            }
            else if (conflictType == "base")
            {
                var conflictID = MemoryMap.New<ReplicationBase>();
                response.WriteBody(conflictID);
            }
            else
            {
                response.WriteEmptyBody();
            }

        }

        public class ReplicationMine : IConflictResolver
        {
            public Document Resolve(Conflict conflict)
            {
                return conflict.Mine;
            }
        }

        public class ReplicationTheirs : IConflictResolver
        {
            public Document Resolve(Conflict conflict)
            {
                return conflict.Theirs;
            }
        }

        public class ReplicationBase : IConflictResolver
        {
            public Document Resolve(Conflict conflict)
            {
                return conflict.Base;
            }
        }

        public class Giveup : IConflictResolver
        {
            public Document Resolve(Conflict conflict)
            {
                return null;
            }
        }
    }   
}

