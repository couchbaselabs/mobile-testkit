// 
//  MemoryMap.cs
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
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Threading;

using JetBrains.Annotations;

namespace Couchbase.Lite.Testing
{
    public static class MemoryMap
    {
        #region Constants

        [NotNull]
        private static readonly ConcurrentDictionary<string, object> Map = new ConcurrentDictionary<string, object>();

        #endregion

        #region Variables

        private static long _NextId;
        private static string _IP = MemoryMap.GetMyHostIP(NetworkInterfaceType.Ethernet);

        #endregion

        #region Private Methods
        internal static string GetMyHostIP(NetworkInterfaceType _type)
        {
            string output = "";
            foreach (NetworkInterface item in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (item.NetworkInterfaceType == _type && item.OperationalStatus == OperationalStatus.Up)
                {
                    foreach (UnicastIPAddressInformation ip in item.GetIPProperties().UnicastAddresses)
                    {
                        if (ip.Address.AddressFamily == AddressFamily.InterNetwork)
                        {
                            output = ip.Address.ToString();
                            break;
                        }
                    }
                }
                if (output != "")
                {
                    break;
                }
            }
            Console.WriteLine("My IP Address is :" + output);
            return output;
        }
        # endregion

        #region Public Methods

        public static void Clear()
        {
            foreach (var pair in Map)
            {
                if (pair.Value is IDisposable d)
                {
                    try {
                        d.Dispose();
                    } catch {
                        Console.WriteLine("Failed to dispose " + d.ToString());
                        throw;
                    }
                }
            }

            Map.Clear();
            Interlocked.Exchange(ref _NextId, 0L);
        }

        [NotNull]
        public static T Get<T>(string id)
        {
            if (!Map.TryGetValue(id, out object existing))
            {
                throw new KeyNotFoundException($"Can't find object with id {id}");
            }

            if (!(existing is T castValue))
            {
                throw new InvalidCastException($"Requested object {id} of type {typeof(T).Name}, but object was actually {existing.GetType()?.Name}");
            }

            return castValue;
        }

        public static string New<T>(params object[] args)
        {
            var nextObject = Activator.CreateInstance(typeof(T), args);
            return Store(nextObject);
        }

        public static void Release(string id)
        {
            if (!Map.TryRemove(id, out object existing))
            {
                throw new KeyNotFoundException($"Can't find object with id {id}");
            }

            if (existing is IDisposable d)
            {
                try {
                    d.Dispose();
                } catch {
                    Console.WriteLine("Failed to dispose " + d.ToString());
                    throw;
                }
            }
        }

        public static string Store(object obj)
        {
            var nextId = "@" + Interlocked.Increment(ref _NextId).ToString() + "_" + _IP + "_net";
            if (!Map.TryAdd(nextId, obj))
            {
                throw new InvalidOperationException("Unable to add newly created object to MemoryMap");
            }

            return nextId;
        }

        #endregion
    }
}