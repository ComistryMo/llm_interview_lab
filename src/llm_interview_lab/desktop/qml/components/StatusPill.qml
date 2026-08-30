import QtQuick

Rectangle {
    id: pill
    property string text: "就绪"
    property color tone: "#2563eb"
    Accessible.name: text
    Accessible.role: Accessible.StaticText
    implicitWidth: label.implicitWidth + 32
    implicitHeight: 26
    radius: 13
    color: Qt.rgba(tone.r, tone.g, tone.b, 0.13)
    border.color: Qt.rgba(tone.r, tone.g, tone.b, 0.35)
    border.width: 1

    Row {
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            width: 6
            height: 6
            radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: pill.tone
        }
        Text {
            id: label
            text: pill.text
            color: pill.tone
            font.pixelSize: 12
            font.weight: Font.DemiBold
            font.letterSpacing: 0.1
        }
    }
}
