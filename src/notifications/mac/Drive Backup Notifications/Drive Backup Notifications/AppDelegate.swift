//
//  AppDelegate.swift
//  Drive Backup Notifications
//
//  Created by George Waters on 2/22/24.
//

import Cocoa
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    func notify() async {
        let center = UNUserNotificationCenter.current()
        
        let _ = try? await center.requestAuthorization(options: [.alert, .sound])

        let settings = await center.notificationSettings()

        guard (settings.authorizationStatus == .authorized) else { return }
        
        let content = UNMutableNotificationContent()
        content.title = UserDefaults.standard.string(forKey: "title") ?? "Drive Backup Notifications"
        content.body = UserDefaults.standard.string(forKey: "body") ?? "Notification"
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: "com.geoh2os8295.Drive-Backup-Notifications", content: content, trigger: nil)
        
        try? await center.add(request)
        
        try? await Task.sleep(nanoseconds: 15_000_000_000)
        
        center.removeAllDeliveredNotifications()
    }

    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Insert code here to initialize your application
        Task {
            await notify()
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
