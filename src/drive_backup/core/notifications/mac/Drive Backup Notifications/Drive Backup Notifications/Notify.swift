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
    
    @Flag(name: .shortAndLong, help: "Show the notification.")
    var show = false
    
    @Flag(name: .shortAndLong, help: "Print out the notification.")
    var verbose = false
    
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
        
        if self.verbose {
            print("Drive Backup Notification:\n\n\(self.title)\n\(self.body)\n")
        }
        
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        
        if self.show {
            try? await center.add(request)
        }else if self.verbose {
            print("Not showing notification (--show not present).")
        }
    }
}
