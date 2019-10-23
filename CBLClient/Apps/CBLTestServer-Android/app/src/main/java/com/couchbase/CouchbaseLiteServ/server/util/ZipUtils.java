/*
  Created by sridevi.saragadam on 11/14/18.
 */

package com.couchbase.CouchbaseLiteServ.server.util;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;


public class ZipUtils {
    private final byte[] buffer = new byte[1024];

    public void unzip(InputStream in, File destination) throws IOException {
        ZipInputStream zis = new ZipInputStream(in);
        ZipEntry ze = zis.getNextEntry();
        while (ze != null) {
            String fileName = ze.getName();
            File newFile = new File(destination, fileName);
            if (ze.isDirectory()) {
                newFile.mkdirs();
            }
            else {
                new File(newFile.getParent()).mkdirs();
                FileOutputStream fos = new FileOutputStream(newFile);
                int len;
                while ((len = zis.read(buffer)) > 0) {
                    fos.write(buffer, 0, len);
                }
                fos.close();
            }
            ze = zis.getNextEntry();
        }
        zis.closeEntry();
        zis.close();
        in.close();
    }

    public boolean deleteRecursive(File fileOrDirectory) {
        if (fileOrDirectory.isDirectory()) {
            for (File child : fileOrDirectory.listFiles()) { deleteRecursive(child); }
        }
        return fileOrDirectory.delete() || !fileOrDirectory.exists();
    }

    public void zipDirectory(String srcDirPath, File zipFile) {
        List<String> zipFiles = new ArrayList<>();

        File srcDir = new File(srcDirPath);
        getFilesList(srcDir, zipFiles);

        int rootPathLen = srcDir.getAbsolutePath().length();

        FileOutputStream fos = null;
        ZipOutputStream zos = null;
        try {
            fos = new FileOutputStream(zipFile);
            zos = new ZipOutputStream(fos);
            for (String filePath : zipFiles) { zipFile(filePath, rootPathLen, zos); }
        }
        catch (IOException e) {
            e.printStackTrace();
        }
        finally {
            if (zos != null) {
                try { zos.close(); } catch (IOException ignore) {}
            }
            if (fos != null) {
                try { fos.close(); } catch (IOException ignore) {}
            }
        }
    }

    public byte[] readFile(File srcFile) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();

        FileInputStream in = null;
        try {
            in = new FileInputStream(srcFile);
            copyFile(in, out);
        }
        catch (IOException e) {
            return null;
        }
        finally {
            if (in != null) {
                try { in.close(); } catch (IOException ignore) {}
            }
        }
        return out.toByteArray();
    }

    private void zipFile(String filePath, int rootPathLen, ZipOutputStream zos) throws IOException {
        FileInputStream fis = null;
        try {
            fis = new FileInputStream(filePath);

            String fn = filePath.substring(rootPathLen + 1, filePath.length());
            android.util.Log.d("###", "adding as '" + fn + "': " + filePath);
            zos.putNextEntry(new ZipEntry(fn));

            copyFile(fis, zos);
        }
        finally {
            if (fis != null) {
                try { zos.closeEntry(); } catch (IOException ignore) {}
                try { fis.close(); } catch (IOException ignore) {}
            }
        }
    }

    private void copyFile(InputStream in, OutputStream out) throws IOException {
        int len;
        while ((len = in.read(buffer)) > 0) { out.write(buffer, 0, len); }
    }

    private void getFilesList(File dir, List<String> files) {
        for (File file : dir.listFiles()) {
            if (file.isDirectory()) { getFilesList(file, files); }
            else { files.add(file.getAbsolutePath()); }
        }
    }
}
