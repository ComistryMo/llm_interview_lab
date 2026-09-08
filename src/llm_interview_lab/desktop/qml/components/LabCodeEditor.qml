import QtQuick
import QtQuick.Controls.Basic as Basic
import InterviewLab.Editor 1.0

FocusScope {
    id: control
    property var theme: null
    property alias text: input.text
    property alias readOnly: input.readOnly
    property alias preeditText: input.preeditText
    property alias cursorPosition: input.cursorPosition
    property alias font: input.font
    property alias color: input.color
    property alias selectionColor: input.selectionColor
    property alias wrapMode: input.wrapMode
    property alias tabStopDistance: input.tabStopDistance
    readonly property var lineStarts: {
        var result = [0]
        for (var i = 0; i < text.length; ++i)
            if (text[i] === "\n") result.push(i + 1)
        return result
    }
    clip: true
    implicitHeight: 260
    implicitWidth: 400
    onActiveFocusChanged: if (activeFocus) input.forceActiveFocus()

    Rectangle {
        anchors.fill: parent
        color: control.theme ? control.theme.surface : "#ffffff"
        border.color: input.activeFocus && control.theme ? control.theme.focusRing : control.theme ? control.theme.borderSubtle : "#d0d0d0"
        border.width: input.activeFocus ? 2 : 1
        radius: control.theme ? control.theme.radiusMedium : 8
    }
    Rectangle {
        id: gutter
        width: Math.max(44, String(control.lineStarts.length).length * 10 + 20)
        anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.margins: 1
        color: control.theme ? control.theme.surfaceSunken : "#f3f3f3"
        clip: true
        Repeater {
            model: control.lineStarts.length
            Text {
                required property int index
                width: gutter.width - 10
                y: input.positionToRectangle(control.lineStarts[index]).y - viewport.contentItem.contentY
                text: index + 1
                font: input.font
                color: control.theme ? control.theme.subtle : "#777777"
                horizontalAlignment: Text.AlignRight
            }
        }
    }
    Basic.ScrollView {
        id: viewport
        anchors.left: gutter.right; anchors.right: parent.right
        anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.margins: 1
        clip: true
        Basic.TextArea {
            id: input
            objectName: "codeTextInput"
            focus: true
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            padding: 12
            topInset: 0; bottomInset: 0
            color: control.theme ? control.theme.textStrong : "#202020"
            selectionColor: control.theme ? control.theme.accentSoft : "#d9e3f0"
            selectedTextColor: color
            font.family: control.theme ? control.theme.monospaceFontFamily : "monospace"
            font.pixelSize: control.theme ? control.theme.scaledPx(14) : 14
            tabStopDistance: 32
            background: null
            Keys.onPressed: function(event) {
                if (readOnly || event.modifiers & (Qt.ControlModifier | Qt.MetaModifier | Qt.AltModifier)) return
                if (event.key === Qt.Key_Tab) {
                    insert(cursorPosition, "    ")
                    event.accepted = true
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    var line = text.slice(0, cursorPosition).split("\n").pop()
                    var indent = (line.match(/^\s*/) || [""])[0]
                    insert(cursorPosition, "\n" + indent + (line.trim().endsWith(":") ? "    " : ""))
                    event.accepted = true
                }
            }
            PythonCodeHighlighter { document: input.textDocument; dark: control.theme ? control.theme.darkMode : false }
        }
    }
}
