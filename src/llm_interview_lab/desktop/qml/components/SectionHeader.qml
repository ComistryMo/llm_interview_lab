import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root

    property var theme: null
    property string title: ""
    property string description: ""

    spacing: theme ? theme.space1 : 4

    LabText {
        theme: root.theme
        Layout.fillWidth: true
        text: root.title
        variant: "section"
        strong: true
        wrapMode: Text.Wrap
    }
    LabText {
        theme: root.theme
        Layout.fillWidth: true
        visible: text.length > 0
        text: root.description
        tone: "muted"
        wrapMode: Text.Wrap
    }
}
