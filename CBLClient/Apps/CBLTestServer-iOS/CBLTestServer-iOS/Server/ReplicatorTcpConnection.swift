//
//  ReplicatorTcpConnection.swift
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

typealias CompletionHandler = (Bool, Error?) -> Void

private class PendingWrite {
    let data: Data
    let completion: CompletionHandler?
    var bytesWritten = 0
    
    init(data: Data, completion: CompletionHandler?) {
        self.data = data
        self.completion = completion
    }
}

/// MessageEndpointConnection implemenation used by the ReplicatorTcpListener.
class ReplicatorTcpConnection : NSObject {
    fileprivate let kReadBufferSize = 1024
    
    fileprivate let queue = DispatchQueue(label: "ReplicatorTcpConnection")
    
    fileprivate var request = CFHTTPMessageCreateEmpty(kCFAllocatorDefault, true).takeRetainedValue()
    
    fileprivate var response: CFHTTPMessage?
    
    fileprivate let inputStream: InputStream
    
    fileprivate let outputStream: OutputStream
    
    fileprivate weak var listener: ReplicatorTcpListener?
    
    fileprivate var replConnection: ReplicatorConnection!
    
    fileprivate var pendingWrites: [PendingWrite] = []
    
    fileprivate var hasSpace = false
    
    fileprivate var opened = false
    
    init(inputStream: InputStream, outputStream: OutputStream, listener: ReplicatorTcpListener) {
        self.inputStream = inputStream
        self.outputStream = outputStream
        self.listener = listener
    }
    
    func open() {
        inputStream.delegate = self
        outputStream.delegate = self
        
        CFReadStreamSetDispatchQueue(inputStream, queue)
        CFWriteStreamSetDispatchQueue(outputStream, queue)
        
        inputStream.open()
        outputStream.open()
    }
    
    fileprivate func closeStreams() {
        inputStream.close()
        outputStream.close()
    }
}

/// MessageEndpointConnection
extension ReplicatorTcpConnection: MessageEndpointConnection {
    public func open(connection: ReplicatorConnection, completion: @escaping (Bool, MessagingError?) -> Void) {
        opened = true
        replConnection = connection
        
        // Write the websocket upgrade request response:
        let data = CFHTTPMessageCopySerializedMessage(response!)!.takeRetainedValue() as Data
        write(data: data) { (success, error) in
            completion(success, error?.toMessagingError(isRecoverable: false))
        }
    }
    
    public func close(error: Error?, completion: @escaping () -> Void) {
        closeStreams()
        completion()
    }
    
    public func send(message: Message, completion: @escaping (Bool, MessagingError?) -> Void) {
        write(data: message.toData()) { (success, error) in
            completion(success, error?.toMessagingError(isRecoverable: false))
        }
    }
    
    fileprivate func closeConnection(error: Error?) {
        closeStreams()
        replConnection.close(error: error?.toMessagingError(isRecoverable: false))
    }
}

/// StreamDelegate and Read/Write stream
extension ReplicatorTcpConnection: StreamDelegate {
    public func stream(_ aStream: Stream, handle eventCode: Stream.Event) {
        switch eventCode {
        case Stream.Event.hasBytesAvailable:
            doRead()
        case Stream.Event.endEncountered:
            closeConnection(error: nil)
        case Stream.Event.errorOccurred:
            closeConnection(error: aStream.streamError)
        case Stream.Event.hasSpaceAvailable:
            hasSpace = true
            doWrite()
        default:
            break
        }
    }
    
    fileprivate func write(data: Data, completion: CompletionHandler?) {
        queue.async {
            self.pendingWrites.append(PendingWrite.init(data: data, completion: completion))
            self.doWrite()
        }
    }
    
