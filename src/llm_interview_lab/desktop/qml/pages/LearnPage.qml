import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette

    function statusText(value) {
        return ({not_started: "未开始", in_progress: "进行中", implemented: "已实现",
                 reviewed: "已审查", retained_d2: "已完成 D+2", retained_d7: "已完成 D+7",
                 mastered: "已掌握"})[value] || value || "未开始"
    }
    function validationText(value) {
        return ({oracle: "Oracle 已验证", field: "已完成实测", stable: "稳定",
                 contract: "契约级实验"})[value] || value || "未验证"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Text { text: "推荐岗位路线"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
                Text { text: "闯关顺序用于学习引导，prerequisites 才是不可绕过的 DAG 硬依赖。"; color: root.palette.muted }
            }
            Item { Layout.fillWidth: true }
            ComboBox { model: ["推荐路线", "全部已就绪题目", "高级依赖图"] }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            clip: true
            model: app.problems
            delegate: LabCard {
                required property var modelData
                width: list.width
                height: 104
                cardColor: root.palette.surface
                borderColor: root.palette.border
                RowLayout {
                    width: parent.width; height: parent.height; spacing: 16
                    Rectangle {
                        width: 38; height: 38; radius: 19
                        color: modelData.status === "mastered" ? Qt.rgba(0.09,0.52,0.36,0.15) : root.palette.surfaceAlt
                        Text { anchors.centerIn: parent; text: modelData.status === "mastered" ? "✓" : (index + 1); color: modelData.status === "mastered" ? root.palette.success : root.palette.muted; font.bold: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: modelData.problem_id + "  " + modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 16 }
                        Text { text: modelData.prerequisites && modelData.prerequisites.length ? "前置：" + modelData.prerequisites.join(", ") : "基础节点"; color: root.palette.muted; font.pixelSize: 12 }
                        RowLayout {
                            StatusPill { text: root.validationText(modelData.validation); tone: ["oracle", "field", "stable"].indexOf(modelData.validation) >= 0 ? root.palette.success : root.palette.warning }
                            StatusPill { text: modelData.retention ? "D+2 / D+7 可用" : "暂无间隔复测"; tone: modelData.retention ? root.palette.accent : root.palette.muted }
                        }
                    }
                    Button { text: modelData.locked ? "未解锁" : (modelData.status === "in_progress" ? "继续" : "打开"); enabled: !modelData.locked && modelData.asset_status !== "planned"; onClicked: app.openProblem(modelData.problem_id) }
                }
            }
        }
    }
}
