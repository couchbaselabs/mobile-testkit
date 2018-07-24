//
//  PeerToPeerRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 7/23/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//
import Foundation
import CouchbaseLiteSwift


public class PeerToPeerRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        
        switch method {

            /////////////////////////////
            // Peer to Peer Apis //
            ////////////////////////////
            
        case "peerToPeer_serverStart":
            let database: Database = args.get(name:"database")!
            // let config = MessageEndpointListenerConfiguration(database: database, protocolType: .byteStream)
            // let messageEndPointListener: MessageEndpointListener = MessageEndpointListener(config)
            let peerToPeerListener: ReplicatorTcpListener = ReplicatorTcpListener(databases: [database])
            peerToPeerListener.start()
            print("Server is getting started")
        
        case "peerToPeer_clientStart":
            let host: Database = args.get(name:"host")!
            let port: Database = args.get(name:"port")!
            let serverDBName: Database = args.get(name:"serverDBName")!
            let database: Database = args.get(name:"database")!
            let basicAuthenticator: BasicAuthenticator = BasicAuthenticator(username: "p2pTest", password: "password")
            
            let url: String = "ws://\(host):\(port)/\(serverDBName)"
            let urlEndPoint: URLEndpoint = URLEndpoint(url: URL(string: url)!)
            let replicatorConfig: ReplicatorConfiguration = ReplicatorConfiguration(database: database, target: urlEndPoint)
            replicatorConfig.continuous = true
            replicatorConfig.replicatorType = ReplicatorType.pushAndPull
            replicatorConfig.authenticator = basicAuthenticator
            let replicator: Replicator = Replicator(config: replicatorConfig)
            replicator.start()
            print("Replicator has started")
            let changeListener = MyReplicationChangeListener()
            let listenerToken = replicator.addChangeListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            sleep(60)
            print("Completed ones are :\(replicator.status.progress.completed)")
            print("Total ones are :\(replicator.status.progress.total)")
            print("Error is :\(String(describing: replicator.status.error))")
            
            
         default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return PeerToPeerRequestHandler.VOID
    }
}

