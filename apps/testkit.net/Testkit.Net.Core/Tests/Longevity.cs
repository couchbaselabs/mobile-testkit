using System;
using Couchbase.Lite;
using Couchbase.Lite.Support;
using Couchbase.Lite.Logging;

using Xunit;

namespace Testkit.Net.Core
{
    public class Longevity : IDisposable
    {
        private readonly Database _db;

        public Longevity()
        {
            NetDestkop.Activate();
            _db = new Database("in-for-the-long-haul");
        }

        public void Dispose()
        {
            _db.Delete();
        }

        [Fact]
        public void Run()
        {
            var document = new Document();
            _db.Save(document);

            document.Set("name", "Apples");
            _db.Save(document);
        }
    }
}
