//
//  ReplicatorTcpListener.swift
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

import CouchbaseLiteSwift

enum ListenerState {
    case stopped
    case starting
    case ready
    case stopping
}

/// A lightweight server that accepts incoming replication connections over
/// WebSocket protocol for P2P replication. It also publishes itself on
/// Bonjour so local peers can find it.
public final class ReplicatorTcpListener: NSObject {
    private static let defaultPort: UInt32 = 5000
    
    /// The TCP port that the server will be listener for requsts.
    public var port: UInt32 = ReplicatorTcpListener.defaultPort {
        didSet {
            if port == 0 {
                port = ReplicatorTcpListener.defaultPort
            }
        }
    }
    
    /// The Bonjour service name. Setting it to an empty String will be
    /// mapped to the device's name.
    public var serviceName: String = ""
    
    /// The Bonjour service type.
    public var serviceType = "_cbmobilesync._tcp"
    
    /// An error if occurred.
    public fileprivate(set) var error: Error?
    
    private var service: NetService!
    
    private var listeners: [String: MessageEndpointListener] = [:]
    
    private var connections: [MessageEndpointConnection] = []
    
    fileprivate var thread: Thread?
    
    fileprivate var state = ListenerState.stopped
    
    /// Initializes an instances.
    ///
    /// - Parameter databases: The databases to be served for replication.
    public init(databases: [Database]) {
        for db in databases {
            let config = MessageEndpointListenerConfiguration(
                database: db, protocolType: .byteStream)
            listeners[db.name] = MessageEndpointListener(config: config)
        }
    }
    
    /// The URL at which the listener can be reached from another device.
    /// This URL will only work for _local_ clients, i.e. over the same WiFi LAN
    /// or over Bluetooth.
    public var url: URL {
        var baseHostName = [CChar](repeating: 0, count: Int(NI_MAXHOST))
        gethostname(&baseHostName, Int(NI_MAXHOST))
        var hostname = String(cString: baseHostName)
        #if targetEnvironment(simulator)
        if !hostname.hasSuffix(".local") {
            hostname.append(".local")
        }
        #endif
        var urlc = URLComponents.init()
        urlc.scheme = "ws"
        urlc.host = hostname
        urlc.port = Int(port)
        return urlc.url!
    }
    
    
    @available(iOS 10.0, *)
    /// Starts the listener.
    public func start() {
        if state != .stopped {
            return
        }
        
        state = .starting
        
        Thread.detachNewThread {
            self.doStart()
        }
    }
    
    /// Stops the listener.
    public func stop() {
        if state != .stopped && state != .stopping {
            state = .stopping
            perform(#selector(doStop), on: thread!, with: nil, waitUntilDone: false)
        }
    }
    
    private func doStart() {
        thread = Thread.current
        service = NetService(domain: "local", type: serviceType,
                             name: serviceName, port: Int32(port))
        service.delegate = self
        service.includesPeerToPeer = true
        service.publish(options: .listenForConnections)
        
        RunLoop.current.run()
    }
    
    @objc fileprivate func doStop() {
        for listener in listeners.values {
            listener.closeAll()
        }
        service.stop()
        thread = nil
        state = .stopped
        CFRunLoopStop(RunLoop.current.getCFRunLoop())
    }
    
    func accept(connection: MessageEndpointConnection, database: String) -> Bool {
        guard let listener = listeners[database] else {
            return false
        }
        listener.accept(connection: connection)
        if let index = connections.index(where: { $0 === connection }) {
            connections.remove(at: index)
        }
        return true
    }
    
    @objc fileprivate func acceptConnection(streams: [Any]) {
        let i = streams[0] as! InputStream
        let o = streams[1] as! OutputStream
        let connection = ReplicatorTcpConnection(inputStream: i, outputStream: o, listener: self)
        connections.append(connection)
        connection.open()
    }
}

extension ReplicatorTcpListener: NetServiceDelegate {
    public func netServiceDidPublish(_ sender: NetService) {
        state = .ready
    }
    
    public func netService(_ sender: NetService, didNotPublish errorDict: [String : NSNumber]) {
        if let code = errorDict[NetService.errorCode]?.intValue {
            self.error = NSError.init(domain: "NetService", code: code, userInfo: nil)
        }
        perform(#selector(doStop), on: thread!, with: nil, waitUntilDone: false)
    }
    
    public func netService(_ sender: NetService, didAcceptConnectionWith inputStream: InputStream, outputStream: OutputStream) {
        perform(#selector(acceptConnection(streams:)), on: thread!, with: [inputStream, outputStream], waitUntilDone: false)
    }
}

