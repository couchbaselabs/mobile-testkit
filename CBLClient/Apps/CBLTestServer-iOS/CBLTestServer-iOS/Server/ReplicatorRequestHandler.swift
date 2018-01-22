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
        case "replicator_create":
            let config: ReplicatorConfiguration.Builder? = args.get(name: "config")
             //return Replicator(withConfig: config!)
            return Replicator(withConfig: (config?.build())!)
            
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
        
        case "replicator_isContinous":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return config?.continuous
            
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
