// 
// WebSocketWrapper.cs
// 
// Copyright (c) 2017 Couchbase, Inc All rights reserved.
// 
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// 
// http://www.apache.org/licenses/LICENSE-2.0
// 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// 

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

using Couchbase.Lite.Interop;
using Couchbase.Lite.Logging;
using Couchbase.Lite.Support;

using JetBrains.Annotations;

using LiteCore.Interop;

namespace Couchbase.Lite.Testing
{
    // This class is the workhorse of the flow of data during replication and needs
    // to be airtight.  Some notes:  The network stream absolutely must not be written
    // to and read from at the same time.  The documentation mentions two unique threads,
    // one for read and one for write, as the best approach.  
    //
    // This class implements an actor like system to try to avoid locking and backing
    // things up.  There are three distinct areas:
    //
    // <c>_queue</c>: This is a serial queue that processes actions that involve the state
    // of the C4Socket* object (receiving data, writing data, closing, opening, etc)
    //
    // <c>PerformRead</c>: Dedicated thread for reading from the remote stream, and passing
    // what it finds to the <c>_queue</c>
    //
    // <c>PerformWrite</c>: Dedicated thread for writing to the remote stream.  It receives
    // data via a pub-sub system whereby it is the subscriber. 
    //
    // <c>_c4Queue</c>: This is a serial queue that process actions that involve operating
    // on the C4Socket* object at the native (LiteCore) level.  The queue is used for thread
    // safety.
    //
    // Example: When it is time to write, LiteCore will callback into the C# callback, and
    // the data will end up in the <c>Write</c> method.  This method will enter the queue,
    // and then publish a message to the write thread (order is important) before exiting
    // the queue.  The write thread will pick that message up, send it, and then enter the
    // _c4Queue to inform LiteCore that it finished sending the data.
    internal sealed class WebSocketConnection
    {
        #region Constants

        enum C4WebSocketCloseCode : int
        {
            WebSocketCloseNormal = 1000,
            WebSocketCloseGoingAway = 1001,
            WebSocketCloseProtocolError = 1002,
            WebSocketCloseDataError = 1003,
            WebSocketCloseNoCode = 1005,
            WebSocketCloseAbnormal = 1006,
            WebSocketCloseBadMessageFormat = 1007,
            WebSocketClosePolicyError = 1008,
            WebSocketCloseMessageTooBig = 1009,
            WebSocketCloseMissingExtension = 1010,
            WebSocketCloseCantFulfill = 1011,
            WebSocketCloseTLSFailure = 1015,
            WebSocketCloseFirstAvailable = 4000,
        }

        private static readonly TimeSpan ConnectTimeout = TimeSpan.FromSeconds(15);
        private static readonly TimeSpan IdleTimeout = TimeSpan.FromSeconds(300);

        #endregion

        #region Variables

        private readonly HTTPLogic _logic;
        private bool _closed;
        private string _expectedAcceptHeader;
        private CancellationTokenSource _readWriteCancellationTokenSource;
        private ManualResetEventSlim _receivePause;
        private BlockingCollection<byte[]> _writeQueue;

        #endregion

        #region Properties

        public delegate void ConnectStatusUpdatedEventHandler(object sender, bool s);
        public event ConnectStatusUpdatedEventHandler ConnectStatusUpdated;

        public Stream NetworkStream { get; private set; }
        public TcpClient Client;

        #endregion

        #region Constructors

        public WebSocketConnection(Uri url)
        {
            _logic = new HTTPLogic(url);
        }

        #endregion

        #region Public Methods

        // Normal closure (requested by client)
        public void CloseSocket()
        {
            // Wait my turn!
            ResetConnections();
            if (_closed)
            {
                Console.WriteLine("Double close detected, ignoring...");
                return;
            }

            Console.WriteLine("Closing socket normally due to request from LiteCore");
            _closed = true;
        }

