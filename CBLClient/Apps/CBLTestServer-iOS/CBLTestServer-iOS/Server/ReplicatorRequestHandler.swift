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



        case "replicator_configureRemoteDbUrl":
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
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

            //let target_converted_url: URL? = URL(string: target_url!)
            if (source_db != nil && target_url != nil) {
                var target: URLEndpoint
                if secure != nil {
                    target = URLEndpoint(withHost: target_url!, secure: secure!)
                } else {
                    target = URLEndpoint(withHost: target_url!, secure: false)
                }
                
                var config = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)

                config.setReplicatorType(replicatorType)
                if continuous != nil {
                    config.setContinuous(continuous!)
                } else {
                    config.setContinuous(false)
                }
                if headers != nil {
                    config.setHeaders(headers)
                }
                config.setAuthenticator(authenticator)
                config.setConflictResolver(conflictResolver!)
                if channels != nil {
                    config.setChannels(channels)
                }
                if documentIDs != nil {
                    config.setDocumentIDs(documentIDs)
                }
                return config
                # return Replicator(withConfig: config.build())
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }


        case "replicator_configureLocalDb":
            let source_db: Database? = args.get(name: "source_db")
            let targetDatabase: Database? = args.get(name: "target_db")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            
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
                var config = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)

                config.setReplicatorType(replicatorType)
                if continuous != nil {
                    config.setContinuous(continuous!)
                } else {
                    config.setContinuous(false)
                }
                if authenticator != nil {
                    config.setAuthenticator(authenticator)
                }
                if headers != nil {
                    config.setHeaders(headers)
                }
                if channels != nil {
                    config.setChannels(channels)
                }
                if conflictResolver != nil {
                    config.setConflictResolver(conflictResolver!)
                }
                if documentIDs != nil {
                    config.setDocumentIDs(documentIDs)
                }
                return config
                
                # return Replicator(withConfig: config.build())
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target DB provided")
            }

        
        case "replicator_create":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return Replicator(withConfig: config!)
            
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

        case "replicator_getActivitylevel":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.activity.hashValue

        case "replicator_getCompleted":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.completed

        case "replicator_getTotoal":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.total

        case "replicator_getError":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return String(describing: replication_obj.status.error)

        case "replicator_addChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener = MyReplicationChangeListener()
            let listenerToken = replication_obj.addChangeListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            return changeListener

        case "replicator_removeChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener : MyReplicationChangeListener = (args.get(name: "changeListener"))!
            replication_obj.removeChangeListener(withToken: changeListener.listenerToken! as! ListenerToken)

        case "replicatorChangeListener_changesCount":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().count

        case "replicatorChangeListener_getChanges":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            // let index: Int = (args.get(name: "index"))!
            return changeListener.getChanges().description
            
        case "replicator_getChannels":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return config?.channels
        
        case "replicator_isContinous":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return config?.continuous
            
        case "replicator_getChannels":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return config?.channels
            
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorRequestHandler.VOID
    }
}

class MyReplicationChangeListener : NSObject  {
    var repl_changes: [ReplicatorChange] = []
    
    var listenerToken: NSObjectProtocol?
    
    lazy var listener: (ReplicatorChange) -> Void = { (change: ReplicatorChange) in
        self.repl_changes.append(change)
    }
    
    public func getChanges() -> [ReplicatorChange] {
        NSLog("GOT repl CHANGES .......\(repl_changes)")
        return repl_changes
    }
}