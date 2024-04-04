//
//  Notify.swift
//  Drive Backup Notifications
//
//  Created by George Waters on 4/4/24.
//

import Foundation
import ArgumentParser
import UserNotifications

struct Notify: AsyncParsableCommand {
    @Flag(name: .shortAndLong, help: "Request authorization to allow notifications and exit.")
    var authorization = false
    
    @Option(name: .shortAndLong, help: "The title to use for the notification.")
    var title = "Drive Backup Notifications"
    
    @Option(name: .shortAndLong, help: "The body to use for the notification.")
    var body = "Notification"
    
    @Option(
        name: .customLong("NSDocumentRevisionsDebugMode", withSingleDash: true),
        help: ArgumentHelp(
            "Xcode automatically adds this option when it runs the app.",
            visibility: .private
        ),
        transform: { $0 == "YES" ? true : false }
    )
    var debugMode: Bool = false
    
    mutating func run() async {
        let center = UNUserNotificationCenter.current()
        
        let _ = try? await center.requestAuthorization(options: [.alert, .sound])
        
        if self.authorization {
            return
        }
        
        let settings = await center.notificationSettings()

        guard (settings.authorizationStatus == .authorized) else { return }
        
        let content = UNMutableNotificationContent()
        content.title = self.title
        content.body = self.body
        content.sound = UNNotificationSound.default
        
        let request = UNNotificationRequest(identifier: "com.geoh2os8295.Drive-Backup-Notifications", content: content, trigger: nil)
        
        try? await center.add(request)
        
        try? await Task.sleep(nanoseconds: 15_000_000_000)
        
        center.removeAllDeliveredNotifications()
    }
}
