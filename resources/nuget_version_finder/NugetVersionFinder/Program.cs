using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using McMaster.Extensions.CommandLineUtils;
using NuGet;
using NuGet.Common;
using NuGet.Configuration;
using NuGet.Protocol;
using NuGet.Protocol.Core.Types;
using NuGet.Versioning;

namespace NugetVersionFinder
{
    public class Logger : ILogger
    {
        private readonly bool _enabled;

        public Logger(bool enabled)
        {
            _enabled = enabled;
        }

        public void LogDebug(string data)
        {
            if (_enabled)
                Console.WriteLine($"DEBUG: {data}");
        }

        public void LogVerbose(string data)
        {
            if (_enabled)
                Console.WriteLine($"VERBOSE: {data}");
        }

        public void LogInformation(string data)
        {
            if (_enabled)
                Console.WriteLine($"INFORMATION: {data}");
        }

        public void LogMinimal(string data)
        {
            if (_enabled)
                Console.WriteLine($"MINIMAL: {data}");
        }

        public void LogWarning(string data) => Console.WriteLine($"WARNING: {data}");
        public void LogError(string data) => Console.WriteLine($"ERROR: {data}");
        public void LogErrorSummary(string data) => Console.WriteLine($"ERROR: {data}");

        public void LogInformationSummary(string data)
        {
            if(_enabled)
                Console.WriteLine($"SUMMARY: {data}");
        }
    }

    public enum OutputType
    {

        BuildNumber,
        NugetVersion
    }

    [HelpOption]
    class Program
    {
        [Option(Description = "Enable more verbose output")]
        public bool Verbose { get; set; }

        [Option(Description = "The version to search for")]
        [Required]
        public string SearchVersion { get; set; }

        [Option(Description = "The type of output to write (NugetVersion or BuildNumber [default])")]
        public OutputType OutputType { get; set; }

        static async Task<int> Main(string[] args) => await CommandLineApplication.ExecuteAsync<Program>(args);

        private async Task<int> OnExecute() {
            var searchVersion = new NuGetVersion(SearchVersion);

            var logger = new Logger(Verbose);
            var providers = new List<Lazy<INuGetResourceProvider>>();
            providers.AddRange(Repository.Provider.GetCoreV3());
            var packageSource = new PackageSource("http://mobile.nuget.couchbase.com/nuget/Internal");
            var sourceRespository = new SourceRepository(packageSource, providers);
            var packageMetadataResource = await sourceRespository.GetResourceAsync<PackageSearchResource>();
            var searchMetadata = await packageMetadataResource.SearchAsync("Couchbase.Lite.Enterprise", new SearchFilter(true), 0, 1000, logger, CancellationToken.None);
            var versions = await searchMetadata.First().GetVersionsAsync();

            NuGetVersion maxVersion = new NuGetVersion(0, 0, 0);
            foreach (var version in versions.Select(x => x.Version))
            {
                if(Verbose)
                {
                    Console.ForegroundColor = ConsoleColor.Gray;
                    Console.WriteLine($"Found version {version}...");
                    Console.ResetColor();
                }

                if (searchVersion.Major == version.Major && searchVersion.Minor == version.Minor
                    && searchVersion.Patch == version.Patch && searchVersion.Revision == version.Revision)
                {
                    if(Verbose && version > maxVersion)
                    {
                        Console.ForegroundColor = ConsoleColor.Gray;
                        Console.WriteLine($"New highest version found: {version}...");
                        Console.ResetColor();
                    }
                    maxVersion = version > maxVersion ? version : maxVersion;
                }
            }

            if(maxVersion.Major == 0)
            {
                return 1;
            }

            if(OutputType == OutputType.NugetVersion)
            {
                Console.WriteLine(maxVersion);
            }
            else
            {
                var buildNumber = Int32.Parse(maxVersion.Release.TrimStart('b'));
                Console.WriteLine(buildNumber);
            }

            return 0;
        }
    }
}
