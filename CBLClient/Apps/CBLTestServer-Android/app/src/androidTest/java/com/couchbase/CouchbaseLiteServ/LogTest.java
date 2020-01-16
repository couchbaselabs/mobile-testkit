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

import java.io.File;

import org.junit.Assert;
import org.junit.Test;

import com.couchbase.mobiletestkit.javacommon.*;
import com.couchbase.mobiletestkit.javacommon.RequestHandler.*;
import com.couchbase.lite.Database;
import com.couchbase.lite.FileLogger;
import com.couchbase.lite.LogDomain;
import com.couchbase.lite.LogLevel;


public class LogTest {

    @Test
    public void testLogZipper() throws Exception {
        RequestHandlerDispatcher.context = CouchbaseLiteServ.getTestServerContext();
        LoggingRequestHandler logRequestHandler = new LoggingRequestHandler();

        final Args args = new Args();
        args.put("directory", "");
        args.put("log_level", "verbose");
        args.put("plain_text", false);
        args.put("max_rotate_count", 1);
        args.put("max_size", 16 * 1024L);
        logRequestHandler.configure(args);

        writeAllLogs("The quick brown fox jumped over the lazy dog");

        RawData data = logRequestHandler.getLogsInZip(args);

        Assert.assertFalse(
            new File(CouchbaseLiteServ.getAppContext().getExternalFilesDir("zip"), "archive.zip").exists());

        Assert.assertNotNull(data);
        Assert.assertEquals("application/zip", data.contentType);
        // I don't know a good way to test the contents of the zip data.  Pick a random number...
        Assert.assertTrue(data.data.length > 20);
    }

    private void writeAllLogs(String message) {
        FileLogger logger = Database.log.getFile();
        logger.log(LogLevel.DEBUG, LogDomain.DATABASE, message);
        logger.log(LogLevel.VERBOSE, LogDomain.DATABASE, message);
        logger.log(LogLevel.INFO, LogDomain.DATABASE, message);
        logger.log(LogLevel.WARNING, LogDomain.DATABASE, message);
        logger.log(LogLevel.ERROR, LogDomain.DATABASE, message);
    }
}

