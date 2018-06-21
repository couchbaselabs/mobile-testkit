//
//  peer2peer.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 6/6/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import UIKit
import CouchbaseLiteSwift
import SwiftSocket

public class PeerToPeerRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    // fileprivate var _peerToPeerImplementation:PeerToPeerImplementation?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        
        switch method {
            
            /////////////////////////////
            // Peer to Peer Apis //
            ////////////////////////////
            
        case "peerToPeer_initialize":
            
            let database: Database = args.get(name:"database")!
            let host: String = args.get(name:"host")!
            let port: Int = args.get(name:"port")!
            let continuous: Bool = args.get(name:"continuous")!
            let peerToPeerImplementation = PeerToPeerImplementation.init(database: database, host: host, port: port, continuous: continuous)
            //_peerToPeerImplementation?.peerIntialize(database: database, host: host, port: port, continuous: continuous)
            return peerToPeerImplementation
            
        case "peerToPeer_start":
            let peerToPeerImplementation: PeerToPeerImplementation = args.get(name:"PeerToPeerImplementation")!
            peerToPeerImplementation.start()
            
        /*case "peerToPeer_createConnection":
            _peerToPeerImplementation?.createConnection(endpoint: <#MessageEndpoint#>)
           */
        case "peerToPeer_stopSession":
            let peerToPeerImplementation: PeerToPeerImplementation = args.get(name:"PeerToPeerImplementation")!
            peerToPeerImplementation.stopSession()
            
        case "peerToPeer_stop":
            let peerToPeerImplementation: PeerToPeerImplementation = args.get(name:"PeerToPeerImplementation")!
            peerToPeerImplementation.stop()
            
        case "peerToPeer_connectTCPServer":
            let tcpConnection = TCPConnection.init()
            tcpConnection.connectTCPServer()
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorRequestHandler.VOID
    }
}
class TCPConnection {
    
    func echoService(client: TCPClient) {
        print("Newclient from:\(client.address)[\(client.port)]")
        let d = client.read(1024*10)
        client.send(data: d!)
        client.close()
    }
    
    func connectTCPServer() {
        let server = TCPServer(address: "127.0.0.1", port: 7070)
        switch server.listen() {
        case .success:
            while true {
                if let client = server.accept() {
                    echoService(client: client)
                } else {
                    print("accept error")
                }
            }
        case .failure(let error):
            print(error)
        }
    }
}
            
class PeerToPeerImplementation: MessageEndpointDelegate {
    
    var inputStream: InputStream!
    var outputStream: OutputStream!
    
    var username = ""
    
    let database: Database
    let host: String
    let port: Int
    let continuous: Bool
    var replicator: Replicator?
    
    
    init(database: Database, host: String, port: Int, continuous: Bool) {
        self.database = database
        self.host = host
        self.port = port
        self.continuous = continuous
    }
    
    //1) Set up the input and output streams for message sending
    func start() {
        var readStream: Unmanaged<CFReadStream>?
        var writeStream: Unmanaged<CFWriteStream>?
        
        CFStreamCreatePairWithSocketToHost(kCFAllocatorDefault,
                                           self.host as CFString,
                                           UInt32(self.port),
                                           &readStream,
                                           &writeStream)
        
        inputStream = readStream!.takeRetainedValue()
        outputStream = writeStream!.takeRetainedValue()
        
        inputStream.schedule(in: .main, forMode: .commonModes)
        outputStream.schedule(in: .main, forMode: .commonModes)
        
        inputStream.open()
        outputStream.open()
        
        let endpoint = MessageEndpoint.init(uid: "uid", target: nil, protocolType: .messageStream, delegate: self)
        let config = ReplicatorConfiguration.init(database: database, target: endpoint)
        config.continuous = false
        
        replicator = Replicator.init(config: config)
        replicator!.addChangeListener { (change) in
            // TODO:
        }
        replicator!.start()
    }
    
    func stop() {
        replicator?.stop()
    }
    
    func stopSession() {
        inputStream.close()
        outputStream.close()
    }
    
    
    
    // MessageEndpointDelegate
    
    func createConnection(endpoint: MessageEndpoint) -> MessageEndpointConnection {
        return MultipeerConnection(inputStream: inputStream, outputStream: outputStream)
    }
    
}

class MultipeerConnection: NSObject, MessageEndpointConnection, StreamDelegate {
    let inputStream: InputStream
    let outputStream: OutputStream
    var replConnection: ReplicatorConnection!
    // var peerToPeer: PeerToPeerImplementation
    let maxReadLength = 1024
    
    init(inputStream: InputStream, outputStream: OutputStream) {
        
        self.inputStream = inputStream
        self.outputStream = outputStream
        super.init()
        self.inputStream.delegate = self
        self.outputStream.delegate = self
    }
    
    func receive(data: Data) {
        replConnection.receive(messge: Message.fromData(data))
    }
    
    // Implement MessageEndpointConnection interface
    
    func open(connection: ReplicatorConnection, completion: @escaping (Bool, MessagingError?) -> Void) {
        replConnection = connection
        completion(true, nil)
    }
    
    func close(error: Error?, completion: @escaping () -> Void) {
        inputStream.close()
        outputStream.close()
        completion()
    }
    
    func send(message: Message, completion: @escaping (Bool, MessagingError?) -> Void) {
        let data = message.toData()
        _ = data.withUnsafeBytes { outputStream.write($0, maxLength: data.count)}
    }
    
    //////////TODO --------
    
    // StreamDelegate
    
    func stream(_ aStream: Stream, handle eventCode: Stream.Event) {
        switch eventCode {
        case Stream.Event.hasBytesAvailable:
            print("new message received")
            readAvailableBytes(stream: aStream as! InputStream)
        case Stream.Event.endEncountered:
            replConnection.close(error: nil)
        case Stream.Event.errorOccurred:
            print("Error has occurred")
            replConnection.close(error: nil) // TODO
        case Stream.Event.hasSpaceAvailable:
            print("has space available")
        default:
            print("some other event...")
            break
        }
    }
    
    private func readAvailableBytes(stream: InputStream) {
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: maxReadLength)
        
        while stream.hasBytesAvailable {
            let numberOfBytesRead = inputStream.read(buffer, maxLength: maxReadLength)
            inputStream.read
            if numberOfBytesRead < 0 {
                if let _ = inputStream.streamError {
                    break
                }
            }
            
            // TODO: Revise
            var data = Data()
            data.append(buffer, count: numberOfBytesRead)
            receive(data: data)
        }
    }
}


