import QtQuick
import QtQuick.Controls.Basic as Basic
import QtQuick.Controls.impl

Basic.CheckBox {
    id: control
    property var theme: null

    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
    implicitHeight: Math.max(theme ? theme.controlHeight : 40, contentItem.implicitHeight + topPadding + bottomPadding)
    padding: 8
    leftPadding: 30
    rightPadding: 0
    spacing: 10
    hoverEnabled: true
    font.family: theme ? theme.uiFontFamily : ""
    font.pixelSize: theme ? theme.fontBody : 14
    FontMetrics { id: metrics; font: control.font }

    indicator: Rectangle {
        x: 0
        // Follow the actual first text baseline, including centered short
        // labels and wrapped consent text at accessibility font sizes.
        y: Math.round(control.contentItem.y + control.contentItem.baselineOffset
                      - metrics.ascent + (metrics.height - height) / 2)
        width: 20
        height: 20
        radius: 4
        color: control.checked || control.checkState === Qt.PartiallyChecked
               ? (control.theme ? control.theme.accent : "#3c638e")
               : (control.theme ? control.theme.surfaceRaised : "white")
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? (control.theme ? control.theme.focusRing : "#4a6f98")
                                          : control.theme ? control.theme.controlBorder : "#8d8d89"
        opacity: control.enabled ? 1 : 0.5
        ColorImage {
            anchors.centerIn: parent
            width: 16
            height: 16
            visible: control.checked && control.checkState !== Qt.PartiallyChecked
            source: "../../resources/icons/check.svg"
            color: control.theme ? control.theme.accentForeground : "white"
        }
        Rectangle {
            anchors.centerIn: parent
            width: 10
            height: 2
            visible: control.checkState === Qt.PartiallyChecked
            color: control.theme ? control.theme.accentForeground : "white"
        }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.theme ? (control.enabled ? control.theme.textStrong : control.theme.subtle) : "#202020"
        wrapMode: Text.Wrap
        verticalAlignment: Text.AlignVCenter
        lineHeight: lineCount > 1 ? 1.45 : 1.0
    }
}
