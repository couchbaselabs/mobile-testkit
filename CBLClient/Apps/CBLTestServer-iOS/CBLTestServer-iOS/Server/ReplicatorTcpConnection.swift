//
//  ReplicatorTcpConnection.swift
//  TestTcpP2P
//
//  Created by Pasin Suriyentrakorn on 7/30/18.
//  Copyright © 2018 Pasin Suriyentrakorn. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public typealias CompletionHandler = (Bool, Error?) -> Void

private class PendingWrite {
    let data: Data
    let completion: CompletionHandler?
    var bytesWritten = 0
    
    init(data: Data, completion: CompletionHandler?) {
        self.data = data
        self.completion = completion
    }
}

/// Base ReplicatorTcpConnection that implements MessageEndpointConnection
/// and StreamDelegate. Subclassed by ReplicatorTcpClientConnection and
/// ReplicatorTcpServerConnection.
public class ReplicatorTcpConnection : NSObject {
    fileprivate let kReadBufferSize = 1024
    
    fileprivate let queue = DispatchQueue(label: "ReplicatorTcpConnection")
    
    fileprivate let inputStream: InputStream
    
    fileprivate let outputStream: OutputStream
    
    fileprivate var pendingWrites: [PendingWrite] = []
    
    fileprivate var hasSpace = false
    
    #if COUCHBASE_ENTERPRISE
    fileprivate var replConnection: ReplicatorConnection?
    #endif
    /// Initializes with input and output stream.
    public init(inputStream: InputStream, outputStream: OutputStream) {
        self.inputStream = inputStream
        self.outputStream = outputStream
    }
    
    /// Initializes and open the input and output stream.
    public func openStream() {
        inputStream.delegate = self
        outputStream.delegate = self
        
        CFReadStreamSetDispatchQueue(inputStream, queue)
        CFWriteStreamSetDispatchQueue(outputStream, queue)
        
        inputStream.open()
        outputStream.open()
    }
    
    /// Closes the input and output stream.
    public func closeStream() {
        inputStream.delegate = nil
        outputStream.delegate = nil
        
        inputStream.close()
        outputStream.close()
    }
    
    /// Should be overriden by subclasses to establish remote connection to
    /// to the other peer. This method shouldn't be called directly by the
    /// subclasses.
    public func openConnection(completion: @escaping (Bool, MessagingError?) -> Void) {
        
    }
    
    /// Closes stream and replication connection.
    public func closeConnection(error: Error?) {
        closeStream()
        replConnection!.close(error: error?.toMessagingError(isRecoverable: false))
    }
    
    /// Writes data to the remote peer.
    public func write(data: Data, completion: CompletionHandler?) {
        queue.async {
            self.pendingWrites.append(PendingWrite.init(data: data, completion: completion))
            self.doWrite()
        }
    }
    
    /// Tells the replicator to consume the data.
    public func receive(bytes: UnsafeMutablePointer<UInt8>, count: Int) {
        let data = Data(bytes: bytes, count: count)
        replConnection!.receive(message: Message.fromData(data))
    }
}

/// MessageEndpointConnection

extension ReplicatorTcpConnection: MessageEndpointConnection {
    public func open(connection: ReplicatorConnection, completion: @escaping (Bool, MessagingError?) -> Void) {
        replConnection = connection
        openConnection(completion: completion)
    }
    
    public func close(error: Error?, completion: @escaping () -> Void) {
        closeStream()
        completion()
    }
    
    public func send(message: Message, completion: @escaping (Bool, MessagingError?) -> Void) {
        write(data: message.toData()) { (success, error) in
            completion(success, error?.toMessagingError(isRecoverable: false))
        }
    }
}

/// StreamDelegate

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
            let count = inputStream.read(buffer, maxLength: kReadBufferSize)
            if count <= 0 {
                break
            }
            receive(bytes: buffer, count: count)
        }
        buffer.deallocate()
    }
}

/// Utilities

extension String {
    func sha1Base64() -> String {
        let data = self.data(using: String.Encoding.ascii)!
        var digest = [UInt8](repeating: 0, count:Int(CC_SHA1_DIGEST_LENGTH))
        data.withUnsafeBytes { _ = CC_SHA1($0, CC_LONG(data.count), &digest) }
        return Data(bytes: digest).base64EncodedString()
    }
}

extension Error {
    func toMessagingError(isRecoverable: Bool) -> MessagingError {
        return MessagingError.init(error: self, isRecoverable: isRecoverable)
    }
}
