using Android.App;
using Android.Widget;
using Android.OS;

using TestServer.Android;
using System;
using System.IO;
using Java.Util.Zip;
using Java.IO;

namespace Couchbase.Lite.Testing.Android
{
    [Activity(Label = "TestServer.Android", MainLauncher = true)]
    public class MainActivity : Activity
    {
        protected override void OnCreate(Bundle savedInstanceState)
        {
            base.OnCreate(savedInstanceState);

            Couchbase.Lite.Support.Droid.Activate(ApplicationContext);

            TestServer.FilePathResolver = ResolvePath;
            var listener = new TestServer();
            listener.Start();

            // Set our view from the "main" layout resource
            SetContentView(Resource.Layout.Main);
        }

        private string ResolvePath(string path, bool unzip)
        {
            var tmpDir = ApplicationContext.CacheDir.AbsolutePath;
            var finalPath = Path.Combine(tmpDir, "tmp");

            // Copy zip file out of the app bundle and into a temporary directory
            using (var input = ApplicationContext.Assets.Open(path))
            {
                using (var output = System.IO.File.OpenWrite(finalPath))
                {
                    input.CopyTo(output);
                }
            }

            if (unzip) {
                using (var input = System.IO.File.OpenRead(Path.Combine(tmpDir, "tmp"))) {
                    byte[] buffer = new byte[1024];
                    ZipInputStream zis = new ZipInputStream(input);
                    ZipEntry ze = zis.NextEntry;
                    while (ze != null) {
                        String fileName = ze.Name;
                        Java.IO.File newFile = new Java.IO.File(tmpDir, fileName);
                        if (ze.IsDirectory) {
                            newFile.Mkdirs();
                        } else {
                            new Java.IO.File(newFile.Parent).Mkdirs();
                            FileOutputStream fos = new FileOutputStream(newFile);
                            int len;
                            while ((len = zis.Read(buffer)) > 0) {
                                fos.Write(buffer, 0, len);
                            }

                            fos.Close();
                        }

                        ze = zis.NextEntry;
                    }

                    zis.CloseEntry();
                    zis.Close();
                }

                // Note that the unzipped database needs to have the same name as the zip file
                finalPath = Path.Combine(tmpDir, path.Replace(".zip", "") + "/");
            }


            return finalPath;
        }
    }
}

