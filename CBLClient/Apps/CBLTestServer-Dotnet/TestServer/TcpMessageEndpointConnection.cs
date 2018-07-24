using Couchbase.Lite.P2P;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace Couchbase.Lite.Testing
{
    public sealed class TcpMessageEndpointConnection : IMessageEndpointConnection
    {
        #region Constants

        internal const int Port = 59840;
        private const int ReceiveBufferSize = 8192;

        public enum STATUS
        {
            OPEN,
            CLOSE,
            SEND,
            TIMEOUT //15 sec
        }

        #endregion

        #region Variables

        private readonly CancellationTokenSource _cancelSource = new CancellationTokenSource();
        private bool _connected;
        private IReplicatorConnection _replicatorConnection;

        Stream _networkStream; //NetworkStream, SslStream
        WebSocketConnection _socketConnection;
        int _timeOut = 15000;
        Uri _uri;

        public delegate void StatusUpdatedEventHandler(object sender, STATUS s);
        public event StatusUpdatedEventHandler StatusUpdated;
        public TcpClient Client;

        #endregion

        #region Constructors

        public TcpMessageEndpointConnection(Uri uri)
        {
            _uri = uri;
            _socketConnection = new WebSocketConnection(uri);
            _socketConnection.ConnectStatusUpdated += socketConnectedStatusUpdate;
            _socketConnection.Start();
        }

        /// <summary>
        /// Constructs a new replicator Active Peer connection instance via Tcp Connection
        /// </summary>
        /// <param name="client">tcp client that is accepted by the listener</param>
        public TcpMessageEndpointConnection(TcpClient client)
        {
            // _client is *already* connected
            Client = client;
            _networkStream = Client.GetStream();
        }

        #endregion

        #region IMessageEndpointConnection

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

            if (_socketConnection != null)
            {
                _socketConnection.CloseSocket();
                _socketConnection.ConnectStatusUpdated -= socketConnectedStatusUpdate;
                StatusUpdated?.Invoke(this, STATUS.CLOSE);
            }
            else
            {
                _cancelSource.Cancel();
                _connected = false;
                Client.Close();
                Client.Dispose();
                Client = null;
            }
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

            if (_socketConnection != null)
            {
                while (_networkStream == null) { await Task.Delay(1000); }
            }
            else
            {
                _networkStream.PerformServerWebSocketHandshake();
                _connected = true;
            }

            _replicatorConnection = connection;
            var ignore = Task.Factory.StartNew(ReceiveLoop, TaskCreationOptions.LongRunning);
        }

        /// <summary>
        /// Sends a message to the remote endpoint
        /// </summary>
        /// <param name="message">The message to send</param>
        /// <returns>A task that can be awaited to determine the end of the send</returns>
        public async Task Send(Message message)
        {
            while (!_connected && _timeOut > 0) { await Task.Delay(1000); _timeOut -= 1000; }
            if (_timeOut <= 0)
            {
                StatusUpdated?.Invoke(this, STATUS.TIMEOUT);
            }
            else
            {
                var bytes = message.ToByteArray();
                await _networkStream.WriteAsync(bytes, 0, bytes.Length).ConfigureAwait(false);
                StatusUpdated?.Invoke(this, STATUS.SEND);
            }
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
                    while ((length = _networkStream.Read(buffer, 0, buffer.Length)) != 0)
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

        private void socketConnectedStatusUpdate(object sender, bool connected)
        {
            if (connected)
            {
                _networkStream = _socketConnection.NetworkStream;
                _connected = connected;
                StatusUpdated?.Invoke(this, STATUS.OPEN);
            }
        }

        #endregion
    }

    internal static class StreamExt
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
    }
}
