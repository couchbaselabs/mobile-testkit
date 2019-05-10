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
            if (String.IsNullOrEmpty(directory))
            {
                directory = System.IO.Path.GetTempPath();
            }
            directory = directory + "log_" + (DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds).ToString();
            Console.WriteLine("File logging configured at: " + directory.ToString());
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
            response.WriteBody(MemoryMap.Store(config));
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

        public static void SetPlainTextStatus([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            bool plain_text = Convert.ToBoolean(postBody["plain_text"]);
            LogFileConfiguration config = MemoryMap.Get<LogFileConfiguration>(postBody["config"].ToString());
            config.UsePlaintext = plain_text;
            response.WriteBody(Database.Log.File.Config);

        }

        public static void SetMaxRotateCount([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            int max_rotate_count = (int) postBody["max_rotate_count"];
            LogFileConfiguration config = MemoryMap.Get<LogFileConfiguration>(postBody["config"].ToString());
            config.MaxRotateCount = max_rotate_count;
            response.WriteBody(Database.Log.File.Config);

        }

        public static void SetMaxSize([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            long max_size = (long)postBody["max_size"];
            LogFileConfiguration config = MemoryMap.Get<LogFileConfiguration>(postBody["config"].ToString());
            config.MaxSize = max_size;
            response.WriteBody(Database.Log.File.Config);

        }

        public static void SetConfig([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            String directory = postBody["directory"].ToString();
            if (String.IsNullOrEmpty(directory))
            {
                directory = System.IO.Path.GetTempPath() + "log_" + (DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds).ToString();
                Console.WriteLine("File logging configured at: " + directory.ToString());
            }
            LogFileConfiguration config = new LogFileConfiguration(directory);
            Database.Log.File.Config = config;
            response.WriteBody(Database.Log.File.Config);

        }

        public static void SetLogLevel([NotNull] NameValueCollection args,
                                [NotNull] IReadOnlyDictionary<string, object> postBody,
                                [NotNull] HttpListenerResponse response)
        {
            String log_level = postBody["log_level"].ToString();
            LogFileConfiguration config = MemoryMap.Get<LogFileConfiguration>(postBody["config"].ToString());
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
            response.WriteBody(Database.Log.File.Config);

        }
    }
}
