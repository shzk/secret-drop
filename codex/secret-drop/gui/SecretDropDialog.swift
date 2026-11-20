// Secret Drop Codex — compact independent native macOS masked dialog.
// No networking or logging. Only this local child process outputs values to
// the parent MCP process over a private pipe, never into model-visible text.
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

// Draws text inside the capsule with exact geometric centering in BOTH axes.
// Avoids NSTextField's default baseline padding that made labels look too high.
private final class VariableChip: NSView {
    let value: String

    init(value: String, frame: NSRect) {
        self.value = value
        super.init(frame: frame)
        toolTip = value
    }

    required init?(coder: NSCoder) { nil }

    override func draw(_ dirtyRect: NSRect) {
        let dark = effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
        let ink = dark
            ? NSColor(srgbRed: 0.96, green: 0.63, blue: 0.70, alpha: 1)
            : NSColor(srgbRed: 0.50, green: 0.13, blue: 0.24, alpha: 1)
        ink.withAlphaComponent(0.09).setFill()
        NSBezierPath(roundedRect: bounds, xRadius: 5, yRadius: 5).fill()

        let font = NSFont.monospacedSystemFont(ofSize: 12, weight: .semibold)
        let style = NSMutableParagraphStyle()
        style.alignment = .center
        style.lineBreakMode = .byTruncatingMiddle
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font, .foregroundColor: ink, .paragraphStyle: style
        ]
        let size = (value as NSString).size(withAttributes: attrs)
        let height = min(bounds.height, size.height + 1)
        let rect = NSRect(x: 5, y: (bounds.height - height) / 2,
                          width: bounds.width - 10, height: height)
        (value as NSString).draw(in: rect, withAttributes: attrs)
    }
}

private final class DialogActions: NSObject, NSWindowDelegate {
    @objc func save(_ sender: NSButton) {
        NSApp.stopModal(withCode: .OK)
    }

    @objc func cancel(_ sender: NSButton) {
        NSApp.stopModal(withCode: .cancel)
    }

    func windowWillClose(_ notification: Notification) {
        NSApp.stopModal(withCode: .cancel)
    }
}

private func writeResult(_ result: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: result) else { return }
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
}

private func textLabel(_ value: String, font: NSFont, color: NSColor,
                       frame: NSRect) -> NSTextField {
    let label = NSTextField(labelWithString: value)
    label.frame = frame
    label.font = font
    label.textColor = color
    label.lineBreakMode = .byTruncatingMiddle
    label.maximumNumberOfLines = 1
    return label
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

    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)

    let width: CGFloat = 428
    let rowHeight: CGFloat = 36
    let rowsHeight = CGFloat(incoming.fields.count) * rowHeight
    let visibleRowsHeight = min(rowsHeight, CGFloat(288))
    let windowHeight: CGFloat = 123 + visibleRowsHeight

    let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: width, height: windowHeight),
        styleMask: [.titled, .closable],
        backing: .buffered,
        defer: false
    )
    window.title = "Secret Drop"
    window.center()
    let actions = DialogActions()
    window.delegate = actions
    let panel = FlippedView(frame: NSRect(x: 0, y: 0, width: width, height: windowHeight))
    window.contentView = panel

    panel.addSubview(textLabel(
        "Secret Drop",
        font: .systemFont(ofSize: 14, weight: .semibold),
        color: .labelColor, frame: NSRect(x: 16, y: 12, width: width - 32, height: 21)
    ))
    let dest = textLabel(
        "Save to: " + incoming.destination,
        font: .systemFont(ofSize: 11), color: .secondaryLabelColor,
        frame: NSRect(x: 16, y: 35, width: width - 32, height: 16)
    )
    dest.toolTip = incoming.destination
    panel.addSubview(dest)

    let scroll = NSScrollView(frame: NSRect(
        x: 16, y: 59, width: width - 32, height: visibleRowsHeight
    ))
    scroll.hasVerticalScroller = rowsHeight > visibleRowsHeight
    scroll.drawsBackground = false
    scroll.borderType = .noBorder
    let document = FlippedView(frame: NSRect(
        x: 0, y: 0, width: width - 34, height: rowsHeight
    ))
    scroll.documentView = document
    panel.addSubview(scroll)

    let mono = NSFont.monospacedSystemFont(ofSize: 12, weight: .semibold)
    let longest = incoming.fields.map {
        ($0.name as NSString).size(withAttributes: [.font: mono]).width
    }.max() ?? 100
    let chipWidth = min(CGFloat(174), max(CGFloat(108), longest + 20))
    let inputX = chipWidth + 12
    let inputWidth = document.frame.width - inputX - 5
    var secureFields: [NSSecureTextField] = []

    for (index, entry) in incoming.fields.enumerated() {
        let rowY = CGFloat(index) * rowHeight
        document.addSubview(VariableChip(
            value: entry.name,
            frame: NSRect(x: 1, y: rowY + 5, width: chipWidth, height: 26)
        ))
        let field = NSSecureTextField(frame: NSRect(
            x: inputX, y: rowY + 3, width: inputWidth, height: 30
        ))
        field.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        field.placeholderString = entry.hint?.isEmpty == false
            ? String(entry.hint!.prefix(120))
            : "Optional secret"
        field.isBezeled = true
        field.bezelStyle = .roundedBezel
        field.usesSingleLineMode = true
        document.addSubview(field)
        secureFields.append(field)
    }

    panel.addSubview(textLabel(
        "Blank fields are skipped. Values stay outside Codex.",
        font: .systemFont(ofSize: 11), color: .secondaryLabelColor,
        frame: NSRect(x: 16, y: 65 + visibleRowsHeight,
                      width: width - 32, height: 16)
    ))

    let buttonY = 85 + visibleRowsHeight
    let cancel = NSButton(title: "Cancel", target: actions, action: #selector(DialogActions.cancel(_:)))
    cancel.frame = NSRect(x: width - 198, y: buttonY, width: 84, height: 28)
    cancel.keyEquivalent = "\u{1b}"
    panel.addSubview(cancel)

    let save = NSButton(title: "Save", target: actions, action: #selector(DialogActions.save(_:)))
    save.frame = NSRect(x: width - 105, y: buttonY, width: 88, height: 28)
    save.keyEquivalent = "\r"
    panel.addSubview(save)

    app.activate(ignoringOtherApps: true)
    window.makeKeyAndOrderFront(nil)
    if let first = secureFields.first {
        window.makeFirstResponder(first)
    }
    let selected = app.runModal(for: window)
    window.orderOut(nil)
    guard selected == .OK else {
        writeResult(["status": "cancelled"])
        return
    }

    var values: [String: String] = [:]
    for (i, entry) in incoming.fields.enumerated() {
        let value = secureFields[i].stringValue
        // Blank means skip; preserve exact nonblank credentials without trim.
        if !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            values[entry.name] = value
        }
    }
    writeResult(["status": "entered", "values": values])
}

run()
