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
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return Replicator(config: config!)
            
        case "replicator_start":
            let replication_obj: Replicator = args.get(name: "replicator")!
            replication_obj.start()

        case "replicator_stop":
            let replication_obj: Replicator = args.get(name: "replicator")!
            replication_obj.stop()

        case "replicator_status":
            let replication_obj: Replicator = args.get(name: "replicator")!
            let value = replication_obj.status.stringify()
            print("displaying replication status \(value)")
            return value

        case "replicator_config":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return replication_obj.config

        case "replicator_getActivityLevel":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return String(describing: replication_obj.status.activity)

        case "replicator_getCompleted":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return replication_obj.status.progress.completed

        case "replicator_getTotal":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return replication_obj.status.progress.total

        case "replicator_getError":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return String(describing: replication_obj.status.error)

        case "replicator_addReplicatorEventChangeListener":
            let replication_obj: Replicator = args.get(name: "replicator")!
            let changeListener = MyDocumentReplicationListener()
            let listenerToken = replication_obj.addDocumentReplicationListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            return changeListener

        case "replicator_removeReplicatorEventListener":
            let replication_obj: Replicator = args.get(name: "replicator")!
            let changeListener : MyDocumentReplicationListener = (args.get(name: "changeListener"))!
            replication_obj.removeChangeListener(withToken: changeListener.listenerToken!)

        case "replicator_replicatorEventChangesCount":
            let changeListener: MyDocumentReplicationListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().count

        case "replicator_replicatorEventGetChanges":
            let changeListener: MyDocumentReplicationListener = (args.get(name: "changeListener"))!
            let changes: [DocumentReplication] = changeListener.getChanges()
            var event_list: [String] = []
            for change in changes {
                for document in change.documents {
                    let doc_event:String = "doc_id: " + document.id
                    let error:String = ", error_code: " + document.error.debugDescription + ", error_domain: nil"
                    let flags:String = ", flags: " + document.flags.rawValue.description
                    let push:String = ", push: " + change.isPush.description
                    event_list.append(doc_event + error + push + flags)
                }
            }
            return event_list

        case "replicator_addChangeListener":
            let replication_obj: Replicator = args.get(name: "replicator")!
            let changeListener = MyReplicationChangeListener()
            let listenerToken = replication_obj.addChangeListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            return changeListener

        case "replicator_removeChangeListener":
            let replication_obj: Replicator = args.get(name: "replicator")!
            let changeListener : MyReplicationChangeListener = (args.get(name: "changeListener"))!
            replication_obj.removeChangeListener(withToken: changeListener.listenerToken!)

        case "replicator_changeListenerChangesCount":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().count

        case "replicator_changeListenerGetChanges":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().description
        
        case "replicator_isContinous":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return config?.continuous

        case "replicator_resetCheckpoint":
            let replication_obj: Replicator = args.get(name: "replicator")!
            return replication_obj.resetCheckpoint()

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorRequestHandler.VOID
    }
}

public class MyReplicationChangeListener : NSObject  {
    var repl_changes: [ReplicatorChange] = []
    
    var listenerToken: ListenerToken?
    
    lazy var listener: (ReplicatorChange) -> Void = { (change: ReplicatorChange) in
        self.repl_changes.append(change)
    }
    
    public func getChanges() -> [ReplicatorChange] {
        return repl_changes
    }
}

public class MyDocumentReplicationListener : NSObject {
    var document_replication_changes: [DocumentReplication] = []
    
    var listenerToken: ListenerToken?
    
    lazy var listener: (DocumentReplication) -> Void = { (change: DocumentReplication) in
        self.document_replication_changes.append(change)
    }
    
    public func getChanges() -> [DocumentReplication] {
        return document_replication_changes
    }
}
