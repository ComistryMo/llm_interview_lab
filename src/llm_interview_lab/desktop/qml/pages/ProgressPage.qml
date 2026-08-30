import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    contentWidth: width; contentHeight: content.implicitHeight + 50; clip: true
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.palette.muted
            opacity: 0.45
        }
    }

    ColumnLayout {
        id: content
        x: 28; y: 26; width: parent.width - 56; spacing: 16
        Text { text: "看能力证据，不看连续打卡"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text { text: "刷题掌握、间隔复测和模拟面试证据彼此分离，并且可以追溯。"; color: root.palette.muted }
        RowLayout {
            Layout.fillWidth: true; spacing: 14
            Repeater {
                model: [
                    {label:"已掌握题目", value: app.dashboard.mastered_count || 0},
                    {label:"到期复测", value: app.dashboard.due_retention ? app.dashboard.due_retention.length : 0},
                    {label:"待审查题目", value: app.dashboard.due_review ? app.dashboard.due_review.length : 0}
                ]
                delegate: LabCard {
                    required property var modelData
                    Layout.fillWidth: true; Layout.preferredHeight: 132; cardColor: root.palette.surface; borderColor: root.palette.border
                    Text { text: modelData.label; color: root.palette.muted }
                    Text { text: modelData.value; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                }
            }
        }
        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(260, (app.dashboard.role_readiness ? app.dashboard.role_readiness.length : 0) * 58 + 92)
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "按技能域查看岗位准备度"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Text { text: "自评与经过验证的能力证据分开显示。"; color: root.palette.muted; font.pixelSize: 12 }
            Repeater {
                model: app.dashboard.role_readiness || []
                delegate: RowLayout {
                    required property var modelData
                    width: parent.width
                    Text { text: modelData.label; color: root.palette.text; Layout.preferredWidth: 170 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Text { text: "已验证"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 70 }
                            ProgressBar { Layout.fillWidth: true; value: modelData.verified }
                            Text { text: Math.round(modelData.verified * 100) + "%"; color: root.palette.muted; Layout.preferredWidth: 42 }
                        }
                        RowLayout {
                            Text { text: "自评"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 70 }
                            ProgressBar { Layout.fillWidth: true; value: modelData.self_reported }
                            Text { text: Math.round(modelData.self_reported * 100) + "%"; color: root.palette.muted; Layout.preferredWidth: 42 }
                        }
                    }
                }
            }
            Text { visible: !app.dashboard.role_readiness || app.dashboard.role_readiness.length === 0; text: "首次启动时选择目标岗位，即可生成这个本地视图。"; color: root.palette.muted }
        }
        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 140; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "如何理解"; color: root.palette.text; font.bold: true }
            Text { width: parent.width; text: "岗位准备度只是在现有证据上计算的本地规划指标，不是 Offer 概率、录用决定，也不能代替真实面试。"; color: root.palette.muted; wrapMode: Text.Wrap }
        }
    }
}
