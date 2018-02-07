// 
//  NameValueCollectionExtensions.cs
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
using System.Collections.Specialized;
using System.Globalization;

using JetBrains.Annotations;

namespace Couchbase.Lite.Testing
{
    internal static class NameValueCollectionExtensions
    {
        #region Public Methods

        public static long GetLong([NotNull]this NameValueCollection collection, string key)
        {
            var gotValue = collection.Get(key) ?? throw new ArgumentNullException(key);
            if (!Int64.TryParse(gotValue, NumberStyles.Integer, CultureInfo.InvariantCulture, out long gotLong)) {
                throw new ArgumentException($"Invalid numeric received for {key}: {gotValue}");
            }

            return gotLong;
        }

        public static bool GetBoolean([NotNull] this NameValueCollection collection, string key)
        {
            var gotValue = collection.Get(key) ?? throw new ArgumentNullException(key);
            if (!Boolean.TryParse(gotValue, out bool gotBool)) {
                throw new ArgumentException($"Invalid boolean received for {key}: {gotValue}");
            }

            return gotBool;
        }

        public static string GetString([NotNull] this NameValueCollection collection, string key)
        {
            var gotValue = collection.Get(key) ?? throw new ArgumentNullException(key);
            return Uri.UnescapeDataString(gotValue);
        }

        #endregion
    }
}