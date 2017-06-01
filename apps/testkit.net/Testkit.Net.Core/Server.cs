using System;
using System.IO;
using System.Net;
using System.Net.Http;
using Newtonsoft.Json;
using System.Threading.Tasks;


namespace Testkit.Net.Core
{
    internal class TestSpec
    {
        [JsonProperty("test")]
        internal string Test { get; set; }
    }

    public class Server
    {
        private readonly HttpListener _listener;

        public Server(int port)
        {
            _listener = new HttpListener(IPAddress.Parse("127.0.0.1"), port);
            _listener.Start();
            Console.WriteLine($"Testkit app listening on port: {port}");
        }

        public async Task Run()
        {
            while (true)
            {
                Console.WriteLine("Waiting for test to run ...");
                // The GetContext method blocks while waiting for a request. 
                HttpListenerContext context = await _listener.GetContextAsync();
                HttpListenerRequest request = context.Request;

                if (request.HttpMethod != "POST")
                {
                    Console.WriteLine($"You must provide the name of a test(s) to run ...");
                    continue;
                }
                string requestBody = "";
                using (var reader = new StreamReader(request.InputStream))
                {
                    requestBody = reader.ReadToEnd();
                }
                var ts = JsonConvert.DeserializeObject<TestSpec>(requestBody);

                // Run test(s)
                int testResult = TestRunner.RunTest(ts.Test);
                string testStatus = testResult == 0 ? "PASS" : "FAIL";

                // Send response status
                HttpListenerResponse response = context.Response;
                // Construct a response.
                await response.WriteContentAsync($"Ran test {ts.Test}: Result: {testStatus}");
            }

        }

        public void Stop()
        {
            _listener.Close();
        }
    }
}
