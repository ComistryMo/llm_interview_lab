import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic

// Style-only counterpart for dialogs using the native standardButtons API.
// Keep accept/reject, button roles and caller-owned content unchanged.
Basic.Dialog {
    id: control
    property var theme: null
    padding: 24
    spacing: 16
    font.family: theme ? theme.uiFontFamily : ""
    font.pixelSize: theme ? theme.fontBody : 14
    palette.windowText: theme ? theme.textStrong : "#202020"
    background: Rectangle {
        radius: control.theme ? control.theme.radiusLarge : 12
        color: control.theme ? control.theme.surfaceRaised : "white"
        border.color: control.theme ? control.theme.borderDefault : "#dcdcd7"
    }
    header: LabText {
        theme: control.theme
        text: control.title
        variant: "section"
        strong: true
        visible: text.length > 0
        wrapMode: Text.Wrap
        leftPadding: 24
        rightPadding: 24
        topPadding: 24
    }
    footer: Basic.DialogButtonBox {
        visible: count > 0
        leftPadding: 24
        rightPadding: 24
        bottomPadding: 24
        spacing: 8
        background: null
        delegate: LabButton { theme: control.theme }
    }
    Overlay.modal: Rectangle { color: "#73000000" }
}
