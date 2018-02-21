using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using System.Net;
using System.Threading.Tasks;

using Couchbase.Lite;
using static Couchbase.Lite.Testing.DatabaseMethods;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

namespace Couchbase.Lite.Testing
{
    public class DatabaseConfigurationMethods
    {
        public static void Configure([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var databaseConfig = new DatabaseConfiguration();
            if (postBody.ContainsKey("directory"))
            {
                var directory = postBody["directory"].ToString();
                databaseConfig.Directory = directory;
            }
            if (postBody.ContainsKey("encryptionKey"))
            {
                With<EncryptionKey>(postBody, "encryptionKey", er => databaseConfig.EncryptionKey = er);
            }
            var databaseConfigId = MemoryMap.Store(databaseConfig);
            response.WriteBody(databaseConfigId);
        }

        public static void Create([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var databaseConfigId = MemoryMap.New<DatabaseConfiguration>();
            response.WriteBody(databaseConfigId);
        }

        public static void GetDirectory([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            With<DatabaseConfiguration>(postBody, "config", dbconfig => response.WriteBody(dbconfig.Directory));
        }

        public static void GetEncryptionKey([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            With<DatabaseConfiguration>(postBody, "config", dbconfig => response.WriteBody(dbconfig.EncryptionKey));
        }

        public static void SetDirectory([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            var directory = postBody["directory"].ToString();
            With<DatabaseConfiguration>(postBody, "config", dbconfig => dbconfig.Directory = directory);
            response.WriteEmptyBody();
        }

        public static void SetEncryptionKey([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            
            With<DatabaseConfiguration>(postBody, "config", dbconfig => 
            {
                With<EncryptionKey>(postBody, "encryptionKey", er => dbconfig.EncryptionKey = er);
            });
            response.WriteEmptyBody();
        }
    }
}
