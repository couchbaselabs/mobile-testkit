//
//  Memory.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/30/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

public class Memory {
    private var _memory:[String:Any] = [:];
    private var _address:Int = 0;
    
    public func get<T>(address:String) -> T? {
        return _memory[address] as Any! as? T
    }
    
    public func add(value: Any) -> String {
        _address += 1
        let address = "@\(_address)"
        _memory[address] = value
        return address
    }
    
    public func remove(address: String) {
        _memory[address] = nil
    }
    
    public func flushMemory() {
        _memory.removeAll()
        _address = 0
    }
}
