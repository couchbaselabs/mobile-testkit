//
//  ViewController.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/24/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import UIKit

class ViewController: UIViewController {
    
    var server: Server!
    var backgroundTask: UIBackgroundTaskIdentifier = UIBackgroundTaskInvalid

    override func viewDidLoad() {
        super.viewDidLoad()
        
        let label = UILabel(frame: CGRect(x: 0, y: 0, width: 360, height: 21))
        label.center = CGPoint(x: 190, y: 285)
        label.textAlignment = .center
        label.text = "CBLTestServer-iOS running @" + getWiFiAddress()! + ":8080"
        self.view.addSubview(label)

        server = Server()
        
        
        NotificationCenter.default.addObserver(
            forName: Notification.Name.UIApplicationDidEnterBackground,
            object: nil, queue: nil) { (note) in
                self.backgroundTask = UIApplication.shared.beginBackgroundTask(
                    expirationHandler: {
                        self.backgroundTask = UIBackgroundTaskInvalid;
                })
        }
        
        NotificationCenter.default.addObserver(
            forName: Notification.Name.UIApplicationWillEnterForeground,
            object: nil, queue: nil) { (note) in
                if self.backgroundTask != UIBackgroundTaskInvalid {
                    UIApplication.shared.endBackgroundTask(self.backgroundTask)
                    self.backgroundTask = UIBackgroundTaskInvalid
                }
        }

    }

    override func didReceiveMemoryWarning() {
        super.didReceiveMemoryWarning()
        // Dispose of any resources that can be recreated.
    }

  
    // Return IP address of WiFi interface (en0) as a String, or `nil`
    // From https://stackoverflow.com/questions/30748480/swift-get-devices-ip-address/30754194#30754194
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
            if addrFamily == UInt8(AF_INET) {
                
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
}

