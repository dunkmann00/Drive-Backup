//
//  main.swift
//  Drive Backup Notifications
//
//  Created by George Waters on 2/22/24.
//

import AppKit

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate

_ = NSApplicationMain(CommandLine.argc, CommandLine.unsafeArgv)
