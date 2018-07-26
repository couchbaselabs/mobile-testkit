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
            let host: String = args.get(name:"host")!
            let serverDBName: String = args.get(name:"serverDBName")!
            let database: Database = args.get(name:"database")!
            let continuous: Bool? = args.get(name:"continuous")!
            let authValue: AnyObject? = args.get(name: "authenticator")
            let authenticator: Authenticator? = authValue as? Authenticator
            let replication_type: String? = args.get(name: "replication_type")!
            let endPointType: String = "UrlEndPoint"
            var replicatorConfig: ReplicatorConfiguration? = nil
            var replicatorType = ReplicatorType.pushAndPull
            
            if let type = replication_type {
                if type == "push" {
                    replicatorType = .push
                } else if type == "pull" {
                    replicatorType = .pull
                } else {
                    replicatorType = .pushAndPull
                }
            }
            if endPointType == "MessageEndPoint"{
                let url = URL(string: "ws://\(host):5000/\(serverDBName)")!
                let endpoint = MessageEndpoint(uid: "p2p", target: url, protocolType: ProtocolType.byteStream, delegate: self)
                replicatorConfig = ReplicatorConfiguration(database: database, target: endpoint)
            }
            else{
            let url: String = "ws://\(host):5000/\(serverDBName)"
            let urlEndPoint: URLEndpoint = URLEndpoint(url: URL(string: url)!)
            replicatorConfig = ReplicatorConfiguration(database: database, target: urlEndPoint)
            }
            if continuous != nil {
                replicatorConfig?.continuous = continuous!
            } else {
                replicatorConfig?.continuous = false
            }
            replicatorConfig?.replicatorType = replicatorType
            replicatorConfig?.authenticator = authenticator
            let replicator: Replicator = Replicator(config: replicatorConfig!)
            replicator.start()
            print("Replicator has started")
            return replicator
            
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return PeerToPeerRequestHandler.VOID
    }
}

extension PeerToPeerRequestHandler: MessageEndpointDelegate {
    public func createConnection(endpoint: MessageEndpoint) -> MessageEndpointConnection {
        let url = endpoint.target as! URL
        return ReplicatorTcpClientConnection.init(url: url)
    }
}

