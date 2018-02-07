using Android.App;
using Android.Widget;
using Android.OS;

using TestServer.Android;

namespace Couchbase.Lite.Testing.Android
{
    [Activity(Label = "TestServer.Android", MainLauncher = true)]
    public class MainActivity : Activity
    {
        protected override void OnCreate(Bundle savedInstanceState)
        {
            base.OnCreate(savedInstanceState);

            Couchbase.Lite.Support.Droid.Activate(ApplicationContext);
            Couchbase.Lite.Support.Droid.EnableTextLogging();

            var listener = new TestServer();
            listener.Start();

            // Set our view from the "main" layout resource
            SetContentView(Resource.Layout.Main);
        }
    }
}