        // This starts the flow of data, and it is quite an intense multi step process
        // So I will label it in sequential order
        public async Task Start()
        {
            if (Client != null)
            {
                Console.WriteLine("Ignoring duplicate call to Start...");
                return;
            }

            _readWriteCancellationTokenSource = new CancellationTokenSource();
            _writeQueue = new BlockingCollection<byte[]>();
            _receivePause = new ManualResetEventSlim(true);

            // STEP 1: Create the TcpClient, which is responsible for negotiating
            // the socket connection between here and the server
            try
            {
                // ReSharper disable once UseObjectOrCollectionInitializer
                Client = new TcpClient(AddressFamily.InterNetworkV6)
                {
                    SendTimeout = (int)IdleTimeout.TotalMilliseconds,
                    ReceiveTimeout = (int)IdleTimeout.TotalMilliseconds
                };
            }
            catch (Exception e)
            {
                DidClose(e);
                return;
            }

            try
            {
                Client.Client.DualMode = true;
            }
            catch (ArgumentException)
            {
                Console.WriteLine("IPv4/IPv6 dual mode not supported on this device, falling back to IPv4");
                Client = new TcpClient(AddressFamily.InterNetwork)
                {
                    SendTimeout = (int)IdleTimeout.TotalMilliseconds,
                    ReceiveTimeout = (int)IdleTimeout.TotalMilliseconds
                };
            }

            // STEP 2: Open the socket connection to the remote host
            var cts = new CancellationTokenSource(ConnectTimeout);
            var tok = cts.Token;

            try
            {
                await Client.ConnectAsync(_logic.UrlRequest.Host, _logic.UrlRequest.Port).ContinueWith(async t =>
                {
                    if (!NetworkTaskSuccessful(t))
                    {
                        return;
                    }
                    await StartInternal();//_queue.DispatchAsync(StartInternal);
                }, tok);
            }
            catch (Exception e)
            {
                // Yes, unfortunately exceptions can either be thrown here or in the task...
                DidClose(e);
            }

            var cancelCallback = default(CancellationTokenRegistration);
            cancelCallback = tok.Register(() =>
            {
                if (Client != null && !Client.Connected)
                {
                    // TODO: Should this be transient?
                    DidClose(new OperationCanceledException());
                }

                cancelCallback.Dispose();
                cts.Dispose();
            });
        }

        #endregion

        #region Private Methods

        private static string Base64Digest(string input)
        {
            var data = Encoding.ASCII.GetBytes(input);
            var engine = SHA1.Create();// ?? throw new RuntimeException("Failed to create SHA1 instance");
            var hashed = engine.ComputeHash(data);
            return Convert.ToBase64String(hashed);
        }

        private static bool CheckHeader(HttpMessageParser parser, string key, string expectedValue, bool caseSens)
        {
            string value = null;
            if (parser.Headers?.TryGetValue(key, out value) != true)
            {
                return false;
            }

            var comparison = caseSens ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase;
            return value?.Equals(expectedValue, comparison) == true;
        }

        private void DidClose(C4WebSocketCloseCode closeCode, string reason)
        {
            if (closeCode == C4WebSocketCloseCode.WebSocketCloseNormal)
            {
                DidClose(null);
                return;
            }

            ResetConnections();

            if (_closed)
            {
                Console.WriteLine("Double close detected, ignoring...");
                return;
            }

            _closed = true;
        }

        private void DidClose(Exception e)
        {
            ResetConnections();
            if (e != null && !(e is ObjectDisposedException) && !(e.InnerException is ObjectDisposedException))
            {
                Console.WriteLine("web socket closed with error :{e.Message}");
                // Log.To.Sync.I(Tag, $"WebSocket CLOSED WITH ERROR: {e}");
            }
            else
            {
                Console.WriteLine("WebSocket CLOSED}"); 
                // Log.To.Sync.I(Tag, "WebSocket CLOSED");
            }

            if (_closed)
            {
                //Log.To.Sync.W(Tag, "Double close detected, ignoring...");
                return;
            }
            _closed = true;
        }

        private async Task HandleHTTPResponse()
        {
            // STEP 6: Read and parse the HTTP response
            try
            {
                using (var streamReader = new StreamReader(NetworkStream, Encoding.ASCII, false, 5, true))
                {
                    var parser = new HttpMessageParser(await streamReader.ReadLineAsync().ConfigureAwait(false));
                    while (true)
                    {

                        var line = await streamReader.ReadLineAsync().ConfigureAwait(false);
                        if (String.IsNullOrEmpty(line))
                        {
                            break;
                        }

                        parser.Append(line);

                    }

                    ReceivedHttpResponse(parser);
                }
            }
            catch (Exception e)
            {
                //Log.To.Sync.I(Tag, "Error reading HTTP response of websocket handshake", e);
                DidClose(e);
            }
        }

        private bool NetworkTaskSuccessful(Task t)
        {
            if (t.IsCanceled)
            {
                DidClose(new SocketException((int)SocketError.TimedOut));
                return false;
            }

            if (t.Exception != null)
            {
                DidClose(t.Exception);
                return false;
            }

            return true;
        }

