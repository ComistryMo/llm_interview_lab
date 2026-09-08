import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var colors
    required property var theme
    contentWidth: width; contentHeight: content.implicitHeight + 50; clip: true
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.colors.muted
            opacity: 0.45
        }
    }

    ColumnLayout {
        id: content
        x: (root.width - width) / 2; y: 24; width: Math.min(root.theme.listWidth, parent.width - 48); spacing: 24
        LabText { theme: root.theme; text: "看能力证据，不看连续打卡"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(24); strong: true }
        LabText { theme: root.theme; text: "刷题掌握、间隔复测和模拟面试证据彼此分离，并且可以追溯。"; color: root.colors.muted }
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
                    Layout.fillWidth: true; cardColor: root.theme.canvas; borderColor: "transparent"; padding: 0; theme: root.theme
                    LabText { theme: root.theme; text: modelData.label; color: root.colors.muted }
                    LabText { theme: root.theme; text: modelData.value; color: root.colors.text; font.pixelSize: root.theme.scaledPx(24); strong: true }
                }
            }
        }
        LabCard {
            Layout.fillWidth: true
            cardColor: root.theme.canvas; borderColor: "transparent"; padding: 0; theme: root.theme
            LabText { theme: root.theme; text: "岗位训练证据"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true }
            LabText { theme: root.theme; text: "掌握率只评价做过的内容；覆盖率说明当前证据能代表多少岗位技能。"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12) }
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
                        LabText { theme: root.theme; text: modelData.label; color: root.colors.text; strong: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        Item { Layout.fillWidth: true }
                        LabText { theme: root.theme;
                            text: "证据 " + modelData.assessed_problem_count + " / " + modelData.assessable_problem_count + " 题"
                            color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        LabText { theme: root.theme; text: "已评测掌握"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); Layout.preferredWidth: root.theme.scaledPx(82) }
                        ProgressBar { visible: readinessEvidence.hasMastery; Layout.fillWidth: true; value: readinessEvidence.hasMastery ? modelData.assessed_mastery : 0 }
                        LabText { theme: root.theme;
                            text: readinessEvidence.hasMastery ? Math.round(modelData.assessed_mastery * 100) + "%" : "尚无评测证据"
                            color: root.colors.muted; Layout.preferredWidth: readinessEvidence.hasMastery ? 52 : root.theme.scaledPx(100)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        LabText { theme: root.theme; text: "证据覆盖"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); Layout.preferredWidth: root.theme.scaledPx(82) }
                        ProgressBar {
                            visible: modelData.assessment_coverage_ceiling > 0
                            Layout.fillWidth: true
                            value: modelData.assessment_coverage
                        }
                        LabText { theme: root.theme;
                            text: modelData.assessment_coverage_ceiling > 0
                                  ? Math.round(modelData.assessment_coverage * 100) + "% · 当前版本上限 " + Math.round(modelData.assessment_coverage_ceiling * 100) + "%"
                                  : "当前版本尚无可评测资产"
                            color: root.colors.muted
                            Layout.preferredWidth: root.theme.scaledPx(modelData.assessment_coverage_ceiling > 0 ? 180 : 156); wrapMode: Text.Wrap
                        }
                    }
                    LabText { theme: root.theme;
                        text: "自评填写覆盖 " + Math.round(modelData.self_assessment_coverage * 100) + "% · 不作为面试评分"
                        color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12)
                    }
                }
            }
            LabText { theme: root.theme; visible: !app.dashboard.role_readiness || app.dashboard.role_readiness.length === 0; text: "首次启动时选择目标岗位，即可生成这个本地视图。"; color: root.colors.muted }
        }
        LabCard {
            Layout.fillWidth: true; cardColor: root.theme.canvas; borderColor: "transparent"; padding: 0; theme: root.theme
            LabText { theme: root.theme; text: "如何理解"; color: root.colors.text; strong: true }
            LabText { theme: root.theme; width: parent.width; text: "覆盖不足表示证据或课程资产不足，不表示你的能力为 0。掌握率只描述已评测部分；这些本地证据不是 Offer 概率、录用决定，也不能代替真实面试。"; color: root.colors.muted; wrapMode: Text.Wrap }
        }
    }
}
