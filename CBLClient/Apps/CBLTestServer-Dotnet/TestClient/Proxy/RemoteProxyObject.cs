// 
//  RemoteProxyObject.cs
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

using JetBrains.Annotations;

namespace TestClient
{
    public abstract class RemoteProxyObject : IDisposable
    {
        #region Variables

        private readonly long _handle;

        #endregion

        #region Constructors

        protected RemoteProxyObject(long handle)
        {
            _handle = handle;
        }

        #endregion

        #region Public Methods

        public static implicit operator long(RemoteProxyObject obj)
        {
            return obj?._handle ?? -1;
        }

        #endregion

        #region Protected Methods

        protected abstract IObjectRESTApi GetApi();

        protected virtual void ReleaseUnmanagedResources()
        {
            GetApi()?.ReleaseAsync(_handle);
        }

        #endregion

        #region IDisposable

        public void Dispose()
        {
            ReleaseUnmanagedResources();
        }

        #endregion
    }
}