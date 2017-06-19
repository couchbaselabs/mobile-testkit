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

            try
            {
                _listener.Start();
            }
            catch (Exception e)
            {
                Console.WriteLine(e);
            }

            Console.WriteLine($"Testkit app listening on http://127.0.0.1:{port}");
            Console.WriteLine($"Make a request to http://127.0.0.1:{port}/kill to exit application.");
        }

        public async Task Run()
        {
            while (true)
            {
                Console.WriteLine("Waiting for test to run ...");
                // The GetContext method blocks while waiting for a request. 
                HttpListenerContext context = await _listener.GetContextAsync();
                HttpListenerRequest request = context.Request;

                if (request.Url.AbsolutePath.Replace("/", "") == "kill")
                {
                    break;
                }

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
                HttpListenerResponse response = context.Response;
                if (ts.Test != null && Suites.Names.Contains(ts.Test))
                {
                    int testResult = TestRunner.RunTest(ts.Test);
                    string testStatus = testResult == 0 ? "PASS" : "FAIL";
                    await response.WriteContentAsync($"Ran test {ts.Test}: Result: {testStatus}");
                }
                else
                {
                    response.InternalServerError();
                }
                response.Close();
            }

            Console.WriteLine("Stopping Listener ...");
            _listener.Close();

        }
    }
}