        private async Task OnSocketReady()
        {
            //STEP 5: Send the HTTP request to start the WebSocket upgrade
            var httpData = _logic.HTTPRequestData();
            var cts = new CancellationTokenSource();
            cts.CancelAfter(IdleTimeout);
            if (NetworkStream == null)
            {
                //Log.To.Sync.E(Tag, "Socket reported ready, but no network stream available!");
                DidClose(C4WebSocketCloseCode.WebSocketCloseAbnormal, "Unexpected error in client logic");
                return;
            }

            NetworkStream.ReadTimeout = (int)IdleTimeout.TotalMilliseconds;
            NetworkStream.WriteTimeout = (int)IdleTimeout.TotalMilliseconds;
            await NetworkStream.WriteAsync(httpData, 0, httpData.Length, cts.Token).ContinueWith(async t =>
            {
                if (!NetworkTaskSuccessful(t))
                {
                    return;
                }
                await HandleHTTPResponse();
            }, cts.Token);
        }

        private void ReceivedHttpResponse(HttpMessageParser parser)
        {
            // STEP 7: Determine if the HTTP response was a success
            _logic.ReceivedResponse(parser);
            var httpStatus = _logic.HttpStatus;

            if (_logic.ShouldRetry)
            {
                // Usually authentication needed, or a redirect
                ResetConnections();
                Start();
                return;
            }
            var dict = parser.Headers?.ToDictionary(x => x.Key, x => (object)x.Value) ?? new Dictionary<string, object>();

            // Success is a 101 response, anything else is not good
            if (_logic.Error != null)
            {
                DidClose(_logic.Error);
            }
            else if (httpStatus != 101)
            {
                var closeCode = C4WebSocketCloseCode.WebSocketClosePolicyError;
                if (httpStatus >= 300 && httpStatus < 1000)
                {
                    closeCode = (C4WebSocketCloseCode)httpStatus;
                }

                var reason = parser.Reason;
                DidClose(closeCode, reason);
            }
            else if (!CheckHeader(parser, "Connection", "Upgrade", false))
            {
                DidClose(C4WebSocketCloseCode.WebSocketCloseProtocolError, "Invalid 'Connection' header");
            }
            else if (!CheckHeader(parser, "Upgrade", "websocket", false))
            {
                DidClose(C4WebSocketCloseCode.WebSocketCloseProtocolError, "Invalid 'Upgrade' header");
            }
            else if (!CheckHeader(parser, "Sec-WebSocket-Accept", _expectedAcceptHeader, true))
            {
                DidClose(C4WebSocketCloseCode.WebSocketCloseProtocolError, "Invalid 'Sec-WebSocket-Accept' header");
            }
            else
            {
                ConnectStatusUpdated?.Invoke(this, true);
                //Connected();
            }
        }

        private void ResetConnections()
        {
            Client?.Dispose();
            Client = null;
            NetworkStream?.Dispose();
            NetworkStream = null;
            _readWriteCancellationTokenSource?.Cancel();
            _readWriteCancellationTokenSource?.Dispose();
            _readWriteCancellationTokenSource = null;
            _receivePause?.Dispose();
            _receivePause = null;
            _writeQueue?.CompleteAdding();
            var count = 0;
            while (count++ < 5 && _writeQueue != null && !_writeQueue.IsCompleted)
            {
                Thread.Sleep(500);
            }

            if (_writeQueue != null && !_writeQueue.IsCompleted)
            {
                //Log.To.Sync.W(Tag, "Timed out waiting for _writeQueue to finish, forcing Dispose...");
            }

            _writeQueue?.Dispose();
            _writeQueue = null;
        }

        private async Task StartInternal()
        {
            // STEP 3: Create the WebSocket Upgrade HTTP request
            var rng = RandomNumberGenerator.Create();
            var nonceBytes = new byte[16];
            rng.GetBytes(nonceBytes);
            var nonceKey = Convert.ToBase64String(nonceBytes);
            _expectedAcceptHeader = Base64Digest(String.Concat(nonceKey, "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"));

            // These ones should be overwritten.  The user has no business setting them.
            _logic["Connection"] = "Upgrade";
            _logic["Upgrade"] = "websocket";
            _logic["Sec-WebSocket-Version"] = "13";
            _logic["Sec-WebSocket-Key"] = nonceKey;
            _logic["Sec-WebSocket-Protocol"] = "BLIP_3+CBMobile_2";

            if (_logic.UseTls)
            {
                var baseStream = Client?.GetStream();
                if (baseStream == null)
                {
                    //Log.To.Sync.W(Tag, "Failed to get network stream (already closed?).  Aborting start...");
                    DidClose(C4WebSocketCloseCode.WebSocketCloseAbnormal, "Unexpected error in client logic");
                    return;
                }
            }
            else
            {
                NetworkStream = Client?.GetStream();
                await OnSocketReady();
            }
        }
        #endregion
    }
}