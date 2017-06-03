using System.Threading.Tasks;
using Testkit.Net.Tests;

namespace Testkit.Net.Core
{
    class Program
    {
        static void Main(string[] args)
        {
            //var server = new Server(50000);
            //Task.WaitAll(server.Run());
            var scenario = new Longevity();
            scenario.Run();
        }
    }
}
