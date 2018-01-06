//
//  BlobRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/26/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class BlobRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////
        // Blob //
        //////////
        case "blob_create":
            let contentType: String = args.get(name: "contentType")!
            let content: Data = args.get(name: "content")!
            let stream: InputStream? = args.get(name: "stream")!
            let fileURL: URL? = args.get(name: "fileURL")!
            if (!contentType.isEmpty){
                return Blob(contentType: contentType, data: content)
            } else if (stream != nil){
                return Blob(contentType: contentType, contentStream: stream!)
            } else if (fileURL != nil){
                return try Blob(contentType: contentType, fileURL: fileURL!)
            } else {
                throw RequestHandlerError.IOException("Incorrect parameters provided")
            }
            
        case "blob_digest":
            let blob: Blob = args.get(name: "blob")!
            return blob.digest
        
        case "blob_equals":
            let blob: Blob = args.get(name: "blob")!
            let obj: Any = args.get(name: "obj")!
            return blob.isEqual(obj)
        
        case "blob_hashCode":
            let blob: Blob = args.get(name: "blob")!
            return blob.hashValue

        case "blob_getContent":
            let blob: Blob = args.get(name: "blob")!
            return blob.content

        case "blob_getProperties":
            let blob: Blob = args.get(name: "blob")!
            return blob.properties
        
        case "blob_getContentStream":
            let blob: Blob = args.get(name: "blob")!
            return blob.contentStream
        
        case "blob_getContentType":
            let blob: Blob = args.get(name: "blob")!
            return blob.contentType
        
        case "blob_length":
            let blob: Blob = args.get(name: "blob")!
            return blob.length
           
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
