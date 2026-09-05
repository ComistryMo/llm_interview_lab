import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The two interview consent dialogs share content-sized rows. Long material
// titles and enlarged fonts must never occupy a neighbouring row.
ListView {
    id: view
    property var theme: null
    property var labelForPart
    property var detailForPart
    clip: true
    spacing: 0
    ScrollBar.vertical: LabScrollBar { theme: view.theme; policy: ScrollBar.AsNeeded }

    delegate: Item {
        id: entry
        required property var modelData
        objectName: "contextPreviewRow"
        width: view.width - 12
        height: rowContent.implicitHeight + 24
        ColumnLayout {
            id: rowContent
            x: 0
            y: 12
            width: parent.width
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 6
                    Layout.preferredHeight: 6
                    Layout.alignment: Qt.AlignTop
                    Layout.topMargin: 8
                    radius: 3
                    color: view.theme ? view.theme.muted : "#777777"
                }
                LabText {
                    objectName: "contextPreviewLabel"
                    theme: view.theme
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: (entry.modelData.selected ? "发送 · " : "不发送 · ")
                          + view.labelForPart(entry.modelData)
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
            }
            LabText {
                objectName: "contextPreviewDetail"
                theme: view.theme
                Layout.fillWidth: true
                Layout.leftMargin: 16
                visible: text.length > 0
                text: view.detailForPart(entry.modelData)
                      || (entry.modelData.sensitive ? "仅在本次确认后发送" : "")
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                variant: "caption"
                tone: "muted"
            }
        }
        LabDivider {
            theme: view.theme
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }
    }
    LabText {
        anchors.centerIn: parent
        theme: view.theme
        visible: view.count === 0
        text: "没有可发送的上下文"
        tone: "muted"
    }
}
