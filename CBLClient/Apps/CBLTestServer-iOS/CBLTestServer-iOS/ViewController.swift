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

    override func viewDidLoad() {
        super.viewDidLoad()
        server = Server()
    }

    override func didReceiveMemoryWarning() {
        super.didReceiveMemoryWarning()
        // Dispose of any resources that can be recreated.
    }


}

