import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var theme: null
    property string tone: "info"
    property string title: ""
    property string message: ""

    readonly property color toneColor: tone === "danger"
                                       ? (theme ? theme.danger : "#b44249")
                                       : tone === "warning"
                                         ? (theme ? theme.warning : "#8b5b16")
                                         : tone === "success"
                                           ? (theme ? theme.success : "#28745b")
                                           : (theme ? theme.accent : "#315ec7")
    readonly property color fillColor: tone === "danger"
                                       ? (theme ? theme.dangerSoft : "#f8e6e8")
                                       : tone === "warning"
                                         ? (theme ? theme.warningSoft : "#f5ecdb")
                                         : tone === "success"
                                           ? (theme ? theme.successSoft : "#e3f1eb")
                                           : (theme ? theme.accentSoft : "#e7e9fa")

    radius: theme ? theme.radiusMedium : 9
    color: fillColor
    border.color: Qt.rgba(toneColor.r, toneColor.g, toneColor.b, 0.35)
    border.width: 1
    implicitHeight: noticeContent.implicitHeight + (theme ? theme.space3 * 2 : 24)
    Accessible.role: Accessible.AlertMessage
    Accessible.name: (title.length ? title + "。" : "") + message

    RowLayout {
        id: noticeContent
        anchors.fill: parent
        anchors.margins: root.theme ? root.theme.space3 : 12
        spacing: root.theme ? root.theme.space2 : 8

        Rectangle {
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: 6
            width: 7
            height: 7
            radius: 4
            color: root.toneColor
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            LabText {
                theme: root.theme
                Layout.fillWidth: true
                visible: text.length > 0
                text: root.title
                strong: true
                wrapMode: Text.Wrap
            }
            LabText {
                theme: root.theme
                Layout.fillWidth: true
                text: root.message
                tone: "muted"
                wrapMode: Text.Wrap
            }
        }
    }
}
