//
//  Memory.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/30/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

// Return IP address of WiFi interface (en0) as a String, or `nil`
func getWiFiAddress() -> String? {
    var address : String?
    
    // Get list of all interfaces on the local machine:
    var ifaddr : UnsafeMutablePointer<ifaddrs>?
    guard getifaddrs(&ifaddr) == 0 else { return nil }
    guard let firstAddr = ifaddr else { return nil }
    
    // For each interface ...
    for ifptr in sequence(first: firstAddr, next: { $0.pointee.ifa_next }) {
        let interface = ifptr.pointee
        
        // Check for IPv4 or IPv6 interface:
        let addrFamily = interface.ifa_addr.pointee.sa_family
        if addrFamily == UInt8(AF_INET) || addrFamily == UInt8(AF_INET6) {
            
            // Check interface name:
            let name = String(cString: interface.ifa_name)
            if  name == "en0" {
                
                // Convert interface address to a human readable string:
                var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                getnameinfo(interface.ifa_addr, socklen_t(interface.ifa_addr.pointee.sa_len),
                            &hostname, socklen_t(hostname.count),
                            nil, socklen_t(0), NI_NUMERICHOST)
                address = String(cString: hostname)
            }
        }
    }
    freeifaddrs(ifaddr)
    
    return address
}

public class Memory {
    private var _memory:[String:Any] = [:];
    private var _address:Int = 0;
    private var _ip = getWiFiAddress()
    
    public func get<T>(address:String) -> T? {
        return _memory[address] as Any! as? T
    }
    
    public func add(value: Any) -> String {
        _address += 1
        var ipaddress = "127.0.0.1"
        if let ip = _ip {
            ipaddress = ip
        }
        let address = "@\(_address)_\(ipaddress)_iOS"
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
