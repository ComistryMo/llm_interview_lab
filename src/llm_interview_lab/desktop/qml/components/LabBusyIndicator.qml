import QtQuick

Item {
    id: control

    property var theme: null
    property bool running: false
    property color indicatorColor: theme ? theme.accent : "#315ec7"
    property real strokeWidth: 2

    implicitWidth: 18
    implicitHeight: 18
    visible: running
    Accessible.role: Accessible.ProgressBar
    Accessible.name: qsTr("正在处理")

    Canvas {
        id: ring
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            var context = getContext("2d")
            context.reset()
            context.lineWidth = control.strokeWidth
            context.lineCap = "round"
            context.strokeStyle = control.indicatorColor
            var inset = control.strokeWidth / 2 + 1
            context.beginPath()
            context.arc(width / 2, height / 2,
                        Math.max(1, Math.min(width, height) / 2 - inset),
                        -Math.PI / 2, Math.PI * 1.15, false)
            context.stroke()
        }

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Connections {
        target: control
        function onIndicatorColorChanged() { ring.requestPaint() }
        function onStrokeWidthChanged() { ring.requestPaint() }
    }

    RotationAnimator on rotation {
        running: control.running && (!control.theme || !control.theme.reducedMotion)
        from: 0
        to: 360
        duration: Math.max(1, control.theme ? control.theme.duration(780) : 780)
        loops: Animation.Infinite
    }
}
