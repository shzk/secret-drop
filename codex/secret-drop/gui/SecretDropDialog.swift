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
        "Blank fields will be skipped. Values will not be sent to Codex."
    alert.addButton(withTitle: "Save")
    alert.addButton(withTitle: "Cancel")

    let width: CGFloat = 475
    let rowHeight: CGFloat = 48
    let totalHeight = CGFloat(incoming.fields.count) * rowHeight + 8
    let visibleHeight = min(totalHeight, CGFloat(385))
    let doc = FlippedView(frame: NSRect(x: 0, y: 0, width: width - 22, height: totalHeight))
    let labelX: CGFloat = 8
    let labelColumnWidth: CGFloat = 190
    let inputX: CGFloat = 204
    let inputWidth = width - inputX - 29

    // Burgundy is deliberately independent of the user's macOS accent color.
    let burgundy = NSColor(name: NSColor.Name("SecretDropBurgundy")) { appearance in
        if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
            return NSColor(srgbRed: 0.93, green: 0.52, blue: 0.62, alpha: 1.0)
        }
        return NSColor(srgbRed: 0.52, green: 0.12, blue: 0.24, alpha: 1.0)
    }
    var secureFields: [NSSecureTextField] = []

    for (index, entry) in incoming.fields.enumerated() {
        let y = CGFloat(index) * rowHeight + 6
        let codeFont = NSFont.monospacedSystemFont(ofSize: 13, weight: .semibold)
        let codeWidth = (entry.name as NSString).size(withAttributes: [.font: codeFont]).width
        let name = NSTextField(labelWithString: entry.name)
        name.frame = NSRect(x: labelX, y: y + 3,
                            width: min(codeWidth + 18, labelColumnWidth - 14), height: 27)
        name.font = codeFont
        name.textColor = burgundy
        name.drawsBackground = true
        name.backgroundColor = burgundy.withAlphaComponent(0.09)
        name.wantsLayer = true
        name.layer?.cornerRadius = 5
        name.lineBreakMode = .byTruncatingMiddle
        name.toolTip = entry.name
        doc.addSubview(name)

        // Place each masked value field directly to the RIGHT of its variable.
        let secret = NSSecureTextField(frame: NSRect(x: inputX, y: y + 2,
                                                      width: inputWidth, height: 30))
        secret.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        secret.placeholderString = (entry.hint?.isEmpty == false)
            ? String(entry.hint!.prefix(120))
            : "Secret value (optional)"
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
        // Save only fields that the person actually filled. Blank means "skip".
        // Do not trim a nonempty credential: leading/trailing whitespace may be intentional.
        if !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            values[entry.name] = value
        }
    }
    writeResult(["status": "entered", "values": values])
}

run()
