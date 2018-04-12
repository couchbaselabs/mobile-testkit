//
//  Extensions.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 12/4/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import CouchbaseLiteSwift
extension Replicator.Status {
    func stringify()->String {
        let progressMirror = Mirror(reflecting: self)
        var str = ""
        for (propName, propValue) in progressMirror.children {
            guard let propName = propName else { continue }
            str += "\(propName):\(propValue),"
            
        }
        return str
    }
}
