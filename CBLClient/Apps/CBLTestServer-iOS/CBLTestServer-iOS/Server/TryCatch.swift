//
//  TryCatch.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 9/17/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation

public func tryCatch(_ block: @escaping () -> Void) throws {
    var exception: Any?
    
    TryCatch.try(block, catch: { (ex) in
        exception = ex
    }, finallyBlock: nil)
    
    if let e = exception {
        throw NSError(domain: "CBLTestServerException", code: 10001, userInfo: ["exception": e])
    }
}
