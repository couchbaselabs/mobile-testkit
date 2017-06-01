using System;
using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;
using Xunit;

namespace Testkit.Net.Core
{
    public class Longevity
    {
        [Fact]
        public void Success()
        {
            Assert.StartsWith("Hello", "Hello, world!");
        }
    }
}
