# TestServer
.NET based server app for Couchbase Lite functional testing

Open the TestServe.sln in Visual Studio. Clean and Rebuild the solution.

# Adding Nuget Packages -
1. Go to TestServer -> Dependencies -> Nuget
2. Right click on Nuget and select "Add Packages"
3. On top left corner of "Add Packages" windows, select "configure sources". Check if below sources are available there, if not add them. Provide a name and add below urls -
      i.  http://mobile.nuget.couchbase.com/nuget/Developer/
      ii. http://mobile.nuget.couchbase.com/nuget/Internal/
4. Select "All Sources" from drop down on top left corner.
5. Locate Couchbase.Lite package and select the Version in bottom right corner to add the package.



