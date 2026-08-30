import QtQuick

Rectangle {
    id: pill

    property var theme: null
    // Compatibility surface used throughout existing pages.
    property string text: "就绪"
    property color tone: theme ? theme.accent : "#2563eb"

    property string style: "soft"
    property bool showDot: true
    property bool compact: false
    property bool busy: false

    readonly property color labelColor: style === "solid"
                                        ? (theme ? theme.accentForeground : "#ffffff") : tone
    readonly property color fillColor: style === "solid" ? tone
                                       : style === "outline" ? "transparent"
                                       : Qt.rgba(tone.r, tone.g, tone.b,
                                                 theme && theme.darkMode ? 0.18 : 0.11)

    Accessible.name: text
    Accessible.role: Accessible.StaticText
    implicitWidth: contentRow.implicitWidth + (compact ? 16 : 22)
    implicitHeight: compact ? 22 : 26
    radius: height / 2
    color: fillColor
    border.color: style === "solid" ? tone
                  : Qt.rgba(tone.r, tone.g, tone.b,
                            theme && theme.darkMode ? 0.52 : 0.34)
    border.width: 1

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: compact ? 5 : 6

        LabBusyIndicator {
            anchors.verticalCenter: parent.verticalCenter
            width: compact ? 10 : 12
            height: width
            strokeWidth: 1.5
            theme: pill.theme
            running: pill.busy
            indicatorColor: pill.labelColor
        }

        Rectangle {
            visible: pill.showDot && !pill.busy
            width: compact ? 5 : 6
            height: width
            radius: width / 2
            anchors.verticalCenter: parent.verticalCenter
            color: pill.labelColor
        }

        Text {
            id: label
            text: pill.text
            color: pill.labelColor
            font.pixelSize: pill.theme ? pill.theme.scaledPx(12) : 12
            font.family: pill.theme ? pill.theme.uiFontFamily : ""
            font.weight: Font.DemiBold
            font.letterSpacing: 0.1
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
