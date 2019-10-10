package com.couchbase.javacommon;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.HashMap;
import java.util.Map;

public class Memory {
    private static String ipAddress = "";
    private final Map<String, Object> _memory = new HashMap<>();
    private int _address = 0;

    public <T> T get(String address) {
        return (T) _memory.get(address);
    }

    public void setIpAddress(String ip){
        Memory.ipAddress = ip;
    }

    public String add(Object value) {
        String address = "@" + (++_address) + "_" + Memory.ipAddress + "_" + RequestHandlerDispatcher.context.getPlatform();
        _memory.put(address, value);
        return address;
    }

    public void remove(String address) {
        _memory.remove(address);
    }

    public Map<String, Object> get_memory_map() {
        return _memory;
    }

    public void flushMemory() {
        _memory.clear();
        _address = 0;
    }

    public String copyFiles(Args args) throws IOException {
        File sourcePath = new File(args.get("source_path").toString());
        File destinationPath = new File(args.get("destination_path").toString());
        try {
            copyFolder(sourcePath, destinationPath);
            return "Copied";
        }
        catch (Exception e) {
            return e.getLocalizedMessage().toString();
        }
    }

    public static void copyFolder(File src, File dest) throws IOException {
        if (src.isDirectory()) {

            if (dest.exists()) {
                deleteRecursive(dest);
            }
            else {
                dest.mkdir();
                System.out.println("Directory copied from " + src + "  to " + dest);
            }

            //list all the directory contents
            String files[] = src.list();

            for (String file : files) {
                //construct the src and dest file structure
                File srcFile = new File(src, file);
                File destFile = new File(dest, file);
                //recursive copy
                copyFolder(srcFile, destFile);
            }
        }
        else {
            //if file, then copy it
            //Use bytes stream to support all file types
            InputStream in = new FileInputStream(src);
            OutputStream out = new FileOutputStream(dest);

            byte[] buffer = new byte[1024];

            int length;
            //copy the file content in bytes
            while ((length = in.read(buffer)) > 0) {
                out.write(buffer, 0, length);
            }

            in.close();
            out.close();
            System.out.println("File copied from " + src + " to " + dest);

        }
        deleteRecursive(src);
    }

    public static void deleteRecursive(File fileOrDirectory) {
        if (fileOrDirectory.isDirectory()) {
            for (File child : fileOrDirectory.listFiles()) { deleteRecursive(child); }
        }

        fileOrDirectory.delete();
    }
}