//
//  ReplicatorRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class ReplicatorRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        /////////////////
        // Replication //
        /////////////////

        case "replicator_create_authenticator":
        let authenticatorType: String! = args.get(name: "authentication_type")

        if authenticatorType == "session" {
            let sessionid: String! = args.get(name: "sessionId")
            let cookiename: String! = args.get(name: "cookieName")
            return SessionAuthenticator(sessionID: sessionid, cookieName: cookiename)
        }
        else {
            let username: String! = args.get(name: "username")
            let password: String! = args.get(name: "password")
            return BasicAuthenticator(username: username!, password: password!)
        }

        case "replicator_configure_remote_db_url":
            let source_db: Database? = args.get(name: "source_db")
            let target_host: String? = args.get(name: "target_host")
            let target_port: Int = args.get(name: "target_port")!
            let target_path: String? = args.get(name: "target_path")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let secure: Bool? = args.get(name: "secure")

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

            if (source_db != nil && target_host != nil && target_port != nil && target_path != nil) {
                var target: URLEndpoint
                if secure != nil {
                    target = URLEndpoint(withHost: target_host!, port: UInt(target_port), path: target_path, secure: secure!)
                } else {
                    target = URLEndpoint(withHost: target_host!, port: UInt(target_port), path: target_path, secure: false)
                }
                
                let config = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)

                config.setReplicatorType(replicatorType)
                if continuous != nil {
                    config.setContinuous(continuous!)
                } else {
                    config.setContinuous(false)
                }

                if authenticator != nil {
                    config.setAuthenticator(authenticator)
                }
                
                if conflictResolver != nil {
                    config.setConflictResolver(conflictResolver!)
                }

                if channels != nil {
                    config.setChannels(channels)
                }

                if documentIDs != nil {
                    config.setDocumentIDs(documentIDs)
                }
                return Replicator(withConfig: config.build())
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }


        case "replicator_configure_local_db":
            let source_db: Database? = args.get(name: "source_db")
            let targetDatabase: Database? = args.get(name: "targetDatabase")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")

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

            if (source_db != nil && targetDatabase != nil) {
                let target = DatabaseEndpoint(withDatabase: targetDatabase!)
                let config = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)

                config.setReplicatorType(replicatorType)
                if continuous != nil {
                    config.setContinuous(continuous!)
                } else {
                    config.setContinuous(false)
                }

                if conflictResolver != nil {
                    config.setConflictResolver(conflictResolver!)
                }

                if documentIDs != nil {
                    config.setDocumentIDs(documentIDs)
                }
                
                return Replicator(withConfig: config.build())
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target db provided")
            }

        case "replicator_start":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.start()

        case "replicator_stop":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.stop()

        case "replicator_status":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let value = replication_obj.status.stringify()
            print("displaying replication status \(value)")
            return value

        case "replicator_config":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.config

        case "replicator_get_activitylevel":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return String(replication_obj.status.activity.hashValue)

        case "replicator_get_completed":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.completed

        case "replicator_get_totoal":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.total

        case "replicator_get_error":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            print("repl object error is \(replication_obj.status.error!)")
            return replication_obj.status.error

        case "replicator_addChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener = MyReplicationChangeListener()
            let listenerToken = replication_obj.addChangeListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            return changeListener

        case "replicator_removeChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener : MyReplicationChangeListener = (args.get(name: "changeListener"))!
            replication_obj.removeChangeListener(withToken: changeListener.listenerToken!)

        case "replicatorChangeListener_changesCount":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().count

        case "replicatorChangeListener_getChange":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            let index: Int = (args.get(name: "index"))!
            return changeListener.getChanges()[index]

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorRequestHandler.VOID
    }
}

class MyReplicationChangeListener : NSObject  {
    var repl_changes: [ReplicatorChange] = []
    
    var listenerToken: ListenerToken?
    
    lazy var listener: (ReplicatorChange) -> Void = { (change: ReplicatorChange) in
        self.repl_changes.append(change)
    }
    
    public func getChanges() -> [ReplicatorChange] {
        return repl_changes
    }
}
