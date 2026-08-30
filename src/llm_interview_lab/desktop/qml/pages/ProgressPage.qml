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
            Layout.preferredHeight: Math.max(280, (app.dashboard.role_readiness ? app.dashboard.role_readiness.length : 0) * 104 + 108)
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "岗位训练证据"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Text { text: "掌握率只评价做过的内容；覆盖率说明当前证据能代表多少岗位技能。"; color: root.palette.muted; font.pixelSize: 12 }
            Repeater {
                model: app.dashboard.role_readiness || []
                delegate: ColumnLayout {
                    id: readinessEvidence
                    required property var modelData
                    property bool hasMastery: modelData.assessed_mastery !== null && modelData.assessed_mastery !== undefined
                    property bool hasSelfAssessment: modelData.self_assessed_attainment !== null && modelData.self_assessed_attainment !== undefined
                    width: parent.width
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.label; color: root.palette.text; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "证据 " + modelData.assessed_problem_count + " / " + modelData.assessable_problem_count + " 题"
                            color: root.palette.muted; font.pixelSize: 11
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "已评测掌握"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 82 }
                        ProgressBar { visible: readinessEvidence.hasMastery; Layout.fillWidth: true; value: readinessEvidence.hasMastery ? modelData.assessed_mastery : 0 }
                        Text {
                            text: readinessEvidence.hasMastery ? Math.round(modelData.assessed_mastery * 100) + "%" : "尚无评测证据"
                            color: root.palette.muted; Layout.preferredWidth: readinessEvidence.hasMastery ? 52 : 100
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "证据覆盖"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 82 }
                        ProgressBar {
                            visible: modelData.assessment_coverage_ceiling > 0
                            Layout.fillWidth: true
                            value: modelData.assessment_coverage
                        }
                        Text {
                            text: modelData.assessment_coverage_ceiling > 0
                                  ? Math.round(modelData.assessment_coverage * 100) + "% · 当前版本上限 " + Math.round(modelData.assessment_coverage_ceiling * 100) + "%"
                                  : "当前版本尚无可评测资产"
                            color: root.palette.muted
                            Layout.preferredWidth: modelData.assessment_coverage_ceiling > 0 ? 180 : 156
                        }
                    }
                    Text {
                        text: readinessEvidence.hasSelfAssessment
                              ? "自评达成 " + Math.round(modelData.self_assessed_attainment * 100) + "% · 已填写 " + Math.round(modelData.self_assessment_coverage * 100) + "%"
                              : "未填写自评"
                        color: root.palette.muted; font.pixelSize: 11
                    }
                }
            }
            Text { visible: !app.dashboard.role_readiness || app.dashboard.role_readiness.length === 0; text: "首次启动时选择目标岗位，即可生成这个本地视图。"; color: root.palette.muted }
        }
        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 140; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "如何理解"; color: root.palette.text; font.bold: true }
            Text { width: parent.width; text: "覆盖不足表示证据或课程资产不足，不表示你的能力为 0。掌握率只描述已评测部分；这些本地证据不是 Offer 概率、录用决定，也不能代替真实面试。"; color: root.palette.muted; wrapMode: Text.Wrap }
        }
    }
}
