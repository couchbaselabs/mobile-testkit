//
//  Args.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/27/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

public class Args {
    private var _args:[String:Any] = [:];
    
    public func get<T>(name:String) -> T? {
        return _args[name] as Any as? T
    }
    
    public func set(value:Any, forName:String) {
        _args[forName] = value
    }
}