    private func doWrite() {
        if !hasSpace {
            return
        }
        
        while !pendingWrites.isEmpty {
            let w = pendingWrites[0]
            let nBytes = w.data.withUnsafeBytes { outputStream.write(
                $0 + w.bytesWritten, maxLength: w.data.count - w.bytesWritten) }
            if nBytes <= 0 {
                hasSpace = false
                return
            }
            w.bytesWritten = w.bytesWritten + nBytes
            if w.bytesWritten < w.data.count {
                hasSpace = false
                return;
            }
            if let completion = w.completion {
                completion(true, nil)
            }
            pendingWrites.remove(at: 0)
        }
    }
    
    private func doRead() {
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: kReadBufferSize)
        while inputStream.hasBytesAvailable {
            let length = inputStream.read(buffer, maxLength: kReadBufferSize)
            if length <= 0 {
                break
            }
            if opened {
                receiveBytes(buffer: buffer, length: length)
            } else {
                receivedHTTPRequestBytes(buffer: buffer, length: length)
            }
        }
        buffer.deallocate()
    }
    
    private func receiveBytes(buffer: UnsafeMutablePointer<UInt8>, length: Int) {
        let data = Data(bytes: buffer, count: length)
        replConnection.receive(messge: Message.fromData(data))
    }
    
    private func receivedHTTPRequestBytes(buffer: UnsafeMutablePointer<UInt8>, length: Int) {
        if !CFHTTPMessageAppendBytes(request, buffer, length) {
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
            let header: NSDictionary = CFHTTPMessageCopyAllHeaderFields(request)?.takeRetainedValue(),
            let key = header["Sec-WebSocket-Key"] as? String,
            let prc = header["Sec-WebSocket-Protocol"] as? String,
            let version = header["Sec-WebSocket-Version"] as? String,
            method == "GET", prc == "BLIP_3+CBMobile_2", version == "13"
            else {
                sendFailureResponse(code: 400, message: "Bad Request")
                return
        }
        
        // Validate path:
        let url = CFHTTPMessageCopyRequestURL(request)?.takeRetainedValue() as URL?
        guard let path = url?.path, path.hasPrefix("/"), path.hasSuffix("/_blipsync") else {
            sendFailureResponse(code: 404, message: "Not Found")
            return
        }
        
        // Prepare response for successly acceptance; the response will be sent
        // in
        let acceptHeader = key.appending("258EAFA5-E914-47DA-95CA-C5AB0DC85B11").sha1Base64()
        response = CFHTTPMessageCreateResponse(kCFAllocatorDefault, 101, "Upgrade" as CFString, kCFHTTPVersion1_1).takeRetainedValue()
        CFHTTPMessageSetHeaderFieldValue(response!, "Connection" as CFString, "Upgrade" as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Upgrade" as CFString, "websocket" as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Sec-WebSocket-Accept" as CFString, acceptHeader as CFString)
        CFHTTPMessageSetHeaderFieldValue(response!, "Sec-WebSocket-Protocol" as CFString, prc as CFString);
        
        // Accept the connection per database:
        let begin = path.index(after: path.startIndex)
        let end = path.index(path.startIndex, offsetBy: path.count - 11)
        let db = String(path[begin...end])
        if !(listener!.accept(connection: self, database: db)) {
            response = nil
            sendFailureResponse(code: 404, message: "Not Found")
        }
    }
    
    private func sendFailureResponse(code: Int, message: String) {
        let response = CFHTTPMessageCreateResponse(kCFAllocatorDefault, code, message as CFString, kCFHTTPVersion1_1).takeRetainedValue()
        let data = CFHTTPMessageCopySerializedMessage(response)!.takeRetainedValue() as Data
        write(data: data) { (success, error) in self.closeStreams() }
    }
}

private extension String {
    func sha1Base64() -> String {
        let data = self.data(using: String.Encoding.ascii)!
        var digest = [UInt8](repeating: 0, count:Int(CC_SHA1_DIGEST_LENGTH))
        data.withUnsafeBytes { _ = CC_SHA1($0, CC_LONG(data.count), &digest) }
        return Data(bytes: digest).base64EncodedString()
    }
}

private extension Error {
    func toMessagingError(isRecoverable: Bool) -> MessagingError {
        return MessagingError.init(error: self, isRecoverable: isRecoverable)
    }
}

