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

If Nuget is not available at step 1. Follow these instructions :
1. Go to project -> Dependencies
2. Right click and select "Manage nuget packages"
3. On right side drop down menu for 'package source' . Add above urls.
4. Select 'All' on that drop down 
5. Click on browse tab .
6. Search for 'couchbase.lite.Enterprise'
7. Select NetDesktop package and install


