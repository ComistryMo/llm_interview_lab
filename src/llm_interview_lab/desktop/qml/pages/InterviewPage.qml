import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var activeQuestion: app.interview.question || null
    property var rubricScores: ({})
    property var aiPreview: ({"parts": [], "estimated_tokens": 0})
    property string pendingAIAction: ""
    property string pendingConnection: ""
    property bool answerLocked: !!app.interview.answer_locked
    property string phase: app.interview.phase || (answerLocked ? "assessment" : "answering")
    property var interviewResult: app.interview.result || ({})
    property string answerDraft: ""
    property string activeQuestionId: activeQuestion ? activeQuestion.question_id : ""
    property bool showSessionDetails: false
    property var configuration: ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    property string codeFontFamily: Qt.platform.os === "windows" ? "Cascadia Mono"
                                    : Qt.platform.os === "osx" ? "Menlo" : "monospace"
    onActiveQuestionIdChanged: { rubricScores = ({}); answerDraft = "" }
    onVisibleChanged: if (visible && leftPanel.setupVisible) Qt.callLater(root.initializeSetup)

    function statusText(value) {
        return ({active: "进行中", ready: "待开始", completed: "已完成", incomplete: "未完成", timed_out: "已超时"})[value] || value || "未知"
    }

    function seniorityText(value) {
        return ({intern: "实习", new_grad: "校招", mid: "有经验", senior: "高级"})[value] || value || "未设置"
    }

    function difficultyText(value) {
        return ({easy: "基础", medium: "标准", hard: "高压"})[value] || value || "未设置"
    }

    function timerText(seconds) {
        if (seconds === undefined || seconds === null)
            return "未开始"
        if (seconds <= 0)
            return "已到时"
        var minutes = Math.floor(seconds / 60)
        var rest = seconds % 60
        return (minutes < 10 ? "0" : "") + minutes + ":" + (rest < 10 ? "0" : "") + rest
    }

    function previewAI(action, connectionId) {
        root.aiPreview = app.interviewContextPreview(
            answer.text, includeInterviewMaterials.checked
        )
        if ((root.aiPreview.parts || []).length === 0)
            return
        root.pendingAIAction = action
        root.pendingConnection = connectionId || ""
        contextDialog.open()
    }

    function rubricComplete() {
        if (!activeQuestion || !activeQuestion.rubric)
            return false
        var dimensions = Object.keys(activeQuestion.rubric.dimensions || {})
        if (dimensions.length === 0)
            return false
        for (var i = 0; i < dimensions.length; ++i) {
            if (root.rubricScores[dimensions[i]] === undefined)
                return false
        }
        return true
    }

    function roleIndex(roleId) {
        var values = app.roles || []
        for (var i = 0; i < values.length; ++i) {
            if (values[i].id === roleId)
                return i
        }
        return values.length > 0 ? 0 : -1
    }

    function seniorityIndex(value) {
        return value === "intern" ? 0 : value === "mid" ? 2 : 1
    }

    function refreshConfiguration() {
        var roleId = role.currentValue || ""
        if (!roleId) {
            root.configuration = ({"available": false, "user_message": "当前没有可选择的岗位蓝图。"})
            return
        }
        if (typeof app.interviewConfiguration === "function")
            root.configuration = app.interviewConfiguration(roleId, seniority.currentValue, difficulty.currentValue)
        else
            root.configuration = ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    }

    function initializeSetup() {
        var rolePreference = (app.dashboard.role && app.dashboard.role.primary_role) || ""
        role.currentIndex = root.roleIndex(rolePreference)
        seniority.currentIndex = root.seniorityIndex((app.dashboard.role && app.dashboard.role.seniority) || "new_grad")
        root.refreshConfiguration()
    }

    function configurationMessage() {
        if (root.configuration.available !== false)
            return ""
        var message = root.configuration.user_message || "当前配置暂时无法开始面试。"
        var rounds = root.configuration.missing_rounds || []
        var environment = root.configuration.missing_environment || []
        if (rounds.length > 0) {
            var roundLabels = []
            for (var i = 0; i < rounds.length; ++i)
                roundLabels.push(root.missingRoundLabel(rounds[i]))
            message += "\n缺少环节：" + roundLabels.join("；")
        }
        if (environment.length > 0) {
            var environmentLabels = []
            for (var j = 0; j < environment.length; ++j)
                environmentLabels.push(root.missingEnvironmentLabel(environment[j]))
            message += "\n环境要求：" + environmentLabels.join("；")
        }
        return message
    }

    function missingRoundLabel(item) {
        if (typeof item === "string")
            return root.roundTypeText(item)
        var label = root.roundTypeText(item.round || item.type || "")
        var reason = ({missing_environment: "当前环境缺少所需依赖",
                       no_strict_candidate: "当前难度没有严格匹配的固定题"})[item.reason]
                     || "当前没有可用的固定题"
        return label + "（" + reason + "）"
    }

    function roundTypeText(value) {
        return ({coding: "代码实现", debugging: "调试分析", product_case: "产品案例",
                 system_design: "系统设计", evaluation_case: "评测案例",
                 project_deep_dive: "项目深挖", behavioral: "行为面试",
                 oral: "口述问答"})[value] || "面试环节"
    }

    function assessmentSourceText(value) {
        return ({self: "自评", human: "人工", ai: "AI", peer: "同伴", mentor: "导师"})[value]
               || "未标注"
    }

    function resultAssessmentSources(result) {
        var evidence = result && Array.isArray(result.assessment_evidence)
                       ? result.assessment_evidence : []
        var sources = []
        for (var i = 0; i < evidence.length; ++i) {
            var source = evidence[i].source || ""
            if (source && sources.indexOf(source) < 0)
                sources.push(source)
        }
        return sources
    }

    function resultScoreLabel(result) {
        var sources = root.resultAssessmentSources(result)
        var partial = result && (result.completion_status !== "completed"
                                 || (result.unanswered || []).length > 0
                                 || (result.unscored || []).length > 0)
        if (sources.length === 0)
            return "评分"
        if (partial && sources.length === 1 && sources[0] === "self")
            return "自评（部分证据）"
        if (partial)
            return "部分证据分数"
        if (sources.length === 1 && sources[0] === "self")
            return "自评分数"
        if (sources.length === 1 && sources[0] === "ai")
            return "AI 评估分数"
        if (sources.length === 1 && sources[0] === "human")
            return "人工评估分数"
        if (sources.length > 1)
            return "混合证据分数"
        return root.assessmentSourceText(sources[0]) + "评估分数"
    }

    function resultSourceNote(result) {
        var sources = root.resultAssessmentSources(result)
        if (sources.length === 0)
            return ""
        var labels = []
        for (var i = 0; i < sources.length; ++i)
            labels.push(root.assessmentSourceText(sources[i]))
        var partial = result && (result.completion_status !== "completed"
                                 || (result.unanswered || []).length > 0
                                 || (result.unscored || []).length > 0)
        if (partial)
            return "本场未完整完成；当前数值基于已记录证据，未完成环节按 0 计入，不代表完整面试结果。评分来源："
                   + labels.join("、") + "。"
        if (sources.length === 1 && sources[0] === "self")
            return "本场只包含自评记录；用于复盘，不是面试官结论。"
        return "评分来源：" + labels.join("、") + "。请结合下方证据逐条核对。"
    }

    function recordedAtText(value) {
        if (!value)
            return "时间未记录"
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return value
        return Qt.formatDateTime(date, "yyyy-MM-dd HH:mm")
    }

    function confidenceText(value) {
        return ({low: "低", medium: "中", high: "高"})[value] || "未标注"
    }

    function missingEnvironmentLabel(item) {
        if (typeof item === "string")
            return item
        return item.reason || item.requirement || item.name || item.type || "未满足的运行环境"
    }

    function resultScoreText(result) {
        if (!result)
            return "尚未评分"
        if (root.resultAssessmentSources(result).length === 0)
            return "尚未评分"
        var score = result.overall_score
        return score === undefined || score === null ? "尚未评分" : String(score)
    }

    function resultListText(value, emptyText) {
        if (value === undefined || value === null || value === false || value === "")
            return emptyText || ""
        if (!Array.isArray(value))
            return String(value)
        if (value.length === 0)
            return emptyText || ""
        var labels = []
        for (var i = 0; i < value.length; ++i) {
            var item = value[i]
            if (typeof item === "string")
                labels.push(item)
            else
                labels.push(item.title || item.question_id || item.skill || item.reason || JSON.stringify(item))
        }
        return labels.join("、")
    }

    function resultUnscoredText(result) {
        var value = result ? root.resultListText(result.unscored, "") : ""
        return value ? "未评分：" + value : ""
    }

    Component.onCompleted: Qt.callLater(root.initializeSetup)

    Timer {
        interval: 1000
        repeat: true
        running: app.interview.status === "active"
        onTriggered: app.refreshInterviewClock()
    }

    RowLayout {
        anchors.fill: parent; anchors.margins: root.width < 1000 ? 16 : 26; spacing: 12

        LabCard {
            id: leftPanel
            Layout.preferredWidth: root.width < 1000 ? 238 : 280
            Layout.minimumWidth: 220
            Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            property bool setupVisible: !app.interview.interview_id || app.interview.status === "completed" || app.interview.status === "incomplete"
            padding: 12

            ScrollView {
                id: setupScroll
                width: parent.width
                height: parent.height
                clip: true

                Column {
                    width: setupScroll.availableWidth
                    spacing: 9
                    Text { width: parent.width; text: leftPanel.setupVisible ? "面试设置" : "进行中的面试"; color: root.palette.text; font.pixelSize: 19; font.bold: true; wrapMode: Text.Wrap }
                    Text { visible: leftPanel.setupVisible; text: "目标岗位"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: role; width: parent.width; textRole: "title"; valueRole: "id"; model: app.roles; currentIndex: -1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "求职阶段"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: seniority; width: parent.width; model: [{id:"intern", label:"实习"}, {id:"new_grad", label:"校招"}, {id:"mid", label:"有经验"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "难度"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: difficulty; width: parent.width; model: [{id:"easy", label:"基础"}, {id:"medium", label:"标准"}, {id:"hard", label:"高压"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text {
                        objectName: "interviewDifficultyHint"
                        visible: leftPanel.setupVisible
                        width: parent.width
                        text: {
                            if (!role.currentValue)
                                return "先选择岗位，系统会检查该难度是否有完整题目。"
                            if (root.configuration.available !== false)
                                return "当前难度可用；开始后题目组合会冻结。"
                            if ((root.configuration.missing_environment || []).length > 0)
                                return "当前环境暂缺所需依赖；可先切换到“标准”或查看环境说明。"
                            return "当前岗位在此难度没有完整固定题；请切换到“标准”或更换岗位。"
                        }
                        color: root.configuration.available === false ? root.palette.warning : root.palette.muted
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        font.pixelSize: 11
                    }
                    Text { visible: leftPanel.setupVisible; text: "面试官"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: aiMode; width: parent.width; model: [{id:"disabled", label:"手动 / 无 AI"}, {id:"provider", label:"普通 LLM API"}, {id:"codex", label:"Codex"}]; textRole: "label"; valueRole: "id" }
                    CheckBox {
                        id: useMaterial
                        width: parent.width
                        visible: leftPanel.setupVisible
                        enabled: aiMode.currentValue !== "disabled" && app.materials.length > 0
                        text: "使用一份逐场授权的求职材料"
                    }
                    ComboBox {
                        id: material
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        model: app.materials
                        textRole: "title"
                        valueRole: "id"
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked && material.currentIndex >= 0
                        text: material.currentIndex >= 0 ? "材料 ID：" + app.materials[material.currentIndex].id + "\n用途：role_interview\nSHA-256：" + app.materials[material.currentIndex].sha256 : ""
                        color: root.palette.muted
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                    }
                    CheckBox {
                        id: consent
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        text: "我同意本场面试读取这个精确 ID / SHA 的材料"
                    }
                    Text {
                        objectName: "interviewConfigurationMessage"
                        width: parent.width
                        visible: leftPanel.setupVisible && root.configuration.available === false
                        text: root.configurationMessage()
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    Button {
                        objectName: "startConfiguredInterview"
                        width: parent.width
                        visible: leftPanel.setupVisible
                        text: app.busy ? "正在准备面试……" : "开始模拟面试"
                        highlighted: true
                        enabled: root.configuration.available !== false
                                 && !!role.currentValue
                                 && !app.busy
                                 && (!useMaterial.checked || (material.currentIndex >= 0 && app.materials[material.currentIndex].ai_access && consent.checked))
                        onClicked: {
                            if (useMaterial.checked)
                                app.createTailoredInterview(role.currentValue, seniority.currentValue, difficulty.currentValue, material.currentValue, consent.checked, aiMode.currentValue)
                            else
                                app.createConfiguredInterview(role.currentValue, seniority.currentValue, difficulty.currentValue, aiMode.currentValue)
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { text: "本场事实"; color: root.palette.text; font.bold: true }
                    Text {
                        width: parent.width
                        text: app.interview.interview_id
                              ? "状态  " + root.statusText(app.interview.status)
                                + "\n岗位  " + (app.interview.role_title || app.interview.role_id)
                                + "\n求职级别  " + root.seniorityText(app.interview.seniority)
                                + "\n选题档位  " + root.difficultyText(app.interview.difficulty)
                                + "\n进度  " + (app.interview.completed_questions || 0)
                                + " / " + (app.interview.total_questions || 0)
                              : "暂无进行中的面试"
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        lineHeight: 1.5
                    }
                    ToolButton {
                        visible: !!app.interview.interview_id
                        text: root.showSessionDetails ? "收起技术详情" : "查看技术详情"
                        onClicked: root.showSessionDetails = !root.showSessionDetails
                    }
                    Text {
                        visible: root.showSessionDetails && !!app.interview.interview_id
                        width: parent.width
                        text: "会话 ID：" + app.interview.interview_id
                              + (app.interview.blueprint_id ? "\n蓝图：" + app.interview.blueprint_id : "")
                              + "\n本场选题难度：" + root.difficultyText(app.interview.difficulty)
                              + (root.activeQuestionId ? "\n当前问题 ID：" + root.activeQuestionId : "")
                        color: root.palette.muted
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                    }
                    Text { width: parent.width; text: "模拟面试分数不会改变刷题训练的掌握状态。"; color: root.palette.warning; wrapMode: Text.Wrap; font.pixelSize: 12; font.bold: true }
                }
            }
        }

        LabCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            RowLayout {
                width: parent.width
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: activeQuestion ? (activeQuestion.kind === "coding" ? "代码题" : (activeQuestion.kind === "system_design" ? "系统设计" : "结构化问答")) : "模拟面试室"; color: root.palette.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                    Text { Layout.fillWidth: true; text: activeQuestion ? activeQuestion.title : "按岗位蓝图开始一场面试"; color: root.palette.text; font.pixelSize: 22; font.bold: true; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                }
                StatusPill {
                    text: app.interview.status === "active"
                          ? root.timerText(app.interview.remaining_seconds)
                          : root.statusText(app.interview.status)
                    tone: app.interview.status === "active" ? root.palette.warning : root.palette.muted
                }
            }
            Rectangle { width: parent.width; height: 1; color: root.palette.border }
            ScrollView {
                id: questionScroll
                width: parent.width
                Layout.fillHeight: true
                clip: true
                // Keep the question column tied to the panel viewport.  Without
                // an explicit content width, Qt sizes the Flickable content to
                // the TextArea's implicit width, leaving the editor as a narrow
                // strip and making the phase controls collide on small screens.
                contentWidth: availableWidth
                Column {
                    width: questionScroll.availableWidth
                    spacing: 16
                    Text { width: parent.width; text: activeQuestion ? activeQuestion.prompt : "选择岗位、求职阶段与难度。系统会冻结一份公共面试蓝图，每次只展示一个问题，并将客观代码证据与 Rubric 主观判断分开。"; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    TextArea { id: answer; objectName: "interviewAnswerEditor"; width: parent.width; height: 180; visible: !!activeQuestion && activeQuestion.kind !== "coding"; text: root.answerLocked ? (app.interview.answer_text || "") : root.answerDraft; readOnly: root.answerLocked; onTextChanged: if (!root.answerLocked) root.answerDraft = text; placeholderText: root.answerLocked ? "回答已锁定" : "输入你的回答……"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.answerLocked ? root.palette.accent : root.palette.border } }
                    LabCard {
                        objectName: "interviewAnswerCorruption"
                        visible: !!app.interview.answer_corrupted
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.danger
                        Text { width: parent.width; text: app.interview.answer_error || "已锁定的回答当前不可读取，评分已暂停。"; color: root.palette.danger; wrapMode: Text.Wrap; font.bold: true }
                    }
                    RowLayout {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                        width: parent.width
                        StatusPill {
                            objectName: "interviewPhasePill"
                            text: root.answerLocked
                                  ? (app.interview.pending_followup ? "阶段 C · 追问" : "阶段 B · 评估")
                                  : "阶段 A · 回答"
                            tone: root.answerLocked ? root.palette.accent : root.palette.muted
                        }
                        Text { text: root.answerLocked ? "阶段 B：回答已锁定，下面进入评估" : "阶段 A：先完成回答；锁定后才会显示评分维度"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Button { objectName: "lockInterviewAnswer"; visible: !root.answerLocked; text: "提交并锁定回答"; highlighted: true; enabled: answer.text.trim().length > 0 && !app.busy; onClicked: app.lockInterviewAnswer(answer.text) }
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && answer.text.trim().length === 0
                        text: "先写下回答，提交按钮才会启用。"
                        color: root.palette.muted
                        font.pixelSize: 11
                    }
                    Column {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted
                        width: parent.width
                        spacing: 6
                        Text { text: "自评 Rubric（每个维度 1–5 分）"; color: root.palette.muted; font.bold: true }
                        Text { text: "用于自我校准，不代表客观面试结论。"; color: root.palette.muted; font.pixelSize: 11; wrapMode: Text.Wrap }
                        Repeater {
                            model: activeQuestion ? Object.keys(activeQuestion.rubric.dimensions) : []
                            delegate: RowLayout {
                                required property string modelData
                                width: parent.width
                                Text { text: modelData.replace(/_/g, " "); color: root.palette.text; Layout.preferredWidth: 190 }
                                Slider {
                                    id: dimensionScore
                                    from: 1; to: 5; stepSize: 1; value: 1
                                    Layout.fillWidth: true
                                    onValueChanged: if (pressed) root.rubricScores[modelData] = Math.round(value)
                                }
                                Text { text: root.rubricScores[modelData] === undefined ? "未评分" : Math.round(dimensionScore.value) + " / 5"; color: root.palette.text; font.bold: true; Layout.preferredWidth: 54 }
                            }
                        }
                    }
                    TextArea { id: evidence; width: parent.width; height: 86; visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted; placeholderText: "支持本次评分的回答证据（必填）"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border } }
                    ComboBox {
                        id: providerConnection
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && app.interview.ai_mode === "provider"
                        width: parent.width
                        model: app.connections
                        textRole: "display_name"
                        valueRole: "connection_id"
                    }
                    CheckBox {
                        id: includeInterviewMaterials
                        visible: !!activeQuestion && root.answerLocked && !app.interview.answer_corrupted
                                 && activeQuestion.kind !== "coding"
                                 && app.interview.ai_mode !== "disabled"
                                 && (app.interview.material_refs || []).length > 0
                        checked: true
                        text: "在本次 AI 请求中包含已授权材料"
                    }
                    Flow {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted
                        width: parent.width
                        spacing: 8
                        Button {
                            text: "记录自评结果"
                            enabled: root.rubricComplete() && evidence.text.trim().length > 0
                                     && !app.busy && !app.interview.assessment_recorded
                            onClicked: app.answerInterviewDetailed(answer.text, JSON.stringify(root.rubricScores), evidence.text)
                        }
                        Button {
                            visible: app.interview.ai_mode === "provider"
                            enabled: providerConnection.currentIndex >= 0 && !app.busy
                                     && !app.interview.assessment_recorded
                            text: "预览 AI 评分上下文"
                            highlighted: true
                            onClicked: root.previewAI("provider", providerConnection.currentValue)
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex"
                            enabled: !app.busy && !app.interview.assessment_recorded
                            text: "连接 Codex 面试官"
                            highlighted: true
                            onClicked: app.connectCodex("interviewer")
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex" && (app.aiStatus.indexOf("已连接") >= 0 || app.aiStatus.indexOf("就绪") >= 0)
                            enabled: !app.busy && !app.interview.assessment_recorded
                            text: "预览 Codex 评分上下文"
                            onClicked: root.previewAI("codex", "")
                        }
                    }
                    LabCard {
                        visible: !!app.interview.pending_followup
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.accent
                        Text { width: parent.width; text: "自适应追问\n" + (app.interview.pending_followup || ""); color: root.palette.text; wrapMode: Text.Wrap; font.bold: true }
                        TextArea { id: followupAnswer; width: parent.width; height: 100; placeholderText: "回答这一个追问"; wrapMode: Text.Wrap; padding: 12; clip: true }
                        Text {
                            width: parent.width
                            text: "追问回答会留档并关联到本题评估；当前评分仍采用主回答生成的 AI 评估，不会根据这次追问自动重算。"
                            color: root.palette.muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        Button {
                            text: "记录追问回答并采用已有评估"
                            highlighted: true
                            enabled: followupAnswer.text.trim().length > 0 && !app.busy
                            onClicked: app.answerAIFollowup(followupAnswer.text)
                        }
                    }
                    LabCard {
                        objectName: "interviewResultCard"
                        visible: Object.keys(root.interviewResult).length > 0
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.border
                        Text { width: parent.width; text: "本场评估"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                        Text {
                            width: parent.width
                            text: root.resultScoreLabel(root.interviewResult) + "：" + root.resultScoreText(root.interviewResult)
                                  + "\n完成状态：" + root.statusText(root.interviewResult.completion_status)
                            color: root.palette.text
                            wrapMode: Text.Wrap
                            lineHeight: 1.4
                        }
                        Text {
                            width: parent.width
                            visible: root.resultSourceNote(root.interviewResult).length > 0
                            text: root.resultSourceNote(root.interviewResult)
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                        Text {
                            width: parent.width
                            visible: !!root.interviewResult.summary
                            text: root.interviewResult.summary || ""
                            color: root.palette.text
                            wrapMode: Text.Wrap
                        }
                        Text { width: parent.width; text: "评分证据"; color: root.palette.muted; font.bold: true }
                        Repeater {
                            model: root.interviewResult.assessment_evidence || []
                            delegate: Rectangle {
                                required property var modelData
                                width: parent.width
                                height: evidenceColumn.implicitHeight + 16
                                radius: 8
                                color: root.palette.surface
                                border.color: root.palette.border
                                Column {
                                    id: evidenceColumn
                                    x: 10; y: 8; width: parent.width - 20; spacing: 4
                                    Text {
                                        width: parent.width
                                        text: (modelData.title || modelData.question_id || "未命名问题")
                                              + (modelData.score === undefined || modelData.score === null ? " · 尚未评分" : " · " + modelData.score)
                                        color: root.palette.text
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: "来源：" + root.assessmentSourceText(modelData.source)
                                              + " · 置信度：" + root.confidenceText(modelData.confidence)
                                        color: root.palette.muted
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        visible: (modelData.followup_ids || []).length > 0
                                        width: parent.width
                                        text: "关联追问：" + (modelData.followup_ids || []).join("、")
                                        color: root.palette.accent
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: modelData.evidence || "未记录评分证据。"
                                        color: root.palette.text
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                        Column {
                            visible: (root.interviewResult.followups || []).length > 0
                            width: parent.width
                            spacing: 8
                            Text { width: parent.width; text: "追问记录"; color: root.palette.muted; font.bold: true }
                            Repeater {
                                model: root.interviewResult.followups || []
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: parent.width
                                    height: followupColumn.implicitHeight + 16
                                    radius: 8
                                    color: root.palette.surface
                                    border.color: root.palette.border
                                    Column {
                                        id: followupColumn
                                        x: 10; y: 8; width: parent.width - 20; spacing: 4
                                        Text {
                                            width: parent.width
                                            text: "追问 " + (index + 1) + " · "
                                                  + (modelData.parent_title || modelData.parent_question_id || "原问题未记录")
                                            color: root.palette.accent
                                            font.bold: true
                                            wrapMode: Text.Wrap
                                        }
                                        Text { width: parent.width; text: modelData.prompt || ""; color: root.palette.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "回答：" + (modelData.answer || ""); color: root.palette.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "来源：" + root.assessmentSourceText(modelData.source); color: root.palette.muted; font.pixelSize: 11; wrapMode: Text.Wrap }
                                        Text {
                                            width: parent.width
                                            text: "记录：" + (modelData.followup_id || "未编号")
                                                  + " · " + root.recordedAtText(modelData.recorded_at)
                                            color: root.palette.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }
                            }
                        }
                        Text {
                            width: parent.width
                            visible: (root.interviewResult.assessment_evidence || []).length === 0
                            text: "本场没有足够证据支持评分。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                        }
                        Text {
                            width: parent.width
                            visible: root.resultListText(root.interviewResult.critical_gaps, "").length > 0
                            text: "关键缺口：" + root.resultListText(root.interviewResult.critical_gaps, "")
                            color: root.palette.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            visible: root.resultUnscoredText(root.interviewResult).length > 0
                            text: root.resultUnscoredText(root.interviewResult)
                            color: root.palette.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            text: "该结果只记录模拟面试证据，不会改变刷题训练的掌握状态。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                    }
                    ColumnLayout {
                        visible: !!activeQuestion && activeQuestion.kind === "coding"
                        width: parent.width; spacing: 10
                        Text { text: "本场冻结的代码答案"; color: root.palette.text; font.bold: true }
                        TextArea {
                            id: codingEditor
                            Layout.fillWidth: true; Layout.preferredHeight: 260
                            text: app.interview.coding_text || ""
                            color: root.palette.text
                            font.family: root.codeFontFamily
                            font.pixelSize: 13
                            wrapMode: TextEdit.NoWrap
                            padding: 12
                            clip: true
                            background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border }
                            Accessible.name: "限时代码面试编辑器"
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Button { text: "保存"; onClicked: app.saveInterviewCoding(codingEditor.text) }
                            Button { text: "运行 Grader"; highlighted: true; enabled: !app.busy; onClicked: app.runInterviewCoding(codingEditor.text) }
                            Button { text: "记录本轮并继续"; enabled: !app.busy; onClicked: app.recordInterviewCodingRound() }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 110; radius: 8
                            color: root.palette.surfaceAlt; border.color: root.palette.border
                            ScrollView {
                                anchors.fill: parent; anchors.margins: 10
                                Text { width: parent.width; text: app.testOutput || "本地 Grader 是代码结果的事实来源。"; color: root.palette.text; wrapMode: Text.Wrap; font.family: root.codeFontFamily; font.pixelSize: 11 }
                            }
                        }
                        Text { text: "面试进行中不会展示教学提示。"; color: root.palette.warning; font.pixelSize: 12; font.bold: true }
                    }
                }
            }
            RowLayout {
                width: parent.width
                Text {
                    text: activeQuestion ? "一次只完成一个主问题" : ""
                    color: root.palette.muted
                    font.pixelSize: 12
                }
                Item { Layout.fillWidth: true }
                Button {
                    objectName: "finishInterviewButton"
                    text: "结束并标记未完成"
                    enabled: !!app.interview.interview_id && !app.busy
                    onClicked: finishDialog.open()
                }
            }
        }
    }

    Dialog {
        id: contextDialog
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 64)
        height: Math.min(520, root.height - 64)
        title: "上下文预览（只读）"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.pendingAIAction === "provider")
                app.assessInterviewWithProvider(
                    answer.text,
                    root.pendingConnection,
                    includeInterviewMaterials.checked
                )
            else if (root.pendingAIAction === "codex")
                app.sendCodexInterviewAnswer(
                    answer.text,
                    includeInterviewMaterials.checked
                )
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        onRejected: {
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "只有下面标记为“将发送”的内容会被发送；取消则不会发送任何内容。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: root.aiPreview.parts || []
                        delegate: RowLayout {
                            required property var modelData
                            width: parent.width
                            StatusPill {
                                text: modelData.selected ? "将发送" : "不发送"
                                tone: modelData.selected ? root.palette.accent : root.palette.muted
                            }
                            Text {
                                text: modelData.label
                                color: root.palette.text
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            StatusPill {
                                visible: modelData.sensitive
                                text: "敏感内容"
                                tone: root.palette.warning
                            }
                        }
                    }
                }
            }
            Text {
                text: "预计上下文：" + (root.aiPreview.estimated_tokens || 0) + " tokens"
                color: root.palette.muted
                font.pixelSize: 12
            }
        }
    }

    Dialog {
        id: finishDialog
        objectName: "interviewFinishDialog"
        modal: true
        anchors.centerIn: parent
        title: "结束本场面试？"
        width: Math.min(440, root.width - 48)
        height: 250
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.finishInterview()
        contentItem: Text {
            width: 360
            text: "已完成：" + (app.interview.completed_questions || 0)
                  + " / " + (app.interview.total_questions || 0)
                  + "\n未回答：" + (app.interview.unanswered_questions || 0)
                  + "\n已回答但未评分：" + (app.interview.unscored_questions || 0)
                  + "\n代码环节未完成：" + (app.interview.coding_incomplete || 0)
                  + "\n\n结束后，本场会按现有证据标记为未完成并留档。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }
}
