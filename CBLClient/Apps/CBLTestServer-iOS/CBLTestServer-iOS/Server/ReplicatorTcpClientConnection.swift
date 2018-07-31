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

private typealias CompletionHandler = (Bool, Error?) -> Void

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
class ReplicatorTcpClientConnection : NSObject {
    fileprivate let kReadBufferSize = 1024
    
    fileprivate let queue = DispatchQueue(label: "ReplicatorTcpClientConnection")
    
    fileprivate var url: URL!
    
    fileprivate var expectedAcceptHeader: String?
    
    fileprivate var response = CFHTTPMessageCreateEmpty(kCFAllocatorDefault, false).takeRetainedValue()
    
    fileprivate var openCompletion: ((Bool, MessagingError?) -> Void)?
    
    fileprivate let inputStream: InputStream
    
    fileprivate let outputStream: OutputStream
    
    fileprivate var replConnection: ReplicatorConnection!
    
    fileprivate var pendingWrites: [PendingWrite] = []
    
    fileprivate var hasSpace = false
    
    fileprivate var opened = false
    
    init(inputStream: InputStream, outputStream: OutputStream) {
        self.inputStream = inputStream
        self.outputStream = outputStream
    }
    
    convenience init(url: URL) {
        var input: InputStream?
        var output: OutputStream?
        Stream.getStreamsToHost(withName: url.host!, port: url.port!, inputStream: &input, outputStream: &output)
        self.init(inputStream: input!, outputStream: output!)
        self.url = url
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
        inputStream.delegate = nil
        outputStream.delegate = nil
        
        inputStream.close()
        outputStream.close()
    }
}

/// MessageEndpointConnection
extension ReplicatorTcpClientConnection: MessageEndpointConnection {
    public func open(connection: ReplicatorConnection, completion: @escaping (Bool, MessagingError?) -> Void) {
        replConnection = connection
        openCompletion = completion
        open()
        sendWebSocketRequest()
    }
    
    func sendWebSocketRequest() {
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
    
    public func close(error: Error?, completion: @escaping () -> Void) {
        closeStreams()
        // Workaround:
        DispatchQueue.main.async {
            completion()
        }
        
    }
    
    public func send(message: Message, completion: @escaping (Bool, MessagingError?) -> Void) {
        write(data: message.toData()) { (success, error) in
            completion(success, error?.toMessagingError(isRecoverable: false))
        }
    }
    
    fileprivate func connected() {
        opened = true
        openCompletion!(true, nil)
    }
    
    fileprivate func closeConnection(error: Error?) {
        closeStreams()
        replConnection.close(error: error?.toMessagingError(isRecoverable: false))
    }
}

/// StreamDelegate and Read/Write stream
extension ReplicatorTcpClientConnection: StreamDelegate {
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
                receivedHTTPResponseBytes(buffer: buffer, length: length)
            }
        }
        buffer.deallocate()
    }
    
    private func receiveBytes(buffer: UnsafeMutablePointer<UInt8>, length: Int) {
        let data = Data(bytes: buffer, count: length)
        replConnection.receive(messge: Message.fromData(data))
    }
    
    private func receivedHTTPResponseBytes(buffer: UnsafeMutablePointer<UInt8>, length: Int) {
        if !CFHTTPMessageAppendBytes(response, buffer, length) {
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
        connected()
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
