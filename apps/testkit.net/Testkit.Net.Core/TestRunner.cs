﻿using System;
using System.Threading;
using Xunit.Runners;
using System.Reflection;


namespace Testkit.Net.Core
{
    public static class TestRunner
    {

        // Taken from: https://github.com/xunit/samples.xunit/blob/master/TestRunner/Program.cs

        // We use consoleLock because messages can arrive in parallel, so we want to make sure we get
        // consistent console output.
        private static object consoleLock = new object();

        // Use an event to know when we're done
        private static ManualResetEvent finished = new ManualResetEvent(false);

        // Start out assuming success; we'll set this to 1 if we get a failed test
        private static int result = 0;

        public static int RunTest(string name)
        {

            var testAssembly = "bin/Debug/netcoreapp1.1/Testkit.Net.Core.dll";
            using (var runner = AssemblyRunner.WithoutAppDomain(testAssembly))
            {

                var testName = "Testkit.Net.Core.Longevity";

                runner.OnDiscoveryComplete = OnDiscoveryComplete;
                runner.OnExecutionComplete = OnExecutionComplete;
                runner.OnTestFailed = OnTestFailed;
                runner.OnTestSkipped = OnTestSkipped;

                Console.WriteLine("Discovering...");
                runner.Start(testName);

                finished.WaitOne();
                finished.Dispose();

                return result;
            }
        }

        private static void OnDiscoveryComplete(DiscoveryCompleteInfo info)
        {
            lock (consoleLock)
                Console.WriteLine($"Running {info.TestCasesToRun} of {info.TestCasesDiscovered} tests...");
        }

        private static void OnExecutionComplete(ExecutionCompleteInfo info)
        {
            lock (consoleLock)
                Console.WriteLine($"Finished: {info.TotalTests} tests in {Math.Round(info.ExecutionTime, 3)}s ({info.TestsFailed} failed, {info.TestsSkipped} skipped)");

            finished.Set();
        }

        private static void OnTestFailed(TestFailedInfo info)
        {
            lock (consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.Red;

                Console.WriteLine("[FAIL] {0}: {1}", info.TestDisplayName, info.ExceptionMessage);
                if (info.ExceptionStackTrace != null)
                    Console.WriteLine(info.ExceptionStackTrace);

                Console.ResetColor();
            }

            result = 1;
        }

        private static void OnTestSkipped(TestSkippedInfo info)
        {
            lock (consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("[SKIP] {0}: {1}", info.TestDisplayName, info.SkipReason);
                Console.ResetColor();
            }
        }
    }
}