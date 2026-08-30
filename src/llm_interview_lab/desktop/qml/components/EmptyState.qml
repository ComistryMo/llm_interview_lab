import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root

    property var theme: null
    property string title: "暂无内容"
    property string description: ""
    property string symbol: "—"

    spacing: theme ? theme.space2 : 8

    LabText {
        theme: root.theme
        Layout.alignment: Qt.AlignHCenter
        text: root.symbol
        tone: "subtle"
        variant: "section"
        strong: true
    }
    LabText {
        theme: root.theme
        Layout.fillWidth: true
        text: root.title
        strong: true
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }
    LabText {
        theme: root.theme
        Layout.fillWidth: true
        visible: text.length > 0
        text: root.description
        tone: "muted"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }
}
