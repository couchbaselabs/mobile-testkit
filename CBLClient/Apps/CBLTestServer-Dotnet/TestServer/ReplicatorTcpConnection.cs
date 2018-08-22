// 
//  ReplicatorTcpConnection.cs
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
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

using System.Threading;
using System.Net.Sockets;
using System.IO;
using System.Security.Cryptography;
using Couchbase.Lite.P2P;

namespace Couchbase.Lite.Testing
{
    /// <summary>
    /// This class is P2P Replicator Tcp communication implementing IMessageEndpointConnection
    /// </summary>
    public sealed class ReplicatorTcpConnection : IMessageEndpointConnection
    {
        #region Constants

        internal const int Port = 5000;
        private const int ReceiveBufferSize = 8192;

        #endregion

        #region Variables

        private readonly CancellationTokenSource _cancelSource = new CancellationTokenSource();
        private bool _connected;
        //sprivate LogHelper _log = new LogHelper(nameof(ReplicatorTcpConnection));
        private IReplicatorConnection _replicatorConnection;
        TcpClient _client;
        Stream _networkStream; //NetworkStream, SslStream

        #endregion

        #region Constructors

        /// <summary>
        /// Constructs a new replicator Active Peer connection instance via Tcp Connection
        /// </summary>
        /// <param name="client">tcp client that is accepted by the listener</param>
        public ReplicatorTcpConnection(TcpClient client)
        {
            // _client is *already* connected
            _client = client;
            _networkStream = _client.GetStream();
        }

        #endregion

        #region Private Methods

        private async void ReceiveLoop()
        {
            var buffer = new byte[ReceiveBufferSize];
            try
            {
                while (!_cancelSource.IsCancellationRequested)
                {
                    //read from _networkStream 				
                    int length;
                    while ((length = await _networkStream.ReadAsync(buffer, 0, buffer.Length).ConfigureAwait(false)) != 0)
                    {
                        _replicatorConnection.Receive(
                                Message.FromBytes(buffer.Take(length).ToArray()));
                    }
                }
            }
            catch (Exception)
            {
                //placerholder for customized logging or error handling
            }
        }

        #endregion

        #region IMessageEndpointConnection -- Passive Peer

        /// <summary>
        /// Closes the connection to the remote endpoint
        /// </summary>
        /// <param name="error">The error that caused the replication to close, if any</param>
        /// <returns>A task that can be awaited to determine the end of the close</returns>
        public async Task Close(Exception error)
        {
            if (!_connected)
            {
                return;
            }
            _cancelSource.Cancel();
            _connected = false;
            _client.Close();
            _client.Dispose();
            _client = null;
        }

        /// <summary>
        /// Opens a connection to the remote endpoint, linking it with the given
        /// <see cref="IReplicatorConnection"/>
        /// </summary>
        /// <param name="connection">The counterpart in the send/receive relationship which
        /// is used to signal the replication process of certain key events</param>
        /// <returns>A task that can be awaited to determine the end of the open</returns>
        public async Task Open(IReplicatorConnection connection)
        {
            if (_connected)
            {
                return;
            }
            _networkStream.PerformServerWebSocketHandshake();
            _connected = true;
            _replicatorConnection = connection;
            await Task.Factory.StartNew(ReceiveLoop, TaskCreationOptions.LongRunning).ConfigureAwait(false);
            Console.Write("Finished open");
        }

        /// <summary>
        /// Sends a message to the remote endpoint
        /// </summary>
        /// <param name="message">The message to send</param>
        /// <returns>A task that can be awaited to determine the end of the send</returns>
        public async Task Send(Message message)
        {
            var bytes = message.ToByteArray();
            await _networkStream.WriteAsync(bytes, 0, bytes.Length).ConfigureAwait(false);
        }

        #endregion
    }

    /*internal static class StreamExt
    {
        internal static bool PerformServerWebSocketHandshake(this Stream stream)
        {
            var buffer = new Byte[8192];
            stream.Read(buffer, 0, buffer.Length);

            //translate bytes of request to string
            string data = Encoding.UTF8.GetString(buffer);
            if (new System.Text.RegularExpressions.Regex("^GET").IsMatch(data))
            {
                StringBuilder sb = new StringBuilder();
                const string eol = "\r\n"; // HTTP/1.1 defines the sequence CR LF as the end-of-line marker
                try
                {
                    var key = new Regex("Sec-WebSocket-Key: (.*)").Match(data).Groups[1].Value.Trim();
                    var protocol = new Regex("Sec-WebSocket-Protocol: (.*)").Match(data).Groups[1].Value.Trim();
                    var version = new Regex("Sec-WebSocket-Version: (.*)").Match(data).Groups[1].Value.Trim();
                    Byte[] response = Encoding.UTF8.GetBytes(sb.Append("HTTP/1.1 101 Switching Protocols").Append(eol)
                    .Append("Connection: Upgrade").Append(eol)
                    .Append("Upgrade: websocket").Append(eol)
                    .Append("Sec-WebSocket-Version: ").Append(version).Append(eol)
                    .Append("Sec-WebSocket-Protocol: ").Append(protocol).Append(eol)
                    .Append("Sec-WebSocket-Accept: ").Append(AcceptKey(key)).Append(eol)
                    .Append(eol).ToString());
                    stream.Write(response, 0, response.Length);
                    return true;
                }
                catch (Exception)
                {
                    // failed to get regex matched value or any other exception
                    // placerholder for customized logging or error handling
                    return false;
                }
            }
            return false;
        }

         private static string AcceptKey(string key)
        {
            string longKey = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
            SHA1 sha1 = SHA1CryptoServiceProvider.Create();
            byte[] hashBytes = sha1.ComputeHash(System.Text.Encoding.ASCII.GetBytes(longKey));
            return Convert.ToBase64String(hashBytes);
        } 
    } */
}