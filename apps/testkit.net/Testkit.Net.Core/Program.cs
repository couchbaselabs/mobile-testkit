using System;
using System.Threading.Tasks;
using Testkit.Net.Tests;
using Microsoft.Extensions.CommandLineUtils;

namespace Testkit.Net.Core
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

            commandLineApplication.HelpOption("-? | -h | --help");
            commandLineApplication.OnExecute(() =>
            {
                if (!syncGatewayUrl.HasValue() || !runtimeMinutes.HasValue())
                {
                    commandLineApplication.ShowHelp();
                    return 1;
                }

                var scenario = new Longevity(syncGatewayUrl.Value(), Convert.ToDouble(runtimeMinutes.Value()));
                scenario.Run();
                return 0;
            });
            commandLineApplication.Execute(args);

            //var server = new Server(50000);
            //Task.WaitAll(server.Run());

        }
    }
}
