//
// Copyright (c) 2019 Couchbase, Inc All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
package com.couchbase.CouchbaseLiteServ;

import android.app.Application;
import android.content.Context;

import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.lite.CouchbaseLite;


public class CouchbaseLiteServ extends Application {
    private static Context appContext;
    private static TestServerContext testServerContext;

    public static Context getAppContext() { return appContext; }

    private static void setContext(Context ctxt) { appContext = ctxt.getApplicationContext(); }

    public static TestServerContext getTestServerContext() {
        return testServerContext;
    }

    private static void setTestServerContext(TestServerContext tsContext) {
        testServerContext = tsContext;
    }

    @Override
    public void onCreate() {
        super.onCreate();

        setContext(this);
        setTestServerContext(new TestServerContext());

        Log.init(new TestServerLogger());
        CouchbaseLite.init(this);
    }
}
