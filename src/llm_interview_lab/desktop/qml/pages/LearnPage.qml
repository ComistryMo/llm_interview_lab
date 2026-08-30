import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    objectName: "learnPage"
    required property var app
    required property var palette
    property string filterMode: "recommended"
    property string query: ""
    property var filteredProblems: []

    function statusText(value) {
        return ({not_started: "未开始", in_progress: "进行中", implemented: "已实现",
                 reviewed: "已审查", retained_d2: "已完成 D+2", retained_d7: "已完成 D+7",
                 mastered: "已掌握"})[value] || value || "未开始"
    }
    function validationText(value) {
        return ({oracle: "Oracle 已验证", field: "已完成实测", stable: "稳定",
                 contract: "契约级实验"})[value] || value || "未验证"
    }
    function searchable(card) {
        var values = [card.problem_id, card.title].concat(card.skills || [], card.keywords || [])
        return values.join(" ").toLowerCase()
    }
    function emptyMessage() {
        if (root.query.trim().length > 0)
            return "没有匹配“" + root.query.trim() + "”的题目。请换一个标题、技能或 Problem ID。"
        if (root.filterMode === "experimental")
            return "当前没有已登记的实验性题目。"
        if (root.filterMode === "available")
            return "当前没有可直接开始的题目。可能是前置尚未完成，或运行环境暂不可用。"
        return "当前没有新的推荐题。请先完成进行中的任务或到期复测。"
    }
    function refreshList() {
        var source = app.problems || []
        var needle = root.query.trim().toLowerCase()
        var result = []
        for (var i = 0; i < source.length; ++i) {
            var card = source[i]
            var validation = card.validation || "contract"
            var available = !card.locked
                            && card.asset_status !== "planned"
                            && card.environment_available !== false
                            && card.status !== "mastered"
            var matches = !needle || searchable(card).indexOf(needle) >= 0
            var include = false
            if (root.filterMode === "recommended")
                include = available
                          && card.recommendable
                          && card.recommended_rank >= 0
                          && ["oracle", "field", "stable"].indexOf(validation) >= 0
            else if (root.filterMode === "available")
                include = available && ["oracle", "field", "stable"].indexOf(validation) >= 0
            else if (root.filterMode === "experimental")
                include = validation === "contract"
            if (include && matches)
                result.push(card)
        }
        result.sort(function(a, b) {
            var rank = function(card) {
                if (card.status === "in_progress") return 0
                if (card.retention_due) return 1
                if (card.status === "not_started") return 2
                return 3
            }
            var learningOrder = root.filterMode === "recommended"
                              ? (a.recommended_rank - b.recommended_rank) : 0
            return rank(a) - rank(b)
                   || learningOrder
                   || String(a.problem_id).localeCompare(String(b.problem_id))
        })
        root.filteredProblems = result
    }

    Component.onCompleted: root.refreshList()
    Connections {
        target: app
        function onStateChanged() { root.refreshList() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                // Main.qml already owns the page title.  Keep this row focused
                // on the learning context so the shell and page do not repeat
                // the same large heading.
                Text {
                    objectName: "learnRouteContext"
                    text: "按课程前置逐题推进"
                    color: root.palette.text
                    font.pixelSize: 16
                    font.bold: true
                }
                Text { text: "只展示当前真实可用的题目；前置关系由课程 DAG 决定。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            ComboBox {
                id: filter
                objectName: "learnFilter"
                model: ["推荐", "全部可做", "实验性"]
                onCurrentIndexChanged: {
                    root.filterMode = ["recommended", "available", "experimental"][currentIndex]
                    root.refreshList()
                }
            }
            TextField {
                id: search
                objectName: "learnSearch"
                Layout.preferredWidth: 220
                placeholderText: "搜索标题、技能或 ID"
                onTextChanged: { root.query = text; root.refreshList() }
            }
        }

        Text {
            id: resultSummary
            objectName: "learnResultSummary"
            text: ({recommended: "推荐", available: "全部可做", experimental: "实验性"}[root.filterMode] || "当前")
                  + " · " + root.filteredProblems.length + " 道题"
            color: root.palette.muted
            font.pixelSize: 12
            Layout.fillWidth: true
        }
        Text {
            visible: list.count === 0
            objectName: "learnEmptyState"
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root.emptyMessage()
            color: root.palette.muted
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
        }

        ListView {
            id: list
            objectName: "learnProblemList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            clip: true
            model: root.filteredProblems
            footer: Item {
                width: list.width
                height: root.filterMode === "recommended" && list.count > 0 ? 46 : 0
                Text {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: 12
                    text: "完成当前任务后会按课程前置自动解锁下一题；“全部可做”仅展示当前可直接开始的题目。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
            }
            delegate: LabCard {
                required property var modelData
                required property int index
                width: list.width
                height: 112
                cardColor: root.palette.surface
                borderColor: root.palette.border
                RowLayout {
                    width: parent.width; height: parent.height; spacing: 16
                    Rectangle {
                        width: 28; height: 28; radius: 14
                        Layout.alignment: Qt.AlignTop
                        color: modelData.status === "mastered" ? Qt.rgba(0.09,0.52,0.36,0.15) : root.palette.surfaceAlt
                        Text { anchors.centerIn: parent; text: modelData.status === "mastered" ? "✓" : (index + 1); color: modelData.status === "mastered" ? root.palette.success : root.palette.muted; font.pixelSize: 11; font.bold: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 17; wrapMode: Text.Wrap; maximumLineCount: 2; Layout.fillWidth: true }
                        Text { text: modelData.skills && modelData.skills.length ? modelData.skills.slice(0, 3).join(" · ") : " "; color: root.palette.muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: modelData.problem_id || ""; color: root.palette.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                        RowLayout {
                            StatusPill { text: root.statusText(modelData.status); tone: modelData.status === "mastered" ? root.palette.success : root.palette.accent }
                            StatusPill { text: root.validationText(modelData.validation); tone: ["oracle", "field", "stable"].indexOf(modelData.validation) >= 0 ? root.palette.success : root.palette.warning }
                            StatusPill { text: modelData.environment || "当前可运行"; tone: root.palette.muted }
                        }
                    }
                    Button {
                        id: problemActionButton
                        objectName: "learnOpenProblemButton"
                        text: modelData.locked ? "未解锁"
                              : modelData.status === "in_progress" ? "继续"
                              : modelData.status === "mastered" ? "查看"
                              : "开始"
                        enabled: !modelData.locked
                                 && modelData.asset_status !== "planned"
                                 && modelData.environment_available !== false
                        Layout.preferredWidth: 82
                        Layout.preferredHeight: 40
                        Layout.alignment: Qt.AlignTop
                        background: Rectangle {
                            radius: 8
                            color: !problemActionButton.enabled
                                   ? root.palette.surfaceAlt
                                   : modelData.status === "in_progress"
                                     ? root.palette.accent : "transparent"
                            border.color: modelData.status === "in_progress"
                                          ? root.palette.accent : root.palette.border
                        }
                        contentItem: Text {
                            text: problemActionButton.text
                            color: !problemActionButton.enabled
                                   ? root.palette.muted
                                   : modelData.status === "in_progress"
                                     ? "white" : root.palette.text
                            font.bold: modelData.status === "in_progress"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: app.openProblem(modelData.problem_id)
                    }
                }
            }
        }
    }
}
