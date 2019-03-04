using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.IO;
using System.Net;
using JetBrains.Annotations;
using Couchbase.Lite.Logging;

namespace Couchbase.Lite.Testing
{
    public class FileLoggingMehtod
    {
        public static void Configure([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            String log_level = postBody["log_level"].ToString();
            String directory = postBody["directory"].ToString();
            int max_rotate_count = (int)postBody["max_rotate_count"];
            long max_size = (long)postBody["max_size"];
            bool plain_text = Convert.ToBoolean(postBody["plain_text"]);

            if (directory.Equals(""))
            {
                directory = Directory.GetCurrentDirectory() + "log_" + (DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds).ToString();
                Console.WriteLine("File logging configured at: " + directory.ToString());
            }
            LogFileConfiguration config = new LogFileConfiguration(directory);
            if (max_rotate_count > 1)
            {
                config.MaxRotateCount = max_rotate_count;
            }
            if (max_size > 512000)
            {
                config.MaxSize = max_size;
            }
            config.UsePlaintext = plain_text;
            Database.Log.File.Config = config;
            switch (log_level)
            {
                case "debug":
                    Database.Log.File.Level = LogLevel.Debug;
                    break;
                case "verbose":
                    Database.Log.File.Level = LogLevel.Verbose;
                    break;
                case "info":
                    Database.Log.File.Level = LogLevel.Info;
                    break;
                case "error":
                    Database.Log.File.Level = LogLevel.Error;
                    break;
                case "warning":
                    Database.Log.File.Level = LogLevel.Warning;
                    break;
                default:
                    Database.Log.File.Level = LogLevel.None;
                    break;
            }
            response.WriteBody(directory);
        }

        public static void GetPlainTextStatus([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Config.UsePlaintext);

        }

        public static void GetLogLevel([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Level.GetHashCode());

        }

        public static void GetMaxSize([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Config.MaxSize);

        }

        public static void GetMaxRotateCount([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Config.MaxRotateCount);

        }

        public static void GetConfig([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Config);

        }

        public static void GetDirectory([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Database.Log.File.Config.Directory.ToString());

        }
    }
}
