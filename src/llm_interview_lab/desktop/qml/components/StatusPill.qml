import QtQuick

Rectangle {
    property string text: "就绪"
    property color tone: "#2563eb"
    implicitWidth: label.implicitWidth + 18
    implicitHeight: 26
    radius: 13
    color: Qt.rgba(tone.r, tone.g, tone.b, 0.13)
    border.color: Qt.rgba(tone.r, tone.g, tone.b, 0.35)

    Text {
        id: label
        anchors.centerIn: parent
        text: parent.text
        color: parent.tone
        font.pixelSize: 12
        font.weight: Font.DemiBold
    }
}
