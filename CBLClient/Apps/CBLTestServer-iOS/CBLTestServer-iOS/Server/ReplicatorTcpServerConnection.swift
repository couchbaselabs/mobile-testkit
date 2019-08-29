//
//  ReplicatorTcpServerConnection.swift
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
public class ReplicatorTcpServerConnection : ReplicatorTcpConnection {
    fileprivate var request = CFHTTPMessageCreateEmpty(kCFAllocatorDefault, true).takeRetainedValue()
    
    fileprivate var response: CFHTTPMessage?
    
    fileprivate var connected = false
    
    fileprivate weak var listener: ReplicatorTcpListener?
    
    public init(inputStream: InputStream, outputStream: OutputStream, listener: ReplicatorTcpListener) {
        super.init(inputStream: inputStream, outputStream: outputStream)
        self.listener = listener
    }
    
    public override func openConnection(completion: @escaping (Bool, MessagingError?) -> Void) {
        connected = true
        
        // Write the websocket upgrade response:
        let data = CFHTTPMessageCopySerializedMessage(response!)!.takeRetainedValue() as Data
        write(data: data) { (success, error) in
            completion(success, error?.toMessagingError(isRecoverable: false))
        }
    }
    
    public override func receive(bytes: UnsafeMutablePointer<UInt8>, count: Int) {
        if connected {
            super.receive(bytes: bytes, count: count)
        } else {
            receivedHTTPRequest(bytes: bytes, count: count)
        }
    }
    
    private func receivedHTTPRequest(bytes: UnsafeMutablePointer<UInt8>, count: Int) {
        if !CFHTTPMessageAppendBytes(request, bytes, count) {
            sendFailureResponse(code: 400, message: "Bad Request")
            return
        }
        
        if CFHTTPMessageIsHeaderComplete(request) {
            performWebSocketHandshake()
        }
    }
    
    private func performWebSocketHandshake() {
        // Validate WebSocket request:
        guard let method: String = CFHTTPMessageCopyRequestMethod(request)?.takeRetainedValue() as String?,
            method == "GET" else {
                sendFailureResponse(code: 400, message: "Bad Request")
                return
        }
        
        guard let header: NSDictionary = CFHTTPMessageCopyAllHeaderFields(request)?.takeRetainedValue(),
            let key = header["Sec-WebSocket-Key"] as? String,
            let prc = header["Sec-WebSocket-Protocol"] as? String else {
                sendFailureResponse(code: 400, message: "Bad Request")
                return
        }
        
        // Validate path:
        let url = CFHTTPMessageCopyRequestURL(request)?.takeRetainedValue() as URL?
        guard let path = url?.path, path.hasPrefix("/") else {
            sendFailureResponse(code: 404, message: "Not Found")
            return
        }
        
        // Prepare response for successly acceptance; the response will be sent in
        let acceptHeader = key.appending("258EAFA5-E914-47DA-95CA-C5AB0DC85B11").sha1Base64()
        response = CFHTTPMessageCreateResponse(kCFAllocatorDefault, 101, "Switching Protocols" as CFString, kCFHTTPVersion1_1).takeRetainedValue()
        CFHTTPMessageSetHeaderFieldValue(response!, "Connection" as CFString, "Upgrade" as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Upgrade" as CFString, "websocket" as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Sec-WebSocket-Accept" as CFString, acceptHeader as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Sec-WebSocket-Protocol" as CFString, prc as CFString);
        
        // Accept the connection per database:
        let begin = path.index(after: path.startIndex)
        var end: String.Index!
        if (path.hasSuffix("/_blipsync")) {
            end = path.index(path.startIndex, offsetBy: path.count - 11)
        } else {
            end = path.index(before: path.endIndex)//path.endIndex
        }

        let db = String(path[begin...end])
        if !(listener!.accept(connection: self, database: db)) {
            response = nil
            sendFailureResponse(code: 404, message: "Not Found")
        }
    }
    
    private func sendFailureResponse(code: Int, message: String) {
        let response = CFHTTPMessageCreateResponse(kCFAllocatorDefault, code, message as CFString, kCFHTTPVersion1_1).takeRetainedValue()
        let data = CFHTTPMessageCopySerializedMessage(response)!.takeRetainedValue() as Data
        write(data: data) { (success, error) in self.closeStream() }
    }
}
