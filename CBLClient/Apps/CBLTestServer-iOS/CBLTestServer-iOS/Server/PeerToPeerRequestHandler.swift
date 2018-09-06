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
            let port: Int = args.get(name:"port")!
            let peerToPeerListener: ReplicatorTcpListener = ReplicatorTcpListener(databases: [database], port: UInt32(port))
            peerToPeerListener.start()
            print("Server is getting started")
            return peerToPeerListener
            
        case "peerToPeer_serverStop":
            let peerToPeerListener: ReplicatorTcpListener = args.get(name:"replicatorTcpListener")!
            peerToPeerListener.stop()
            
        case "peerToPeer_clientStart":
            let host: String = args.get(name:"host")!
            let port: Int = args.get(name:"port")!
            let serverDBName: String = args.get(name:"serverDBName")!
            let database: Database = args.get(name:"database")!
            let continuous: Bool? = args.get(name:"continuous")!
            let replication_type: String? = args.get(name: "replicationType")!
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let endPointType: String = args.get(name: "endPointType")!
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
            
            let url = URL(string: "ws://\(host):\(port)/\(serverDBName)")!
            if endPointType == "URLEndPoint"{
                let urlEndPoint: URLEndpoint = URLEndpoint(url: url)
                replicatorConfig = ReplicatorConfiguration(database: database, target: urlEndPoint)
            }
            else{
                let endpoint = MessageEndpoint(uid: url.absoluteString, target: url, protocolType: ProtocolType.byteStream, delegate: self)
                replicatorConfig = ReplicatorConfiguration(database: database, target: endpoint)
            }
            
            if continuous != nil {
                replicatorConfig?.continuous = continuous!
            } else {
                replicatorConfig?.continuous = false
            }
            if documentIDs != nil {
                replicatorConfig?.documentIDs = documentIDs
            }
            replicatorConfig?.replicatorType = replicatorType
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

