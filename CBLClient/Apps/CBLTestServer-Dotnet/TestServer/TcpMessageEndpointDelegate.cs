using Couchbase.Lite.P2P;
using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;

namespace Couchbase.Lite.Testing
{
    internal sealed class TcpMessageEndpointDelegate : IMessageEndpointDelegate
    {
        public IMessageEndpointConnection CreateConnection(MessageEndpoint endpoint)
        {
            var host = (Uri)endpoint.Target;
            var tcpMessageConnection = new TcpMessageEndpointConnection(host);
            return tcpMessageConnection;
        }
    }
}
