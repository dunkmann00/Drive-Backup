//
//  AppDelegate.swift
//  Drive Backup Notifications
//
//  Created by George Waters on 2/22/24.
//

import Cocoa
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Insert code here to initialize your application
        Task {
            await Notify.main()
            exit(0)
        }
    }

    func applicationWillTerminate(_ aNotification: Notification) {
        // Insert code here to tear down your application
    }

    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }
}
