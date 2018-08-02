//
//  ReplicatorTcpClientConnection.swift
//  CouchbaseLite
//
//  Copyright (c) 2018 Couchbase, Inc. All rights reserved.
//
//  Licensed under the Couchbase License Agreement (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//  https://info.couchbase.com/rs/302-GJY-034/images/2017-10-30_License_Agreement.pdf
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

import Foundation
import CouchbaseLiteSwift

/// MessageEndpointConnection implemenation used by the ReplicatorTcpListener.
public class ReplicatorTcpClientConnection : ReplicatorTcpConnection {
    fileprivate var url: URL!
    
    fileprivate var expectedAcceptHeader: String?
    
    fileprivate var response = CFHTTPMessageCreateEmpty(kCFAllocatorDefault, false).takeRetainedValue()
    
    fileprivate var hasSpace = false
    
    fileprivate var connected = false
    
    fileprivate var openCompletion: ((Bool, MessagingError?) -> Void)?
    
    public init(url: URL) {
        var input: InputStream?
        var output: OutputStream?
        Stream.getStreamsToHost(withName: url.host!, port: url.port!, inputStream: &input, outputStream: &output)
        super.init(inputStream: input!, outputStream: output!)
        self.url = url
    }
    
    public override func openConnection(completion: @escaping (Bool, MessagingError?) -> Void) {
        self.openCompletion = completion
        openStream()
        sendWebSocketRequest()
    }
    
    private func sendWebSocketRequest() {
        var keyBytes: [UInt8] = [UInt8](repeating: 0, count: 16)
        _ = SecRandomCopyBytes(kSecRandomDefault, 16, &keyBytes)
        let key = Data(bytes: keyBytes).base64EncodedString()
        expectedAcceptHeader = key.appending("258EAFA5-E914-47DA-95CA-C5AB0DC85B11").sha1Base64()
        
        var urlComp = URLComponents.init()
        urlComp.scheme = "http"
        urlComp.host = url.host
        urlComp.port = url.port
        urlComp.path = "\(url.path)/_blipsync"
        let syncURL = urlComp.url!
        
        var host = syncURL.host!
        if let port = syncURL.port {
            host = "\(host):\(port)"
        }
        
        let request = CFHTTPMessageCreateRequest(kCFAllocatorDefault, "GET" as CFString, syncURL as CFURL, kCFHTTPVersion1_1).takeRetainedValue()
        CFHTTPMessageSetHeaderFieldValue(request, "Sec-WebSocket-Version" as CFString, "13" as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "Sec-WebSocket-Key" as CFString, key as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "Sec-WebSocket-Protocol" as CFString, "BLIP_3+CBMobile_2" as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "Upgrade" as CFString, "websocket" as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "Connection" as CFString, "Upgrade" as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "User-Agent" as CFString, "CouchbaseLite/2.1 ReplicatorTcpClientConnection" as CFString)
        CFHTTPMessageSetHeaderFieldValue(request, "Host" as CFString, host as CFString)
        
        let data = CFHTTPMessageCopySerializedMessage(request)!.takeRetainedValue() as Data
        write(data: data, completion: nil)
    }
    
    public override func receive(bytes: UnsafeMutablePointer<UInt8>, count: Int) {
        if connected {
            super.receive(bytes: bytes, count: count)
        } else {
            receivedHTTPResponse(bytes: bytes, count: count)
        }
    }
    
    private func receivedHTTPResponse(bytes: UnsafeMutablePointer<UInt8>, count: Int) {
        if !CFHTTPMessageAppendBytes(response, bytes, count) {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        
        if CFHTTPMessageIsHeaderComplete(response) {
            verifyWebSocketRequestResponse()
        }
    }
    
    private func verifyWebSocketRequestResponse() {
        let code = CFHTTPMessageGetResponseStatusCode(response) as Int
        if code != 101 {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        
        guard let header: NSDictionary = CFHTTPMessageCopyAllHeaderFields(response)?.takeRetainedValue() else {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        guard let v1 = header["Connection"] as? String, v1.caseInsensitiveCompare("Upgrade") == .orderedSame else {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        guard let v2 = header["Upgrade"] as? String, v2.caseInsensitiveCompare("websocket") == .orderedSame else {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        guard let v3 = header["Sec-WebSocket-Accept"] as? String, v3 == expectedAcceptHeader! else {
            closeConnection(error: NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            return
        }
        
        // Success:
        connected = true
        openCompletion!(true, nil)
    }
}
