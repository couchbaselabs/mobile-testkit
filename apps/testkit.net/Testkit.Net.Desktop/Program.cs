using System;
using Microsoft.Extensions.CommandLineUtils;

namespace Testkit.Net.Desktop
{
    class Program
    {
        static void Main(string[] args)
        {
            CommandLineApplication commandLineApplication = new CommandLineApplication();
            CommandOption syncGatewayUrl = commandLineApplication.Option(
                "-r | --replication-endpoint <SyncGatewayEndpoint>",
                "The Sync Gateway url/db to replicate with",
                CommandOptionType.SingleValue
            );
            CommandOption runtimeMinutes = commandLineApplication.Option(
                "-t | --runtime-min <NumberOfMinutesToRun>",
                "The number of minutes to run the scenario for",
                CommandOptionType.SingleValue
            );
            CommandOption maxNumberDocs = commandLineApplication.Option(
               "-m | --max-docs <MaxNumberOfDocsToCreate>",
               "Then number of docs the client should create",
               CommandOptionType.SingleValue
           );

            commandLineApplication.HelpOption("-? | -h | --help");
            commandLineApplication.OnExecute(() =>
            {
                if (!syncGatewayUrl.HasValue() || !runtimeMinutes.HasValue() || !maxNumberDocs.HasValue())
                {
                    commandLineApplication.ShowHelp();
                    return 1;
                }

                var scenario = new Longevity(
                    syncGatewayUrl.Value(),
                    Convert.ToDouble(runtimeMinutes.Value()),
                    Convert.ToInt32(maxNumberDocs.Value())
                );
                scenario.Run();
                return 0;
            });
            commandLineApplication.Execute(args);

            // TODO
            // Start a HTTP server to listen for test suites to exectue
            // Partial implementation removed to keep repo clean. To resurrect this work,
            // Checkout ba7ec515f69f56eef5cddd49028ef2297ebd107b
            // https://github.com/couchbaselabs/mobile-testkit/blob/master/apps/testkit.net/Testkit.Net.Core/Server.cs
            // https://github.com/couchbaselabs/mobile-testkit/blob/master/apps/testkit.net/Testkit.Net.Core/TestRunner.cs
            // https://github.com/couchbaselabs/mobile-testkit/blob/master/apps/testkit.net/Testkit.Net.Core/Tests.cs
        }
    }
}
