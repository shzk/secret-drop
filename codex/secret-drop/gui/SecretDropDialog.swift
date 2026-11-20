// Secret Drop Codex — native macOS multi-secret input dialog.
// No telemetry/network, no clipboard, no disk I/O. Secret values are written
// only to this local child process's stdout pipe and never shown in the model.
import AppKit
import Foundation

struct InputField: Decodable {
    let name: String
    let hint: String?
}

struct Prompt: Decodable {
    let fields: [InputField]
    let destination: String
}

private final class FlippedView: NSView {
    override var isFlipped: Bool { true }
}

private func writeResult(_ result: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: result, options: [.fragmentsAllowed]) else {
        return
    }
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
}

private func run() {
    guard let incoming = try? JSONDecoder().decode(
        Prompt.self, from: FileHandle.standardInput.readDataToEndOfFile()
    ), !incoming.fields.isEmpty, incoming.fields.count <= 12,
       incoming.destination.count < 1024,
       incoming.fields.allSatisfy({ !$0.name.isEmpty && $0.name.count <= 128 }) else {
        writeResult(["status": "error"])
        return
    }

    // An accessory view gives the names and per-field hints full font control,
    // unlike macOS's built-in one-line AppleScript hidden-answer dialog.
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)

    let alert = NSAlert()
    alert.alertStyle = .informational
    alert.messageText = "🔐 Secret Drop"
    alert.informativeText =
        "Enter \(incoming.fields.count) secret value(s).\n" +
        "Save to: \(incoming.destination)\n" +
        "The values will not be sent to Codex."
    alert.addButton(withTitle: "Save")
    alert.addButton(withTitle: "Cancel")

    let width: CGFloat = 475
    let rowHeight: CGFloat = 78
    let totalHeight = CGFloat(incoming.fields.count) * rowHeight + 8
    let visibleHeight = min(totalHeight, CGFloat(385))
    let doc = FlippedView(frame: NSRect(x: 0, y: 0, width: width - 22, height: totalHeight))
    var secureFields: [NSSecureTextField] = []

    for (index, entry) in incoming.fields.enumerated() {
        let y = CGFloat(index) * rowHeight + 6
        let name = NSTextField(labelWithString: entry.name)
        name.frame = NSRect(x: 8, y: y, width: width - 50, height: 20)
        name.font = NSFont.monospacedSystemFont(ofSize: 14, weight: .semibold)
        name.textColor = .labelColor
        name.lineBreakMode = .byTruncatingMiddle
        name.toolTip = entry.name
        doc.addSubview(name)

        let secret = NSSecureTextField(frame: NSRect(x: 8, y: y + 25, width: width - 60, height: 29))
        secret.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        secret.placeholderString = (entry.hint?.isEmpty == false)
            ? String(entry.hint!.prefix(120))
            : "Paste a secret for \(entry.name)"
        secret.isBezeled = true
        secret.bezelStyle = .roundedBezel
        secret.usesSingleLineMode = true
        doc.addSubview(secret)
        secureFields.append(secret)
    }

    let scroll = NSScrollView(frame: NSRect(x: 0, y: 0, width: width, height: visibleHeight))
    scroll.documentView = doc
    scroll.hasVerticalScroller = incoming.fields.count > 4
    scroll.drawsBackground = false
    scroll.borderType = .noBorder
    alert.accessoryView = scroll
    app.activate(ignoringOtherApps: true)
    if let first = secureFields.first {
        alert.window.makeFirstResponder(first)
    }

    let selected = alert.runModal()
    guard selected == .alertFirstButtonReturn else {
        writeResult(["status": "cancelled"])
        return
    }
    var values: [String: String] = [:]
    for (idx, entry) in incoming.fields.enumerated() {
        let value = secureFields[idx].stringValue
        if value.isEmpty {
            writeResult(["status": "empty"])
            return
        }
        values[entry.name] = value
    }
    writeResult(["status": "entered", "values": values])
}

run()
