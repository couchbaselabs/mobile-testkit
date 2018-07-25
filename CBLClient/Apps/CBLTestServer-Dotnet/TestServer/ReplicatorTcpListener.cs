// 
//  ReplicatorTcpListener.cs
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Couchbase License Agreement (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//  https://info.couchbase.com/rs/302-GJY-034/images/2017-10-30_License_Agreement.pdf
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Couchbase.Lite.P2P
{

    public sealed class ReplicatorTcpListener
    {
        private TcpClient _connectedTcpClient;
        private TcpListener _listener;
        private MessageEndpointListener _endpointListener;
        private bool _opened;

        /// <summary>
        /// Constructs a new replicator Passive Peer Tcp listener
        /// </summary>
        /// <param name="endpointListener">used to accept any incoming peer tcp client connection</param>
        public ReplicatorTcpListener(MessageEndpointListener endpointListener)
        {
            _endpointListener = endpointListener;
        }

        /// <summary>
        /// Tcp listener starts to listen for incoming and accept tcp connection(s)
        /// </summary>
        public void Start()
        {
            if (_listener == null)
            {
                try
                {
                    _listener = new TcpListener(IPAddress.Any, ReplicatorTcpConnection.Port);
                    _listener.Start();
                    _opened = true;
                    AcceptLoop();

                }
                catch (Exception)
                {
                    //placerholder for customized logging or error handling
                }
            }

        }

        /// <summary>
        /// Stop Tcp listener to listen for incoming tcp connection(s)
        /// </summary>
        public bool Stop()
        {

            if (_listener != null)
            {
                _opened = false;
                _listener.Stop();
                _listener = null;
                _endpointListener = null;
                return true;
            }

            return false;
        }

        private async Task AcceptLoop()
        {
            while (_opened)
            {
                _connectedTcpClient = await _listener?.AcceptTcpClientAsync();
                var socketConnection = new ReplicatorTcpConnection(_connectedTcpClient);
                _endpointListener.Accept(socketConnection);
            }
        }
    }
}