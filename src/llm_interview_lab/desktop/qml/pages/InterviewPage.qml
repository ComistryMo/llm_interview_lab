import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var colors
    property var theme: null
    readonly property bool dynamicInterview: app.interview.delivery_mode === "dynamic_ai"
    readonly property bool conversationalAnswer: root.dynamicInterview && !!activeQuestion && !root.codingQuestion
    property bool showVoiceOptions: false
    property bool showVoiceSettings: false
    readonly property bool voiceRecording: app.interviewVoice.state === "recording"
    readonly property bool voiceTranscribing: app.interviewVoice.transcription_state === "transcribing"
    readonly property string voiceActionText: root.voiceRecording ? "完成录音" : root.voiceTranscribing ? "正在转成文字…" : "语音输入"
    property var activeQuestion: app.interview.question || null
    property var rubricScores: ({})
    property var aiPreview: ({"parts": [], "estimated_tokens": 0})
    property var planContext: ({"parts": [], "estimated_tokens": 0, "context_sha256": ""})
    // A Codex plan click connects the dedicated interviewer thread first.
    // Keep that intent so the first click continues into the context preview.
    property bool codexPlanPending: false
    property string pendingAIAction: ""
    property string pendingConnection: ""
    property bool answerLocked: !!app.interview.answer_locked
    property string phase: app.interview.phase || (answerLocked ? "assessment" : "answering")
    property var interviewResult: app.interview.result || ({})
    property string answerDraft: ""
    // Keep a confirmation snapshot so an accidental click cannot lock a
    // changing editor value.  The backend remains the source of truth for
    // the actual frozen answer.
    property string pendingLockAnswer: ""
    property string activeQuestionId: activeQuestion ? activeQuestion.question_id : ""
    property string activeQuestionKey: String(app.profileId || "") + "::" + String(app.interview.interview_id || "")
                                  + "::" + String(activeQuestion ? activeQuestion.question_id : "")
    property bool configuringNewInterview: false
    property bool syncingQuestionEditors: false
    // The context confirmation is a single, synchronous hand-off to the
    // controller.  Keep a local gate as well as ``app.busy`` so keyboard
    // activation and a mouse click in the same event loop cannot create two
    // sessions.
    property bool startingDynamicInterview: false
    property var pendingConnectionCheck: null
    property string setupConnectionId: ""
    property string transcriptionConnectionId: ""
    readonly property bool usingLocalStt: voiceConnection.currentValue === app.localStt.connection_id
    readonly property string setupProfileId: app.profileId
    onSetupProfileIdChanged: {
        Qt.callLater(root.initializeSetup)
        Qt.callLater(root.clearSetupConsent)
    }
    // A coding round can only be recorded when the visible editor still
    // matches the revision that the local Grader tested. TextArea bindings are
    // intentionally broken after typing, so track edits explicitly.
    property bool codingEditorDirty: false
    property bool showCodingPrompt: true
    property bool showEnglishQuestion: app.language === "en"
    readonly property string preferredQuestionLanguage: app.language
    onPreferredQuestionLanguageChanged: showEnglishQuestion = preferredQuestionLanguage === "en"
    readonly property bool codingQuestion: !!activeQuestion && activeQuestion.kind === "coding"
    readonly property bool interviewFinished: app.interview.status === "completed" || app.interview.status === "incomplete"
    readonly property bool hasUnsubmittedDraft: !!activeQuestion && (root.codingQuestion
        ? root.codingEditorDirty
        : !root.answerLocked && (answer.text.length > 0 || answer.preeditText.length > 0))
    onHasUnsubmittedDraftChanged: app.setInterviewDraftDirty(root.hasUnsubmittedDraft)
    property bool interviewCanEdit: app.interview.status === "active"
                                    && app.interview.expired !== true
    // A short viewport needs to keep the answer action visible before asking
    // the learner to scroll.  This is a presentation breakpoint only; it does
    // not change interview timing or answer semantics.
    // The page width excludes the shell/sidebar.  Keep the full interview
    // layout at a normal 1280×800 window; only genuinely narrow/short views
    // switch to the compact editor sizing.
    property bool compactInterviewLayout: width < 900 || height < 600
    property var configuration: ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    property string codeFontFamily: Qt.platform.os === "windows" ? "Cascadia Mono"
                                    : Qt.platform.os === "osx" ? "Menlo" : "monospace"
    onActiveQuestionKeyChanged: {
        if (app.interview.status === "active")
            root.configuringNewInterview = false
        Qt.callLater(root.resetQuestionEditors)
    }
    onAnswerLockedChanged: Qt.callLater(root.syncQuestionEditors)
    onVisibleChanged: {
        if (!visible) root.pendingConnectionCheck = null
        if (visible && leftPanel.setupVisible) Qt.callLater(root.initializeSetup)
    }

    function statusText(value) {
        return ({active: "进行中", paused: "已暂停", ready: "待开始", completed: "已完成", incomplete: "未完成", timed_out: "已超时"})[value] || value || "未知"
    }

    function finishDialogMessage() {
        if (root.dynamicInterview) {
            var coverage = app.interview.flow_coverage || ({})
            return coverage.complete === true
                ? "自我介绍、经历追问、岗位原理和手撕均已有实际证据。确认后结束并生成本场报告。"
                : "尚未完成：" + (coverage.missing_labels || []).join("、")
                  + "。确认后将保留已有证据并标记未完成，不会生成完整面试结论。"
        }
        var completed = Number(app.interview.completed_questions || 0)
        var total = Number(app.interview.total_questions || 0)
        var unanswered = Number(app.interview.unanswered_questions || 0)
        var unscored = Number(app.interview.unscored_questions || 0)
        var codingIncomplete = Number(app.interview.coding_incomplete || 0)
        var complete = total > 0 && completed >= total && unanswered === 0
                       && unscored === 0 && codingIncomplete === 0
        if (app.interview.expired === true || app.interview.status === "timed_out")
            return "计时已到；确认后会按现有证据生成超时/未完成报告。"
        if (complete)
            return "所有固定问题都已有回答和评分证据。确认后会生成完整报告并结束本场。"
        if (app.interview.status === "paused")
            return "本场目前已暂停。确认后会按现有证据留档为未完成报告。"
        return "当前证据尚未覆盖全部问题。确认后会按现有证据留档为未完成报告。"
    }

    // Answer/coding editors stop honoring their initial `text:` binding as
    // soon as the learner types.  Rehydrate them only when the frozen
    // question or lock state changes; ordinary state updates must never erase
    // in-progress typing.
    function syncQuestionEditors() {
        root.syncingQuestionEditors = true
        if (answer)
            answer.text = root.answerLocked ? (app.interview.answer_text || "") : ""
        if (codingEditor)
            codingEditor.text = app.interview.coding_text || ""
        root.codingEditorDirty = false
        root.syncingQuestionEditors = false
    }

    function resetQuestionEditors() {
        root.showVoiceOptions = false
        root.showVoiceSettings = false
        root.rubricScores = ({})
        root.answerDraft = ""
        root.pendingLockAnswer = ""
        root.showCodingPrompt = true
        root.showEnglishQuestion = app.language === "en"
        voiceConsent.checked = false
        var savedConnection = String(app.interview.connection_id || "")
        var selectedIndex = providerConnection.indexOfValue(savedConnection)
        if (selectedIndex >= 0)
            providerConnection.currentIndex = selectedIndex
        evidence.text = ""
        followupAnswer.text = ""
        root.syncQuestionEditors()
    }

    function runCodingTests() {
        if (app.runInterviewCoding(codingEditor.text)) {
            root.codingEditorDirty = false
            root.showCodingPrompt = false
            questionScroll.contentItem.contentY = 0
        }
    }

    Shortcut {
        sequences: ["Ctrl+R", "Meta+R"]
        enabled: root.visible && root.codingQuestion && root.interviewCanEdit && !app.busy
        onActivated: root.runCodingTests()
    }

    function providerIsReady(itemOrId) {
        // ``ready`` is a controller-owned boolean set only after a successful
        // connection test.  Presentation strings such as “已连接” must not
        // become a second business-status source in QML.
        var item = itemOrId
        if (typeof itemOrId === "string") {
            var values = app.connections || []
            for (var i = 0; i < values.length; ++i) {
                if (String(values[i].connection_id || "") === itemOrId) {
                    item = values[i]
                    break
                }
            }
        }
        if (!item || typeof item !== "object")
            return false
        return item.ready === true
    }

    function prepareInterview() {
        if (root.startingDynamicInterview || root.pendingConnectionCheck || app.busy)
            return
        if (aiMode.currentValue === "provider" && !root.providerIsReady(planConnection.currentValue)) {
            root.pendingConnectionCheck = {profile: app.profileId, connection: planConnection.currentValue}
            app.testConnection(planConnection.currentValue)
            if (!app.busy) root.pendingConnectionCheck = null
            return
        }
        root.openPersonalizedPlanContext()
    }

    function finishConnectionCheck() {
        var pending = root.pendingConnectionCheck
        root.pendingConnectionCheck = null
        if (pending && root.visible && leftPanel.setupVisible
                && pending.profile === app.profileId
                && aiMode.currentValue === "provider"
                && pending.connection === planConnection.currentValue
                && root.providerIsReady(pending.connection))
            root.openPersonalizedPlanContext()
    }

    function openPersonalizedPlanContext() {
        if (root.startingDynamicInterview || app.busy)
            return
        root.planContext = app.dynamicInterviewContextPreview(
            role.currentValue,
            seniority.currentValue,
            difficulty.currentValue,
            root.selectedMaterials(),
            useMaterial.checked ? consent.checked : false
        )
        if ((root.planContext.parts || []).length > 0)
            planContextDialog.open()
    }

    function selectedMaterials() {
        if (!useMaterial.checked) return ""
        var ids = material.currentValue ? [material.currentValue] : []
        if (useJD.checked && jd.currentValue && ids.indexOf(jd.currentValue) < 0)
            ids.push(jd.currentValue)
        return JSON.stringify(ids)
    }

    function materialsReady() {
        if (!useMaterial.checked) return true
        return consent.checked && material.currentIndex >= 0
            && app.materials[material.currentIndex].ai_access
            && (!useJD.checked || (jd.currentIndex >= 0 && app.materials[jd.currentIndex].ai_access))
    }

    // Keep long material titles and hashes out of the layout's primary row.
    // The context preview is a confirmation surface, not a raw diagnostic
    // dump: show a short human label first and put the integrity hash on its
    // own bounded line.
    function previewPartLabel(part) {
        var id = String((part && part.id) || "")
        var value = String((part && (part.label || part.id)) || "")
        // The preview is a consent surface, not a raw context dump.  Keep
        // stable human labels in the first line and put sensitive/hash
        // metadata on their own bounded lines below it.
        if (id === "policy")
            return "面试流程与 AI 使用规则"
        if (id === "question")
            return "本轮问题、岗位技能与评分要求"
        if (id === "candidate_answer")
            return "你已提交并锁定的回答"
        if (id === "interview_contract" || id === "blueprint")
            return "岗位技能与面试流程"
        if (id === "profile_context")
            return "求职意向与能力自评"
        // Match the semantic marker itself instead of relying on a particular
        // full-width/ASCII parenthesis spelling.  Values can come through a
        // QVariant bridge where punctuation is normalized.
        var hashMarker = value.indexOf("SHA-256")
        if (hashMarker >= 0)
            value = value.slice(0, hashMarker)
        var consentMarker = value.indexOf("本场确认后发送")
        if (consentMarker >= 0)
            value = value.slice(0, consentMarker)
        value = value.replace(/[（(\s]+$/, "").trim()
        if (id.indexOf("material:") === 0) {
            var colon = value.indexOf(":")
            if (colon < 0)
                colon = value.indexOf("：")
            if (colon >= 0)
                value = value.slice(colon + 1).trim()
            return "授权材料：" + value
        }
        return value.trim()
    }

    function previewPartSha(part) {
        // The context digest shown at the bottom is the integrity proof for
        // the whole request.  Per-part hashes are useful only for an
        // explicitly authorised material; showing hashes for policy and role
        // metadata makes this confirmation surface look like a log dump.
        var id = String((part && part.id) || "")
        if (id.indexOf("material:") !== 0)
            return ""
        var value = String((part && part.sha256) || "")
        if (!value) {
            var label = String((part && part.label) || "")
            var match = label.match(/SHA-256\s+([0-9a-fA-F]+)/)
            value = match ? match[1] : ""
        }
        return value ? "已校验 · SHA-256 " + value.slice(0, 8) : ""
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

    function submitAnswer() {
        var connectionId = app.interview.ai_mode === "codex" ? "codex" : providerConnection.currentValue
        if (!app.submitInterviewAnswer(answer.text, connectionId || "", includeInterviewMaterials.checked)
                && app.interview.ai_assessment_state === "consent_required")
            root.previewAI("submit", connectionId)
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

    // QML does not reliably notify bindings when a JavaScript object stored in
    // a `var` property is mutated in place.  Always publish a new score map so
    // the completion check, score labels and action button update immediately
    // after a learner moves one rubric slider.
    function setRubricScore(dimension, value) {
        var next = {}
        var current = root.rubricScores || {}
        for (var key in current) {
            // The map is created locally and only contains rubric dimensions;
            // copying its enumerable keys is sufficient and Qt's QML JS
            // runtime stays compatible with older desktop builds.
            next[key] = current[key]
        }
        next[dimension] = Math.round(value)
        root.rubricScores = next
    }

    function roleIndex(roleId) {
        var values = app.roles || []
        for (var i = 0; i < values.length; ++i) {
            if (values[i].id === roleId)
                return i
        }
        // Never silently substitute the first role when a stored preference
        // is missing or stale.  An explicit empty selection makes the setup
        // action explain what needs fixing instead of starting the wrong
        // interview blueprint.
        return -1
    }

    function refreshConfiguration() {
        var roleId = role.currentValue || ""
        if (!roleId) {
            var storedRole = (app.dashboard.role && app.dashboard.role.primary_role) || ""
            root.configuration = ({"available": false,
                                   "user_message": storedRole
                                      ? "档案中的目标岗位已不可用，请重新选择后再开始面试。"
                                      : "请选择一个目标岗位后再开始面试。"})
            return
        }
        if (typeof app.interviewConfiguration === "function")
            root.configuration = app.interviewConfiguration(roleId, seniority.currentValue, difficulty.currentValue)
        else
            root.configuration = ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    }

    function initializeSetup() {
        var saved = app.interviewPreferences()
        role.currentIndex = root.roleIndex(saved.role_id)
        seniority.currentIndex = seniority.indexOfValue(saved.seniority)
        difficulty.currentIndex = difficulty.indexOfValue(saved.difficulty)
        aiMode.currentIndex = aiMode.indexOfValue(saved.ai_mode)
        root.setupConnectionId = saved.connection_id || ""
        root.transcriptionConnectionId = saved.transcription_connection_id || ""
        root.restoreSetupConnection()
        root.restoreTranscriptionConnection()
        root.refreshConfiguration()
    }

    function saveSetup() {
        root.setupConnectionId = planConnection.currentValue || root.setupConnectionId
        app.saveInterviewPreferences({
            role_id: role.currentValue || "", seniority: seniority.currentValue || "",
            difficulty: difficulty.currentValue || "", ai_mode: aiMode.currentValue || "disabled",
            connection_id: root.setupConnectionId
        })
        root.refreshConfiguration()
    }

    function restoreSetupConnection() {
        planConnection.currentIndex = root.setupConnectionId
            ? planConnection.indexOfValue(root.setupConnectionId) : (planConnection.count ? 0 : -1)
    }

    function restoreTranscriptionConnection() {
        voiceConnection.currentIndex = root.transcriptionConnectionId
            ? voiceConnection.indexOfValue(root.transcriptionConnectionId) : (voiceConnection.count ? 0 : -1)
    }

    function clearSetupConsent() {
        useMaterial.checked = false
        useJD.checked = false
        consent.checked = false
        voiceConsent.checked = false
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

    function nonCodingFallback() {
        if (!root.configuration || !root.configuration.non_coding_fallback)
            return ({"available": false})
        return root.configuration.non_coding_fallback
    }

    function fallbackAvailable() {
        return root.configuration.available === false
               && root.nonCodingFallback().available === true
    }

    function fallbackRoundSummary(items) {
        var values = items || []
        var labels = []
        for (var i = 0; i < values.length; ++i) {
            var item = values[i] || {}
            var label = root.roundTypeText(item.type || item.round || "")
            if (item.duration_minutes !== undefined)
                label += "（" + item.duration_minutes + " 分钟）"
            labels.push(label)
        }
        return labels.length > 0 ? labels.join("、") : "无"
    }

    function fallbackCoveragePercent() {
        return Math.round(Number(root.nonCodingFallback().coverage_weight || 0) * 100)
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
        return ({self: "自评", human: "人工", ai: "AI", grader: "本地 Grader 客观", peer: "同伴", mentor: "导师"})[value]
               || "未标注"
    }

    function resultAssessmentSources(result) {
        // Python QVariantList is a QML sequence, not necessarily a JS Array.
        var evidence = result ? (result.assessment_evidence || []) : []
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
        if (sources.length === 1 && sources[0] === "grader")
            return "本地 Grader 客观分数"
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
        if (sources.length === 1 && sources[0] === "grader")
            return "本场代码分数来自本地 Grader 的当前版本公开测试；它不是 AI 或人工主观判断。"
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

    function followupLabelList(ids) {
        var linked = ids || []
        var records = root.interviewResult.followups || []
        var labels = []
        for (var i = 0; i < linked.length; ++i) {
            var label = linked[i]
            for (var j = 0; j < records.length; ++j) {
                if (records[j].followup_id === linked[i]) {
                    label = "追问 " + (j + 1)
                           + (records[j].parent_title ? "（" + records[j].parent_title + "）" : "")
                    break
                }
            }
            labels.push(label)
        }
        return labels.join("、")
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

    Component.onCompleted: {
        Qt.callLater(root.initializeSetup)
        Qt.callLater(root.syncQuestionEditors)
    }

    Connections {
        target: app
        function onBusyChanged() {
            // The worker publishes its connection result after clearing busy.
            // Continue on the next UI tick, using the stored credential once.
            if (!app.busy && root.pendingConnectionCheck)
                Qt.callLater(root.finishConnectionCheck)
        }
        function onAiStateChanged() {
            // Continue the original button action once the Codex interviewer
            // thread is ready; do not make the user click a second time.
            if (root.codexPlanPending
                    && root.visible
                    && aiMode.currentValue === "codex"
                    && app.aiStatusVariant === "connected") {
                root.codexPlanPending = false
                Qt.callLater(root.openPersonalizedPlanContext)
            }
        }
        function onInterviewPlanReady() {
            // The legacy full-plan signal is retained for old API clients,
            // but it is intentionally not rendered here.  A dynamic session
            // starts with one local opening question; exposing a frozen list
            // would contradict the one-question-at-a-time contract and can
            // leave users waiting for a provider response.
        }
        function onInterviewTranscriptReady(value) {
            // Transcription is a draft only.  Keep the answer editable and
            // require the normal "submit and lock" action before it becomes
            // interview evidence.
            if (!value)
                return
            // Dictation adds to an existing draft; never discard what the
            // candidate typed while recognition was running.
            answer.text = answer.text.trim().length ? answer.text + "\n" + value : value
            root.answerDraft = answer.text
            answer.forceActiveFocus()
        }
    }

    function toggleRecording() {
        root.showVoiceOptions = true
        if (root.voiceRecording) {
            app.stopInterviewRecording()
        } else if ((root.usingLocalStt && (!app.localStt.ready || !app.localStt.runtime_available || app.localStt.downloading))
                   || (!root.usingLocalStt && !voiceConsent.checked)) {
            root.showVoiceSettings = true
        } else {
            if (app.startInterviewDictation(voiceConnection.currentValue, voiceConsent.checked))
                root.showVoiceSettings = false
            voiceConsent.checked = false
        }
        Qt.callLater(function() {
            questionContent.forceLayout()
            questionScroll.contentItem.contentY = Math.min(voicePanel.y,
                Math.max(0, questionContent.height - questionScroll.availableHeight))
        })
    }

    Timer {
        interval: 1000
        repeat: true
        running: app.interview.status === "active" && app.interview.expired !== true
        onTriggered: app.refreshInterviewClock()
    }

    RowLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: root.compactInterviewLayout ? 12 : 24
        anchors.bottomMargin: 12
        width: Math.min(root.width - (root.compactInterviewLayout ? 32 : 64),
                        root.codingQuestion ? 920 : root.theme ? root.theme.readingWidth : 760)
        spacing: 0
        clip: true

        LabCard {
            id: leftPanel
            visible: setupVisible
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.fillHeight: true
            theme: root.theme
            cardColor: "transparent"
            borderColor: "transparent"
            property bool setupVisible: !app.interview.interview_id || root.configuringNewInterview
            padding: 0

            // LabCard's default content column is intentionally lightweight
            // for static cards.  This panel has a viewport plus a persistent
            // footer, so use a local layout to allocate the viewport's
            // remaining height instead of letting its implicit content push
            // the footer below a short window.
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 10

                ScrollView {
                    id: setupScroll
                    objectName: "interviewSetupScroll"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.vertical: LabScrollBar {
                        theme: root.theme
                        objectName: "interviewSetupScrollBar"
                        x: setupScroll.width - width
                        y: setupScroll.topPadding
                        height: setupScroll.availableHeight
                        policy: setupScroll.contentHeight > setupScroll.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                    }

                Column {
                    width: setupScroll.availableWidth - 12
                    spacing: 14
                    LabText { width: parent.width; theme: root.theme; text: "为下一次真实面试，做好准备。"; variant: "title"; strong: true; wrapMode: Text.Wrap }
                    LabText { width: parent.width; theme: root.theme; text: "从你的经历出发，一问一答，逐步深入。"; tone: "muted"; wrapMode: Text.Wrap }
                    Flow {
                        width: parent.width
                        spacing: 14
                        Repeater {
                            model: ["01  自我介绍", "02  经历深挖", "03  岗位原理", "04  手撕验证"]
                            delegate: LabText {
                                required property string modelData
                                theme: root.theme; text: modelData; variant: "caption"; tone: "muted"
                            }
                        }
                    }
                    LabDivider { width: parent.width; theme: root.theme }
                    LabText { theme: root.theme; text: "面试目标"; variant: "section"; strong: true }
                    LabText { theme: root.theme; text: "目标岗位"; variant: "caption"; tone: "muted" }
                    LabComboBox { theme: root.theme; id: role; objectName: "interviewRoleSelector"; width: parent.width; textRole: "title"; valueRole: "id"; model: app.roles; currentIndex: -1; onActivated: root.saveSetup() }
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 8
                        LabText { theme: root.theme; text: "求职阶段"; variant: "caption"; tone: "muted" }
                        LabText { theme: root.theme; text: "难度"; variant: "caption"; tone: "muted" }
                        LabComboBox { theme: root.theme; id: seniority; objectName: "interviewSenioritySelector"; Layout.fillWidth: true; Layout.minimumWidth: 0; model: [{id:"intern", label:"实习"}, {id:"new_grad", label:"校招"}, {id:"mid", label:"有经验"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.saveSetup() }
                        LabComboBox { theme: root.theme; id: difficulty; objectName: "interviewDifficultySelector"; Layout.fillWidth: true; Layout.minimumWidth: 0; model: [{id:"easy", label:"基础"}, {id:"medium", label:"标准"}, {id:"hard", label:"高压"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.saveSetup() }
                    }
                    Text {
                        objectName: "interviewDifficultyHint"
                        visible: leftPanel.setupVisible
                        width: parent.width
                        text: {
                            if (!role.currentValue)
                                return "请选择这次准备面试的岗位。"
                            if (aiMode.currentValue !== "disabled")
                                return "难度用于调整 AI 追问强度；不要求该档位有完整固定题单。"
                            return "选择面试官后即可开始；不连接 AI 仍可继续刷题。"
                        }
                        color: root.colors.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    LabDivider { width: parent.width; theme: root.theme }
                    LabText { visible: leftPanel.setupVisible; theme: root.theme; text: "面试官与背景"; variant: "section"; strong: true }
                    LabComboBox {
                        theme: root.theme
                        visible: leftPanel.setupVisible
                        id: aiMode
                        objectName: "interviewAiModeSelector"
                        width: parent.width
                        model: [{id:"disabled", label:"手动 / 无 AI"}, {id:"provider", label:"普通 LLM API"}, {id:"codex", label:"Codex"}]
                        textRole: "label"
                        valueRole: "id"
                        onActivated: {
                            root.saveSetup()
                            if (currentValue === "codex"
                                    && !app.codexAvailable
                                    && !app.codexProbeRunning)
                                app.refreshCodexAvailability()
                        }
                    }
                    Text {
                        objectName: "noAiInterviewNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "disabled"
                        text: "模拟面试需要 AI 才能进行真实追问和证据化复盘。No-AI 模式仍可继续刷题、运行测试、复盘和间隔复测；不会创建虚假的 Session、评分或报告。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    LabCard {
                        objectName: "noAiInterviewLockPanel"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "disabled"
                        padding: 12
                        cardColor: root.colors.surfaceAlt
                        borderColor: root.colors.border
                        theme: root.theme
                        Text {
                            width: parent.width
                            text: "个性化模拟面试已锁定"
                            color: root.colors.text
                            font.bold: true
                            wrapMode: Text.Wrap
                        }
                        Text {
                            width: parent.width
                            text: "接入普通 LLM、配置本地 Ollama 或连接 Codex 后，才能根据你的回答进行追问和证据化复盘。AI 连接不是刷题的前置条件。"
                            color: root.colors.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 11
                        }
                        Flow {
                            width: parent.width
                            spacing: 6
                            LabButton {
                                theme: root.theme
                                variant: "primary"
                                objectName: "goToConnectionsFromInterview"
                                text: "打开 AI 连接"
                                onClicked: app.navigate("connections")
                            }
                            LabButton {
                                theme: root.theme
                                objectName: "continueNoAiPractice"
                                text: "继续刷题"
                                onClicked: app.navigate("learn")
                            }
                        }
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "codex"
                        objectName: "personalizedInterviewCodexStatus"
                        text: app.aiStatusVariant === "connected"
                              ? "Codex 面试官已连接。确认后立即进入本地开场题；提交回答后再由 Codex 根据证据逐步追问。"
                              : (app.codexAvailable
                                 ? "确认后会先进入本地开场题；提交回答时再调用 Codex。你也可以先在设置中选择模型和推理强度。"
                                 : "尚未发现 Codex。请在 AI 连接页检查安装/登录状态；普通 LLM API 也可单独使用。")
                        color: app.aiStatusVariant === "connected" ? root.colors.success : root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    ColumnLayout {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "codex"
                        spacing: 8
                        Text {
                            objectName: "personalizedInterviewCodexPreferences"
                            Layout.fillWidth: true
                            text: "本场 Codex：" + (app.codexModel || "默认模型")
                                  + " · 推理强度：" + (app.codexReasoningEffort || "默认")
                            color: root.colors.muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        LabButton {
                            objectName: "openCodexPreferencesFromInterview"
                            theme: root.theme
                            variant: "ghost"
                            compact: true
                            text: "设置模型与推理强度"
                            onClicked: app.navigate("settings")
                        }
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                        text: "AI 连接"
                        color: root.colors.muted
                        font.pixelSize: 12
                    }
                    LabComboBox {
                        theme: root.theme
                        id: planConnection
                        objectName: "personalizedInterviewConnection"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                        model: app.connections
                        textRole: "display_name"
                        valueRole: "connection_id"
                        onActivated: root.saveSetup()
                        onModelChanged: Qt.callLater(root.restoreSetupConnection)
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                                 && (planConnection.currentIndex < 0
                                     || !root.providerIsReady(planConnection.currentValue))
                        text: planConnection.currentIndex < 0
                              ? (root.setupConnectionId
                                 ? "上次使用的连接已删除或不在当前档案中。请选择其他连接，或到 AI 连接页重新配置。"
                                 : "尚未选择 AI 连接，请先到 AI 连接页保存一个连接。")
                              : "已保存的连接可以直接复用；点击开始后会先检测，无需重新填写 Key。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    CheckBox {
                        id: useMaterial
                        objectName: "interviewUseMaterials"
                        width: parent.width
                        visible: leftPanel.setupVisible
                        enabled: aiMode.currentValue !== "disabled" && app.materials.length > 0
                        text: "使用求职材料（可选）"
                        contentItem: Text {
                            text: useMaterial.text
                            font: useMaterial.font
                            color: useMaterial.enabled ? root.colors.text : root.colors.muted
                            leftPadding: useMaterial.indicator.width + useMaterial.spacing
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    LabComboBox {
                        theme: root.theme
                        id: material
                        objectName: "interviewPrimaryMaterial"
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        model: app.materials
                        textRole: "title"
                        valueRole: "id"
                    }
                    CheckBox {
                        id: useJD
                        objectName: "interviewUseAdditionalMaterial"
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        text: "再选择一份 JD / 补充经历材料"
                    }
                    LabComboBox {
                        id: jd
                        objectName: "interviewAdditionalMaterial"
                        theme: root.theme
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked && useJD.checked
                        model: app.materials
                        textRole: "title"
                        valueRole: "id"
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked && useJD.checked && jd.currentIndex >= 0
                        text: jd.currentIndex >= 0 ? "补充材料：" + app.materials[jd.currentIndex].id
                              + " · SHA " + app.materials[jd.currentIndex].sha256.slice(0, 12)
                              + (app.materials[jd.currentIndex].ai_access ? "" : "\n请先在求职材料页允许此材料供 AI 使用。") : ""
                        color: root.colors.muted
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 12
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked && material.currentIndex >= 0
                        text: material.currentIndex >= 0 ? "材料 ID：" + app.materials[material.currentIndex].id + "\n用途：role_interview\nSHA-256：" + app.materials[material.currentIndex].sha256 : ""
                        color: root.colors.muted
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                    }
                    Text {
                        objectName: "personalizedInterviewMaterialAccessNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && !app.materials[material.currentIndex].ai_access
                        text: "这份材料尚未允许 AI 使用。点击下方按钮后，系统会在本机重新提取 PDF/DOCX 文本并绑定当前文件 SHA；提取失败时仍保持本地保存。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Button {
                        objectName: "openMaterialsForInterviewAuthorization"
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && !app.materials[material.currentIndex].ai_access
                        text: "允许此材料供 AI 使用"
                        flat: true
                        enabled: !app.busy
                        onClicked: app.setMaterialAiAccess(material.currentValue, true)
                    }
                    CheckBox {
                        id: consent
                        objectName: "interviewMaterialConsent"
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        text: "允许本场面试使用所选材料"
                        contentItem: Text {
                            text: consent.text
                            font: consent.font
                            color: root.colors.text
                            leftPadding: consent.indicator.width + consent.spacing
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Text {
                        objectName: "personalizedInterviewConsentNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && app.materials[material.currentIndex].ai_access
                                 && !consent.checked
                        text: "请勾选上方授权后，Codex 才会读取这份材料；未勾选不会发送。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "interviewConfigurationMessage"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
                                 && root.configuration.available === false
                        text: root.configurationMessage()
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    Button {
                        objectName: "startNonCodingInterview"
                        width: parent.width
                        visible: false
                        text: app.busy ? "正在准备专项面试……" : "开始非代码专项面试"
                        highlighted: true
                        enabled: root.fallbackAvailable()
                                 && !!role.currentValue
                                 && !app.busy
                                 && aiMode.currentValue !== "disabled"
                                 && (!useMaterial.checked || (material.currentIndex >= 0 && app.materials[material.currentIndex].ai_access && consent.checked))
                        onClicked: nonCodingInterviewDialog.open()
                    }
                    Text {
                        objectName: "interviewPyTorchEnvironmentHelp"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
                                 && (root.configuration.missing_environment || []).indexOf("pytorch") >= 0
                        text: "完整蓝图需要源码 PyTorch 环境。桌面应用不会自行安装依赖。需先克隆源码并进入仓库根目录，再运行：\npython -m pip install -e \".[torch,dev]\""
                        color: root.colors.muted
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "interviewSourceEnvironmentLink"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
                                 && (root.configuration.missing_environment || []).indexOf("pytorch") >= 0
                        text: "<a href=\"https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md\">查看源码环境说明</a>"
                        textFormat: Text.RichText
                        color: root.colors.accent
                        font.pixelSize: 11
                        onLinkActivated: Qt.openUrlExternally(link)
                    }
                    Text {
                        objectName: "dynamicInterviewStatus"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "disabled"
                                 && app.interviewPlanPreview.status === "starting"
                        text: app.interviewPlanPreview.user_message || "正在进入面试……"
                        color: root.colors.accent
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "personalizedInterviewAlphaScope"
                        width: parent.width
                        visible: false
                        text: "AI 会依据岗位蓝图、canonical skills、求职级别和难度生成结构化问题；材料是可选上下文。Coding 环节只使用当前环境可运行的已验证本地题，不满足时会在计划中明确省略。"
                        color: root.colors.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "dynamicInterviewScope"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue !== "disabled"
                        text: "先自我介绍，再围绕你的经历深入追问、考察岗位原理，最后从当前可运行的本地题目中选择手撕题。AI 每次只生成下一问；没有可用代码题时会明确标记未完成环节。"
                        color: root.colors.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    LabButton {
                        visible: root.configuringNewInterview
                        theme: root.theme
                        variant: "ghost"
                        text: "返回上一场结果"
                        onClicked: root.configuringNewInterview = false
                    }
                    Text { width: parent.width; text: "面试结果仅用于复盘，不改变刷题训练的掌握状态。"; color: root.colors.muted; wrapMode: Text.Wrap; font.pixelSize: root.theme ? root.theme.fontCaption : 12 }
                }
            }
                LabDivider { theme: root.theme; Layout.fillWidth: true }
                LabText {
                    objectName: "dynamicInterviewError"
                    theme: root.theme
                    Layout.fillWidth: true
                    visible: app.interviewPlanPreview.status === "error"
                             || (aiMode.currentValue === "provider" && (app.connectionError || "").length > 0)
                    text: app.interviewPlanPreview.status === "error"
                          ? app.interviewPlanPreview.user_message + "\n" + app.interviewPlanPreview.recommended_action
                          : app.connectionError
                    tone: "danger"; variant: "caption"; wrapMode: Text.Wrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    LabText {
                        theme: root.theme
                        text: setupScroll.contentItem.contentY + setupScroll.availableHeight < setupScroll.contentHeight - 8
                              ? "向下滚动，查看其余设置 ↓"
                              : aiMode.currentValue === "disabled" ? "接入 AI 后开始；刷题仍可离线使用。"
                              : "开始前，你可以确认本场发送范围。"
                        variant: "caption"; tone: "muted"; wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    LabButton {
                        objectName: "startConfiguredInterview"
                        theme: root.theme
                        variant: "primary"
                        Layout.alignment: Qt.AlignRight
                        visible: leftPanel.setupVisible && aiMode.currentValue !== "disabled"
                        text: root.pendingConnectionCheck ? "正在检测已保存连接……" : app.busy ? "正在进入面试……" : "开始面试"
                        enabled: !!role.currentValue
                                 && !app.busy
                                 && ((aiMode.currentValue === "provider"
                                      && planConnection.currentIndex >= 0)
                                      || aiMode.currentValue === "codex")
                                 && root.materialsReady()
                        // Confirm only the explicit first-turn context. Future
                        // questions are generated after the current answer.
                        onClicked: root.prepareInterview()
                    }
                }
        }
        }

        LabCard {
            objectName: "interviewConversation"
            visible: !leftPanel.setupVisible
            theme: root.theme
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.fillHeight: true
            clip: true
            cardColor: "transparent"
            borderColor: "transparent"
            padding: 0
            // The question viewport and the persistent finish action need real
            // remaining-space allocation.  LabCard intentionally uses a plain
            // Column for simple cards, so this interview panel owns a local
            // ColumnLayout rather than relying on ignored Layout.fillHeight
            // hints inside that Column.
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                LabText {
                    theme: root.theme
                    visible: !root.interviewFinished
                    objectName: "interviewQuestionPosition"
                    text: root.dynamicInterview ? "第 " + (app.interview.total_questions || 1) + " 问 · 逐问面试" : "限时面试"
                    variant: "caption"
                    tone: "muted"
                    Layout.alignment: Qt.AlignVCenter
                }
                Item { Layout.fillWidth: true }
                StatusPill {
                    theme: root.theme
                    // Keep the existing test/accessibility hook while moving
                    // the phase marker next to the question title.
                    objectName: "interviewPhasePill"
                    visible: !root.dynamicInterview && !!activeQuestion && app.interview.status === "active"
                    text: root.answerLocked ? "回答已锁定" : "正在回答"
                    tone: root.colors.muted
                    style: "plain"
                    showDot: false
                }
                StatusPill {
                    objectName: "interviewTimerPill"
                    theme: root.theme
                    visible: !!app.interview.interview_id
                    text: app.interview.status === "active"
                          ? root.timerText(app.interview.remaining_seconds)
                          : root.statusText(app.interview.status)
                    tone: app.interview.expired === true ? root.colors.warning : root.colors.muted
                    style: "plain"
                    showDot: false
                }
                LabButton {
                    theme: root.theme
                    variant: "ghost"
                    compact: true
                    visible: app.interview.status === "active" || app.interview.status === "paused"
                    text: app.interview.status === "paused" ? "恢复计时" : "暂停"
                    enabled: !app.busy
                    onClicked: app.interview.status === "paused"
                               ? app.resumeInterview() : pauseInterviewDialog.open()
                }
                }
                ScrollView {
                id: questionScroll
                objectName: "interviewQuestionScroll"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                // Keep the question column tied to the panel viewport.  Without
                // an explicit content width, Qt sizes the Flickable content to
                // the TextArea's implicit width, leaving the editor as a narrow
                // strip and making the phase controls collide on small screens.
                contentWidth: availableWidth
                ScrollBar.vertical: LabScrollBar {
                    theme: root.theme
                    objectName: "interviewQuestionScrollBar"
                    x: questionScroll.width - width
                    y: questionScroll.topPadding
                    height: questionScroll.availableHeight
                    policy: questionScroll.contentHeight > questionScroll.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                }
                Column {
                    id: questionContent
                    width: questionScroll.availableWidth - 12
                    spacing: 18
                    LabText {
                        width: parent.width
                        theme: root.theme
                        visible: !root.dynamicInterview
                        text: activeQuestion ? (activeQuestion.kind === "coding" ? "代码题" : "面试官") : "面试复盘"
                        variant: "caption"
                        tone: "muted"
                    }
                    LabText {
                        objectName: "interviewExpiryNotice"
                        theme: root.theme
                        width: parent.width
                        visible: app.interview.expired === true
                        text: "本场计时已到。请点击“结束本场”，保存已有回答与复盘结果。"
                        tone: "warning"
                        wrapMode: Text.Wrap
                    }
                    LabText {
                        objectName: "interviewQuestionTitle"
                        visible: true
                        width: parent.width
                        theme: root.theme
                        text: activeQuestion ? (root.codingQuestion && !root.showEnglishQuestion
                                               ? app.problemTitle(activeQuestion.source.id, activeQuestion.title)
                                               : activeQuestion.title)
                              : root.interviewFinished ? "本场复盘"
                              : app.interview.expired ? "本场已到时" : "本场作答已完成"
                        variant: "title"
                        strong: true
                        font.pixelSize: root.theme ? root.theme.fontTitle : 26
                        wrapMode: Text.Wrap
                    }
                    LabText {
                        objectName: "interviewCodingSelectionNotice"
                        theme: root.theme
                        width: parent.width
                        visible: root.codingQuestion && app.interview.coding_selection_corrected === true
                        text: "AI 建议的题目不在本地可运行范围内，已按本场技能改选当前真实题目，可以直接作答。"
                        tone: "muted"
                        wrapMode: Text.Wrap
                    }
                    Text {
                        objectName: "interviewQuestionPrompt"
                        visible: !root.codingQuestion || root.showCodingPrompt
                        width: parent.width
                        // Markdown's default implicit height does not include
                        // the complete custom paragraph leading on Qt/Windows.
                        height: contentHeight
                        text: activeQuestion ? (root.codingQuestion && !root.showEnglishQuestion
                                               ? app.problemStatement(activeQuestion.source.id, activeQuestion.prompt)
                                               : root.codingQuestion ? activeQuestion.prompt.replace(/^#[^\n]+\n+/, "") : activeQuestion.prompt)
                              : root.interviewFinished ? "下面汇总已记录的回答与评估依据。缺少的环节不会作为已完成计入。"
                              : "点击「结束并查看复盘」保存本场结果；完成情况以实际回答和测试证据为准。"
                        color: root.colors.text
                        font.family: root.theme ? root.theme.uiFontFamily : ""
                        font.pixelSize: root.theme ? root.theme.fontBodyLarge : 15
                        wrapMode: Text.Wrap
                        textFormat: Text.MarkdownText
                        lineHeight: 1.4
                    }
                    LabButton {
                        objectName: "toggleInterviewQuestionLanguage"
                        theme: root.theme
                        visible: root.codingQuestion && root.showCodingPrompt
                                 && (root.activeQuestion.prompt || "").indexOf("\n## 任务\n") < 0
                        text: root.showEnglishQuestion ? "查看中文题目" : "查看英文题目"
                        compact: true
                        variant: "ghost"
                        onClicked: root.showEnglishQuestion = !root.showEnglishQuestion
                    }
                    Item {
                        id: answerInlineHost
                        width: parent.width
                        height: visible ? (root.compactInterviewLayout ? 156 : 196) : 0
                        visible: !!activeQuestion && !root.codingQuestion && !root.dynamicInterview
                    }
                    ScrollView {
                        id: replyViewport
                        objectName: "interviewReplyViewport"
                        // Keep the editor inside its ScrollView so Qt follows
                        // the caret during typing, selection and IME input.
                        parent: root.dynamicInterview ? replySlot : answerInlineHost
                        width: parent.width
                        height: parent.height
                        contentWidth: availableWidth
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical: LabScrollBar {
                            theme: root.theme
                            objectName: "interviewReplyScrollBar"
                            x: replyViewport.width - width
                            y: replyViewport.topPadding
                            height: replyViewport.availableHeight
                            policy: replyViewport.contentHeight > replyViewport.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                        }
                        LabTextArea {
                            id: answer
                            objectName: "interviewAnswerEditor"
                            theme: root.theme
                            composer: true
                            width: replyViewport.availableWidth
                            height: Math.max(replyViewport.availableHeight, implicitHeight)
                            visible: !!activeQuestion && activeQuestion.kind !== "coding"
                            text: root.answerLocked ? (app.interview.answer_text || "") : root.answerDraft
                            readOnly: root.answerLocked || !root.interviewCanEdit
                            onTextChanged: if (!root.answerLocked && !root.syncingQuestionEditors) root.answerDraft = text
                            placeholderText: root.answerLocked ? "回答已锁定" : !root.interviewCanEdit ? "面试已暂停或结束" : "输入你的回答……"
                            background: Rectangle {
                                color: root.dynamicInterview ? "transparent" : root.theme.surfaceRaised
                                radius: root.theme.composerRadius
                                border.color: root.dynamicInterview ? "transparent"
                                              : answer.activeFocus ? root.theme.focusRing : root.theme.borderDefault
                            }
                        }
                    }
                    LabButton {
                        theme: root.theme
                        variant: "ghost"
                        visible: !root.dynamicInterview && !!activeQuestion && activeQuestion.kind !== "coding" && !root.answerLocked
                        compact: true
                        text: root.voiceActionText
                        enabled: root.interviewCanEdit && !root.voiceTranscribing && (!app.busy || root.voiceRecording)
                        onClicked: root.toggleRecording()
                    }
                    LabCard {
                        id: voicePanel
                        objectName: "interviewVoiceCard"
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && root.interviewCanEdit && root.showVoiceOptions
                        width: parent.width
                        cardColor: root.colors.surfaceAlt
                        borderColor: app.interviewVoice.state === "recording"
                                      ? root.colors.warning : root.colors.border
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: root.voiceRecording ? "正在听，请说话…"
                                          : root.voiceTranscribing ? "正在转成文字…"
                                          : app.interviewVoice.transcription_state === "transcribed" ? "已添加到回答框" : "语音输入"
                                    color: root.colors.text
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                Text {
                                    objectName: "interviewVoiceDuration"
                                    visible: root.voiceRecording || root.voiceTranscribing
                                    text: {
                                        var seconds = Math.floor(Number(app.interviewVoice.duration_ms || 0) / 1000)
                                        return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60
                                    }
                                    color: root.colors.muted
                                    font.pixelSize: 12
                                    font.family: root.codeFontFamily
                                }
                                StatusPill {
                                    objectName: "interviewVoiceState"
                                    text: app.interviewVoice.state === "recording"
                                          ? "录音中"
                                          : app.interviewVoice.transcription_state === "transcribing"
                                            ? "转录中" : app.interviewVoice.transcription_state === "transcribed"
                                              ? "已转录" : app.interviewVoice.state === "error" ? "录音失败"
                                            : app.interviewVoice.audio_ready ? "已录音" : "未开始"
                                    tone: app.interviewVoice.state === "recording"
                                          ? root.colors.warning : root.colors.muted
                                }
                                LabButton {
                                    objectName: "interviewVoiceSettings"
                                    theme: root.theme; compact: true; variant: "ghost"
                                    text: root.showVoiceSettings ? "收起设置" : "语音设置"
                                    enabled: !root.voiceRecording && !root.voiceTranscribing
                                    onClicked: root.showVoiceSettings = !root.showVoiceSettings
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.usingLocalStt
                                      ? "结束录音后自动在本机转成文字，不上传音频。你可以修改后再提交。"
                                      : "远程转录需本次授权，录音结束后自动转文字。文字追加到回答框，不会自动提交。"
                                color: root.colors.muted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                            Text {
                                objectName: "interviewVoiceError"
                                visible: !!app.interviewVoice.error
                                Layout.fillWidth: true
                                text: app.interviewVoice.error || ""
                                color: root.colors.danger
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }
                            LabButton {
                                objectName: "transcribeInterviewRecording"
                                theme: root.theme; compact: true
                                visible: app.interviewVoice.audio_ready && !root.voiceTranscribing
                                         && app.interviewVoice.transcription_state !== "transcribed"
                                text: "重试转成文字"
                                enabled: !app.busy && (root.usingLocalStt
                                    ? app.localStt.ready && app.localStt.runtime_available && !app.localStt.downloading
                                    : voiceConsent.checked)
                                onClicked: {
                                    app.transcribeInterviewRecording(voiceConnection.currentValue, voiceConsent.checked)
                                    voiceConsent.checked = false
                                }
                            }
                            ColumnLayout {
                                visible: root.showVoiceSettings
                                Layout.fillWidth: true
                                spacing: 8
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 1
                                    ComboBox {
                                        id: voiceConnection
                                        objectName: "interviewVoiceConnection"
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        model: app.interviewTranscriptionOptions
                                        textRole: "display_name"
                                        valueRole: "connection_id"
                                        displayText: currentIndex < 0 ? "请选择语音转录连接" : currentText
                                        enabled: !root.voiceTranscribing && !root.voiceRecording
                                        onModelChanged: Qt.callLater(root.restoreTranscriptionConnection)
                                        onActivated: {
                                            voiceConsent.checked = false
                                            root.transcriptionConnectionId = currentValue || ""
                                            app.saveInterviewPreferences({transcription_connection_id: root.transcriptionConnectionId})
                                        }
                                    }
                                    CheckBox {
                                        id: voiceConsent
                                        objectName: "interviewVoiceRemoteConsent"
                                        visible: !root.usingLocalStt
                                        text: "本次允许将录音发送到所选服务转录"
                                        enabled: voiceConnection.currentIndex >= 0 && !root.voiceTranscribing && !root.voiceRecording
                                    }
                                }
                                ColumnLayout {
                                    visible: root.usingLocalStt
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Text {
                                        objectName: "interviewLocalSttStatus"
                                        Layout.fillWidth: true
                                        text: !app.localStt.runtime_available
                                              ? "当前环境缺少本地语音组件，请按桌面指南更新 desktop 依赖。"
                                              : app.localStt.downloading
                                                ? "正在下载本地模型：" + app.localStt.progress + "%（不会上传录音）"
                                                : app.localStt.ready
                                                  ? "本地模型已下载 · 无需联网或 Key；首次识别会加载模型。"
                                                  : "首次需下载约 " + app.localStt.download_mb + " MB 模型，之后可离线转录中文或英文。"
                                        color: root.colors.muted
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                    ProgressBar {
                                        Layout.fillWidth: true
                                        visible: app.localStt.downloading
                                        from: 0; to: 100; value: app.localStt.progress
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        LabButton {
                                            objectName: "downloadLocalSttModel"
                                            theme: root.theme
                                            compact: true
                                            text: app.localStt.ready ? "检查 / 重新下载模型" : "下载本地模型"
                                            enabled: !app.localStt.downloading && app.localStt.runtime_available
                                                     && app.interviewVoice.transcription_state !== "transcribing"
                                            onClicked: app.downloadLocalSttModel()
                                        }
                                        LabButton {
                                            objectName: "cancelLocalSttDownload"
                                            theme: root.theme
                                            compact: true
                                            text: "取消下载"
                                            visible: app.localStt.downloading
                                            onClicked: app.cancelLocalSttDownload()
                                        }
                                        Item { Layout.fillWidth: true }
                                    }
                                    Text {
                                        objectName: "interviewLocalSttDownloadError"
                                        visible: !!app.localStt.error
                                        Layout.fillWidth: true
                                        text: app.localStt.error || ""
                                        color: root.colors.danger
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "SenseVoiceSmall：FunAudioLLM / Alibaba；ONNX 由 k2-fsa 转换。点击下载表示同意 <a href='" + app.localStt.license_url + "'>模型使用许可</a>。"
                                        textFormat: Text.RichText
                                        color: root.colors.muted
                                        linkColor: root.colors.accent
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                                    }
                                }
                                Text {
                                    objectName: "interviewTranscriptionAvailability"
                                    visible: !root.usingLocalStt
                                    Layout.fillWidth: true
                                    text: "远程转录使用 whisper-1，服务需支持 /audio/transcriptions。DeepSeek 仅用于文字面试，也可直接搭配上方的本地转录；选择本地时不需要远程授权。"
                                    color: root.colors.muted
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                    LabCard {
                        objectName: "interviewAnswerCorruption"
                        visible: !!app.interview.answer_corrupted
                        width: parent.width
                        cardColor: root.colors.surfaceAlt
                        borderColor: root.colors.danger
                        Text { width: parent.width; text: app.interview.answer_error || "已锁定的回答当前不可读取，评分已暂停。"; color: root.colors.danger; wrapMode: Text.Wrap; font.bold: true }
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && answer.text.trim().length === 0
                        width: parent.width
                        text: root.voiceRecording ? "说完后点击「完成录音」，文字会自动填入下方。"
                              : root.voiceTranscribing ? "正在识别，完成后可编辑文字再提交。"
                              : "输入回答，或点击「语音输入」开始口述。"
                        color: root.colors.muted
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                    Column {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
                        width: parent.width
                        spacing: 6
                        Text { text: "候选人自评 Rubric（每个维度 1–5 分）"; color: root.colors.muted; font.bold: true }
                        Text { text: "用于自我校准，不代表客观面试结论。请点击每个滑块选择分数，未评分项不会提交。"; color: root.colors.muted; font.pixelSize: 11; wrapMode: Text.Wrap; width: parent.width }
                        Repeater {
                            model: activeQuestion ? Object.keys(activeQuestion.rubric.dimensions) : []
                            delegate: RowLayout {
                                required property string modelData
                                width: parent.width
                                Text { text: modelData.replace(/_/g, " "); color: root.colors.text; Layout.preferredWidth: 190 }
                                Slider {
                                    id: dimensionScore
                                    // Zero is a presentation-only placeholder.
                                    // A rubric score is published only after an
                                    // explicit drag/click, so an untouched
                                    // slider can never look like a score of 1.
                                    from: 0; to: 5; stepSize: 1; value: 0
                                    Layout.fillWidth: true
                                    Accessible.name: modelData.replace(/_/g, " ") + "自评分数"
                                    Accessible.description: "点击或拖动选择 1 到 5 分"
                                    // A click on the initial value (1) may not
                                    // emit valueChanged. Record the press too,
                                    // so choosing the lowest score is still an
                                    // explicit, valid assessment.
                                    onPressedChanged: if (pressed && value >= 1) root.setRubricScore(modelData, Math.round(value))
                                    enabled: root.interviewCanEdit
                                    onValueChanged: if ((pressed || activeFocus) && value >= 1) root.setRubricScore(modelData, Math.round(value))
                                }
                                Text { text: root.rubricScores[modelData] === undefined ? "未评分" : root.rubricScores[modelData] + " / 5"; color: root.colors.text; font.bold: true; Layout.preferredWidth: 54 }
                            }
                        }
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
                        text: "回答证据 · 必填"
                        color: root.colors.text
                        font.bold: true
                        font.pixelSize: 13
                        width: parent.width
                    }
                    LabTextArea {
                        id: evidence
                        objectName: "interviewEvidenceEditor"
                        theme: root.theme
                        width: parent.width
                        height: 86
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
                        enabled: root.interviewCanEdit
                        placeholderText: root.interviewCanEdit ? "请引用回答中的具体证据（必填）" : "面试已暂停或结束"
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted
                                 && app.interview.ai_mode === "provider"
                                 && providerConnection.currentIndex >= 0
                                 && !root.providerIsReady(providerConnection.currentValue)
                        width: parent.width
                        text: root.dynamicInterview
                              ? "当前连接尚未测试通过。请到“AI 连接”完成测试，再返回生成下一问。"
                              : "当前连接尚未测试通过。请到“AI 连接”测试后再请求评估，或改用人工评分。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted
                                 && app.interview.ai_mode === "provider"
                                 && providerConnection.currentIndex < 0
                        width: parent.width
                        text: root.dynamicInterview
                              ? "还没有可用的已测试连接。请到“AI 连接”保存并测试服务，再返回继续面试。"
                              : "还没有可用的已测试连接；可以去 AI 连接页配置，或直接记录人工评分。"
                        color: root.colors.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    LabCard {
                        visible: !!app.interview.pending_followup
                        width: parent.width
                        cardColor: root.colors.surfaceAlt
                        borderColor: root.colors.accent
                        Text { width: parent.width; text: "自适应追问\n" + (app.interview.pending_followup || ""); color: root.colors.text; wrapMode: Text.Wrap; font.bold: true }
                        LabTextArea { id: followupAnswer; objectName: "interviewFollowupEditor"; theme: root.theme; width: parent.width; height: 100; enabled: root.interviewCanEdit; placeholderText: root.interviewCanEdit ? "回答这一个追问" : "面试已暂停或结束" }
                        Text {
                            width: parent.width
                            text: "追问回答会留档并关联到本题评估；当前评分仍采用主回答生成的 AI 评估，不会根据这次追问自动重算。"
                            color: root.colors.muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        Button {
                            text: "记录追问回答并采用已有评估"
                            highlighted: true
                            enabled: root.interviewCanEdit && followupAnswer.text.trim().length > 0 && !app.busy
                            onClicked: app.answerAIFollowup(followupAnswer.text)
                        }
                    }
                    LabCard {
                        objectName: "interviewResultCard"
                        visible: Object.keys(root.interviewResult).length > 0
                        width: parent.width
                        theme: root.theme
                        cardColor: "transparent"
                        borderColor: "transparent"
                        padding: 0
                        Rectangle {
                            width: parent.width
                            height: reportSummary.implicitHeight + 40
                            radius: root.theme.radiusLarge
                            color: root.theme.surfaceSunken
                            RowLayout {
                                id: reportSummary
                                x: 20; y: 20; width: parent.width - 40
                                spacing: 24
                                LabText {
                                    objectName: "interviewResultScore"
                                    theme: root.theme
                                    text: root.resultScoreText(root.interviewResult)
                                    strong: true
                                    font.pixelSize: root.theme.scaledPx(36)
                                }
                                Text {
                                    Layout.fillWidth: true
                                    objectName: "interviewResultSummary"
                                    text: root.resultScoreLabel(root.interviewResult)
                                          + (root.resultAssessmentSources(root.interviewResult).length > 0 ? " · 满分 100" : "")
                                          + "\n" + root.statusText(root.interviewResult.completion_status)
                                    color: root.colors.text
                                    font.pixelSize: root.theme.fontBody
                                    wrapMode: Text.Wrap
                                    lineHeight: 1.5
                                }
                            }
                        }
                        Text {
                            objectName: "interviewFallbackResultScope"
                            width: parent.width
                            visible: root.interviewResult.delivery_mode === "non_coding_fallback"
                            text: "非代码专项 · 蓝图证据覆盖 "
                                  + Math.round(Number((root.interviewResult.blueprint_coverage || {}).coverage_weight || 0) * 100)
                                  + "%\n省略代码实现轮次："
                                  + root.fallbackRoundSummary((root.interviewResult.blueprint_coverage || {}).omitted_rounds)
                            color: root.colors.warning
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            visible: root.resultSourceNote(root.interviewResult).length > 0
                            text: root.resultSourceNote(root.interviewResult)
                            color: root.colors.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                        Text {
                            width: parent.width
                            visible: !!root.interviewResult.summary
                            text: root.interviewResult.summary || ""
                            color: root.colors.text
                            wrapMode: Text.Wrap
                        }
                        Text { width: parent.width; text: "评分证据"; color: root.colors.muted; font.bold: true }
                        Repeater {
                            model: root.interviewResult.assessment_evidence || []
                            delegate: Rectangle {
                                required property var modelData
                                width: parent.width
                                objectName: "interviewEvidenceRow"
                                height: evidenceColumn.implicitHeight + 32
                                color: "transparent"
                                LabDivider { width: parent.width; theme: root.theme }
                                Column {
                                    id: evidenceColumn
                                    x: 0; y: 16; width: parent.width; spacing: 8
                                    Text {
                                        width: parent.width
                                        text: (modelData.title || modelData.question_id || "未命名问题")
                                              + (modelData.score === undefined || modelData.score === null ? " · 尚未评分" : " · " + modelData.score)
                                        color: root.colors.text
                                        font.pixelSize: root.theme.fontBodyLarge
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: "来源：" + root.assessmentSourceText(modelData.source)
                                              + " · 置信度：" + root.confidenceText(modelData.confidence)
                                        color: root.colors.muted
                                        font.pixelSize: root.theme.fontCaption
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        visible: (modelData.followup_ids || []).length > 0
                                        width: parent.width
                                        text: "关联追问：" + root.followupLabelList(modelData.followup_ids)
                                        color: root.colors.accent
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: modelData.evidence || "未记录评分证据。"
                                        color: root.theme.text
                                        font.pixelSize: root.theme.fontBody
                                        wrapMode: Text.Wrap
                                        lineHeight: 1.45
                                    }
                                }
                            }
                        }
                        Column {
                            visible: (root.interviewResult.followups || []).length > 0
                            width: parent.width
                            spacing: 8
                            Text { width: parent.width; text: "追问记录"; color: root.colors.muted; font.bold: true }
                            Repeater {
                                model: root.interviewResult.followups || []
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: parent.width
                                    height: followupColumn.implicitHeight + 16
                                    radius: 8
                                    color: root.colors.surface
                                    border.color: root.colors.border
                                    Column {
                                        id: followupColumn
                                        x: 10; y: 8; width: parent.width - 20; spacing: 4
                                        Text {
                                            width: parent.width
                                            text: "追问 " + (index + 1) + " · "
                                                  + (modelData.parent_title || modelData.parent_question_id || "原问题未记录")
                                            color: root.colors.accent
                                            font.bold: true
                                            wrapMode: Text.Wrap
                                        }
                                        Text { width: parent.width; text: modelData.prompt || ""; color: root.colors.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "回答：" + (modelData.answer || ""); color: root.colors.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "来源：" + root.assessmentSourceText(modelData.source); color: root.colors.muted; font.pixelSize: 11; wrapMode: Text.Wrap }
                                        Text {
                                            width: parent.width
                                            text: "记录：" + (modelData.followup_id || "未编号")
                                                  + " · " + root.recordedAtText(modelData.recorded_at)
                                            color: root.colors.muted
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
                            color: root.colors.muted
                            wrapMode: Text.Wrap
                        }
                        Text {
                            width: parent.width
                            visible: root.resultListText(root.interviewResult.critical_gaps, "").length > 0
                            text: "关键缺口：" + root.resultListText(root.interviewResult.critical_gaps, "")
                            color: root.colors.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            visible: root.resultUnscoredText(root.interviewResult).length > 0
                            text: root.resultUnscoredText(root.interviewResult)
                            color: root.colors.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            text: "该结果只记录模拟面试证据，不会改变刷题训练的掌握状态。"
                            color: root.colors.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                    }
                    ColumnLayout {
                        visible: root.codingQuestion && !root.showCodingPrompt
                        width: parent.width; spacing: 10
                        Text { text: "本场手撕代码"; color: root.colors.text; font.bold: true }
                        LabTextArea {
                            id: codingEditor
                            objectName: "interviewCodingEditor"
                            theme: root.theme
                            Layout.fillWidth: true; Layout.preferredHeight: root.compactInterviewLayout ? 210 : 260
                            text: app.interview.coding_text || ""
                            readOnly: !root.interviewCanEdit
                            color: root.colors.text
                            font.family: root.codeFontFamily
                            font.pixelSize: 13
                            wrapMode: TextEdit.NoWrap
                            padding: 12
                            clip: true
                            background: Rectangle { color: root.colors.surfaceAlt; radius: 8; border.color: root.colors.border }
                            Accessible.name: "限时代码面试编辑器"
                            onTextChanged: if (!root.syncingQuestionEditors) root.codingEditorDirty = true
                        }
                        LabText {
                            theme: root.theme
                            text: root.codingEditorDirty ? "上次测试输出（代码已修改）" : "测试输出"
                            variant: "caption"
                            tone: "muted"
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 140; radius: 8
                            color: root.colors.surfaceAlt; border.color: root.colors.border
                            ScrollView {
                                id: codingOutputScroll
                                anchors.fill: parent; anchors.margins: 10
                                contentWidth: availableWidth
                                clip: true
                                Text {
                                    objectName: "interviewCodingOutput"
                                    width: codingOutputScroll.availableWidth
                                    text: app.interview.coding_test_output || "尚未运行。点击「保存并测试」，将测试当前编辑器中的代码。"
                                    textFormat: Text.PlainText
                                    color: root.colors.text
                                    wrapMode: Text.Wrap
                                    font.family: root.codeFontFamily
                                    font.pixelSize: root.theme ? root.theme.scaledPx(12) : 12
                                }
                            }
                        }
                        Text { text: "面试进行中不会展示教学提示。代码记录只接受当前编辑器已复测的版本。"; color: root.colors.warning; font.pixelSize: 12; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                }
                ColumnLayout {
                    visible: root.codingQuestion
                    Layout.fillWidth: true
                    spacing: 8
                    LabText {
                        objectName: "interviewCodingStatus"
                        theme: root.theme
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        variant: "caption"
                        text: root.codingEditorDirty ? "代码已修改；请保存并测试，旧结果不能用于当前代码。"
                              : app.interview.coding_test_status === "running" ? "正在测试已保存的代码…"
                              : app.interview.coding_test_current === true
                                ? (app.interview.coding_test_status === "passed" ? "测试通过" : "测试未通过")
                                  + " · revision " + String(app.interview.coding_tested_revision).slice(0, 7)
                                  + " · 可以继续修改，也可记录本次结果。"
                              : app.interview.coding_test_status === "error" ? "测试未能完成，请查看输出后重试。"
                                : "运行测试会先保存当前代码。"
                        tone: root.codingEditorDirty ? "warning"
                              : app.interview.coding_test_current === true
                                ? (app.interview.coding_test_status === "passed" ? "success" : "danger") : "muted"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        LabButton {
                            objectName: "toggleInterviewCodingPrompt"
                            theme: root.theme
                            text: root.showCodingPrompt ? "开始作答" : "查看题面"
                            onClicked: {
                                root.showCodingPrompt = !root.showCodingPrompt
                                questionScroll.contentItem.contentY = 0
                                if (!root.showCodingPrompt) codingEditor.forceActiveFocus()
                            }
                        }
                        LabButton {
                            theme: root.theme
                            text: "保存"
                            variant: "ghost"
                            enabled: root.interviewCanEdit && !app.busy
                            onClicked: if (app.saveInterviewCoding(codingEditor.text)) root.codingEditorDirty = false
                        }
                        LabButton {
                            objectName: "runInterviewGrader"
                            theme: root.theme
                            variant: "primary"
                            text: app.interview.coding_test_status === "running" ? "正在测试…" : "保存并测试"
                            enabled: root.interviewCanEdit && !app.busy
                            onClicked: root.runCodingTests()
                            ToolTip.visible: hovered
                            ToolTip.text: Qt.platform.os === "osx" ? "Command+R · 测试当前编辑器代码" : "Ctrl+R · 测试当前编辑器代码"
                        }
                        LabButton {
                            objectName: "recordInterviewCodingRound"
                            theme: root.theme
                            text: "记录本轮并继续"
                            enabled: root.interviewCanEdit && !app.busy && !root.codingEditorDirty
                                     && app.interview.coding_test_current === true
                            onClicked: app.recordInterviewCodingRound()
                        }
                    }
                }
                Rectangle {
                    objectName: "interviewPhaseGuidance"
                    visible: !!activeQuestion && activeQuestion.kind !== "coding"
                    Layout.fillWidth: true
                    Layout.preferredHeight: phaseActions.implicitHeight + 24
                    radius: root.theme ? root.theme.composerRadius : 18
                    color: root.dynamicInterview ? root.theme.surfaceRaised : "transparent"
                    border.color: root.dynamicInterview
                                  ? (answer.activeFocus ? root.theme.focusRing : root.theme.borderDefault)
                                  : "transparent"
                    GridLayout {
                        id: phaseActions
                        anchors.fill: parent
                        anchors.margins: 12
                        columns: 2
                        rowSpacing: 8
                        columnSpacing: 12
                        Item {
                            id: replySlot
                            visible: root.dynamicInterview
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            Layout.preferredHeight: Math.min(root.theme.scaledPx(root.compactInterviewLayout ? 144 : 192),
                                                            Math.max(root.theme.scaledPx(76), answer.implicitHeight))
                        }
                        Flow {
                            objectName: "interviewComposerOptions"
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            Layout.preferredHeight: childrenRect.height
                            spacing: 8
                            visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                     && (root.answerLocked || root.dynamicInterview) && !app.interview.answer_corrupted
                                     && (app.interview.ai_mode === "provider"
                                         || (app.interview.ai_mode === "codex" && (app.interview.material_refs || []).length > 0))
                            ComboBox {
                                id: providerConnection
                                objectName: "interviewActiveProvider"
                                visible: !!activeQuestion && activeQuestion.kind !== "coding" && (root.answerLocked || root.dynamicInterview) && !app.interview.answer_corrupted && app.interview.ai_mode === "provider"
                                enabled: !app.busy
                                width: Math.min(240, parent.width)
                                height: root.theme.controlHeightCompact
                                font.family: root.theme.uiFontFamily
                                font.pixelSize: root.theme.fontCaption
                                model: app.connections
                                textRole: "display_name"
                                valueRole: "connection_id"
                            }
                            CheckBox {
                                id: includeInterviewMaterials
                                objectName: "includeInterviewMaterialsToggle"
                                width: Math.min(implicitWidth, parent.width)
                                height: root.theme.controlHeightCompact
                                font.pixelSize: root.theme.fontCaption
                                font.family: root.theme.uiFontFamily
                                visible: !!activeQuestion && (root.answerLocked || root.dynamicInterview) && !app.interview.answer_corrupted
                                         && activeQuestion.kind !== "coding"
                                         && app.interview.ai_mode !== "disabled"
                                         && (app.interview.material_refs || []).length > 0
                                checked: true
                                enabled: !app.busy
                                text: "包含本场授权的简历 / JD"
                            }
                        }
                        Text {
                            objectName: "interviewAnswerActionHint"
                            visible: !root.dynamicInterview
                            text: root.answerLocked
                                  ? "回答已锁定；先记录证据，再选择评分来源。"
                                  : "提交并锁定后，再查看评分维度。"
                            color: root.colors.muted
                            font.family: root.theme ? root.theme.uiFontFamily : ""
                            font.pixelSize: root.theme ? root.theme.fontCaption : 12
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                        }
                        RowLayout {
                            visible: root.dynamicInterview
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 4
                            LabButton {
                                objectName: "inspectInterviewContext"
                                theme: root.theme
                                compact: true
                                variant: "ghost"
                                enabled: !app.busy && answer.text.trim().length > 0
                                text: "发送范围"
                                toolTip: "查看本场授权和本轮发送内容；查看不会发送请求"
                                onClicked: root.previewAI("inspect", "")
                            }
                            LabButton {
                                objectName: "toggleInterviewVoice"
                                theme: root.theme
                                compact: true
                                variant: "ghost"
                                visible: !root.answerLocked
                                text: root.voiceActionText
                                enabled: root.interviewCanEdit && !root.voiceTranscribing && (!app.busy || root.voiceRecording)
                                onClicked: root.toggleRecording()
                            }
                            Item { Layout.fillWidth: true }
                        }
                        LabButton {
                            objectName: "lockInterviewAnswer"
                            theme: root.theme
                            variant: "primary"
                            topInset: 0
                            bottomInset: 0
                            visible: !root.answerLocked || root.dynamicInterview
                            text: root.dynamicInterview
                                  ? (root.voiceTranscribing ? "正在转成文字…" : app.busy ? "正在接续面试…" : root.answerLocked ? "重试生成下一问" : "提交并继续")
                                  : "提交并锁定回答"
                            enabled: root.interviewCanEdit && answer.text.trim().length > 0 && !app.busy && !root.voiceRecording
                            Layout.alignment: Qt.AlignRight
                            onClicked: {
                                if (root.dynamicInterview) {
                                    root.submitAnswer()
                                    return
                                }
                                root.pendingLockAnswer = answer.text
                                lockAnswerDialog.open()
                            }
                        }
                    }
                }
                Flow {
                    visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted
                             && (!root.dynamicInterview || app.busy || !!app.interview.ai_error)
                    Layout.fillWidth: true
                    spacing: 8
                    Button {
                        objectName: "recordSelfAssessment"
                        visible: !root.dynamicInterview
                        text: "记录自评结果"
                        enabled: root.interviewCanEdit && root.rubricComplete() && evidence.text.trim().length > 0
                                 && !app.busy && !app.interview.assessment_recorded
                        onClicked: app.answerInterviewDetailed(answer.text, JSON.stringify(root.rubricScores), evidence.text)
                    }
                    LabButton {
                        theme: root.theme
                        variant: "primary"
                        topInset: 0
                        bottomInset: 0
                        visible: !root.dynamicInterview && app.interview.ai_mode === "provider"
                        enabled: root.interviewCanEdit && providerConnection.currentIndex >= 0
                                 && root.providerIsReady(providerConnection.currentValue)
                                 && !app.busy
                                 && !app.interview.assessment_recorded
                        text: root.dynamicInterview ? "生成下一问" : "预览 AI 评分上下文"
                        highlighted: true
                        onClicked: root.previewAI("provider", providerConnection.currentValue)
                    }
                    Button {
                        visible: app.interview.ai_mode === "provider"
                                 && (providerConnection.currentIndex < 0
                                     || !root.providerIsReady(providerConnection.currentValue))
                        text: "去 AI 连接"
                        flat: true
                        onClicked: app.navigate("connections")
                    }
                    Button {
                        visible: !root.dynamicInterview && app.interview.ai_mode === "codex"
                                  && app.aiStatusVariant !== "connected"
                        enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                        text: "连接 Codex 面试官"
                        onClicked: app.connectCodex("interviewer")
                    }
                    LabButton {
                        theme: root.theme
                        variant: "primary"
                        topInset: 0
                        bottomInset: 0
                        objectName: "continueCodexInterview"
                        visible: !root.dynamicInterview && app.interview.ai_mode === "codex" && app.aiStatusVariant === "connected"
                        enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                        text: root.dynamicInterview ? "让 Codex 继续提问" : "请求 Codex 评分"
                        onClicked: root.previewAI("codex", "")
                    }
                    LabButton {
                        objectName: "stopCodexInterviewRequest"
                        theme: root.theme
                        variant: "secondary"
                        visible: app.interview.ai_mode === "codex" && app.busy
                                 && (app.interview.ai_assessment_state === "streaming"
                                     || app.interview.ai_assessment_state === "connecting"
                                     || app.interview.ai_assessment_state === "retrying")
                        text: "停止请求"
                        onClicked: app.cancelCodex()
                    }
                    LabButton {
                        theme: root.theme
                        variant: "secondary"
                        visible: app.interview.ai_mode === "codex"
                                 && app.interview.ai_assessment_state === "error" && !app.busy
                        text: "检查 Codex 设置"
                        onClicked: app.navigate("settings")
                    }
                }
                Text {
                    visible: !!app.interview.ai_assessment_state
                             && app.interview.ai_assessment_state !== "complete"
                    Layout.fillWidth: true
                    text: app.interview.ai_assessment_state === "connecting"
                          ? "正在连接 Codex 面试官，连接后会自动发送，无需再点一次。"
                          : app.interview.ai_assessment_state === "streaming"
                          ? (root.dynamicInterview ? "AI 正在阅读你的回答并生成下一问……" : "AI 正在根据回答生成评分证据……")
                          : app.interview.ai_error || "Codex 评分尚未完成；可以检查连接后重试。"
                    color: app.interview.ai_assessment_state === "streaming"
                           ? root.colors.accent : root.colors.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 40
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: root.conversationalAnswer
                              ? (root.answerLocked ? "回答已保存，失败后可直接重试。" : "提交后，AI 会根据本轮回答继续追问。")
                              : root.interviewFinished ? "保留每轮证据，复盘更有依据。" : ""
                        color: root.colors.muted
                        font.pixelSize: 12
                    }
                    Item { Layout.fillWidth: true }
                    LabButton {
                        objectName: "finishInterviewButton"
                        theme: root.theme
                        variant: "ghost"
                        compact: true
                        visible: !root.interviewFinished
                        text: activeQuestion ? "结束本场" : "结束并查看复盘"
                        flat: true
                        enabled: !!app.interview.interview_id
                                 && (app.interview.status === "active"
                                     || app.interview.status === "paused"
                                     || app.interview.status === "timed_out")
                                 && !app.busy
                        onClicked: finishDialog.open()
                    }
                    LabButton {
                        objectName: "configureAnotherInterview"
                        theme: root.theme
                        variant: "primary"
                        visible: app.interview.status === "completed" || app.interview.status === "incomplete"
                        text: "再面试一场"
                        onClicked: { root.configuringNewInterview = true; root.clearSetupConsent(); root.initializeSetup() }
                    }
                }
            }
        }
    }

    LabDialog {
        id: lockAnswerDialog
        theme: root.theme
        objectName: "lockInterviewAnswerDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(460, root.width - 48)
        title: "锁定本题回答？"
        primaryText: "确认提交"
        message: "提交后回答将保存为只读，之后才能让 AI 继续提问。请确认这是你要留下的回答。"
        onAccepted: {
            if (!root.answerLocked && root.pendingLockAnswer.trim().length > 0)
                app.lockInterviewAnswer(root.pendingLockAnswer)
            root.pendingLockAnswer = ""
        }
        onRejected: root.pendingLockAnswer = ""
    }

    LabDialog {
        id: pauseInterviewDialog
        theme: root.theme
        objectName: "pauseInterviewDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(420, root.width - 48)
        title: "暂停本场面试？"
        primaryText: "暂停计时"
        message: "暂停后保留当前题目和剩余时间；暂停期间不能提交回答或运行代码。"
        onAccepted: app.pauseInterview()
    }

    Basic.Dialog {
        id: contextDialog
        objectName: "interviewAnswerContextDialog"
        modal: true
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.45) }
        anchors.centerIn: parent
        width: Math.min(560, Math.max(360, root.width - 48))
        height: Math.min(420, Math.max(300, root.height - 40))
        padding: 20
        title: "上下文预览（只读）"
        standardButtons: Dialog.NoButton
        header: Item {
            implicitHeight: answerContextTitle.implicitHeight + 32
            Text {
                id: answerContextTitle
                x: 20
                y: 16
                width: parent.width - 40
                text: contextDialog.title
                color: root.colors.text
                font.pixelSize: root.theme ? root.theme.fontSection : 18
                font.bold: true
                wrapMode: Text.Wrap
            }
        }
        background: Rectangle {
            color: root.colors.surface
            radius: 12
            border.color: root.colors.border
            border.width: 1
        }
        footer: Basic.DialogButtonBox {
            padding: 16
            spacing: 8
            alignment: Qt.AlignRight
            background: Rectangle { color: "transparent" }
            LabButton {
                theme: root.theme
                variant: "ghost"
                text: root.pendingAIAction === "inspect" ? "关闭" : "取消"
                onClicked: contextDialog.reject()
            }
            LabButton {
                objectName: "confirmInterviewAnswerContext"
                theme: root.theme
                variant: "primary"
                topInset: 0
                bottomInset: 0
                text: "确认发送"
                visible: root.pendingAIAction !== "inspect"
                onClicked: contextDialog.accept()
            }
        }
        onAccepted: {
            if (root.pendingAIAction === "submit") {
                if (app.authorizeInterviewConversation(answer.text, root.pendingConnection, includeInterviewMaterials.checked))
                    root.submitAnswer()
            } else if (root.pendingAIAction === "provider")
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
                text: root.pendingAIAction === "submit"
                      ? "授权本场对话：点击提交时发送当前回答、前序问答、岗位背景和下列材料。相同范围只需确认一次；材料、背景或服务改变后会重新确认。"
                      : "这里只列出发送范围。关闭预览不会发送任何内容。"
                color: root.colors.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "以下列出本次请求的内容范围；授权材料另显示短 SHA 以供核对。"
                color: root.colors.muted
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ContextPreviewList {
                id: contextPartsView
                objectName: "interviewAnswerContextList"
                theme: root.theme
                labelForPart: root.previewPartLabel
                detailForPart: root.previewPartSha
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.aiPreview.parts || []
            }
            Text {
                Layout.fillWidth: true
                text: "预计上下文：" + (root.aiPreview.estimated_tokens || 0) + " tokens"
                color: root.colors.muted
                font.pixelSize: root.theme ? root.theme.fontCaption : 12
                wrapMode: Text.Wrap
            }
        }
    }

    Basic.Dialog {
        id: planContextDialog
        objectName: "personalizedInterviewContextDialog"
        modal: true
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.45) }
        anchors.centerIn: parent
        width: Math.min(600, Math.max(380, root.width - 40))
        height: Math.min(460, Math.max(320, root.height - 36))
        padding: 20
        title: "确认设置并进入面试"
        standardButtons: Dialog.NoButton
        property bool submitting: false
        onOpened: {
            submitting = false
            root.startingDynamicInterview = false
        }
        onRejected: {
            submitting = false
            root.startingDynamicInterview = false
        }
        header: Item {
            implicitHeight: setupContextTitle.implicitHeight + 32
            Text {
                id: setupContextTitle
                x: 20
                y: 16
                width: parent.width - 40
                text: planContextDialog.title
                color: root.colors.text
                font.pixelSize: root.theme ? root.theme.fontSection : 18
                font.bold: true
                wrapMode: Text.Wrap
            }
        }
        background: Rectangle {
            color: root.colors.surface
            radius: 12
            border.color: root.colors.border
            border.width: 1
        }
        footer: Basic.DialogButtonBox {
            padding: 16
            spacing: 8
            alignment: Qt.AlignRight
            background: Rectangle {
                color: "transparent"
                border.width: 0
            }
            LabButton {
                id: cancelPlanContextButton
                theme: root.theme
                variant: "ghost"
                text: "取消"
                onClicked: planContextDialog.reject()
            }
            LabButton {
                id: confirmPlanContextButton
                objectName: "confirmInterviewSetupContext"
                theme: root.theme
                variant: "primary"
                text: "确认进入面试"
                enabled: !planContextDialog.submitting && !app.busy
                onClicked: planContextDialog.accept()
            }
        }
        onAccepted: {
            if (planContextDialog.submitting)
                return
            planContextDialog.submitting = true
            root.startingDynamicInterview = true
            app.startDynamicPersonalizedInterview(
                role.currentValue,
                seniority.currentValue,
                difficulty.currentValue,
                aiMode.currentValue === "codex" ? "codex" : planConnection.currentValue,
                root.selectedMaterials(),
                useMaterial.checked ? consent.checked : false,
                root.planContext.context_sha256 || ""
            )
            // The current first-turn use case is synchronous: it persists the
            // real opening question before returning.  Release the local gate
            // after the call so a validation error remains retryable as well.
            root.startingDynamicInterview = false
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "确认后立即进入开场题。面试流程、岗位技能、难度和你明确授权的材料会作为后续 AI 请求的上下文；不会在开始时等待模型，也不会提前生成整场计划。"
                color: root.colors.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "本场授权包含你主动提交的回答及前序问答。每次点击“提交并继续”会直接发送，不再逐轮弹窗；材料、背景或服务改变时重新确认。AI 只生成当前下一问，不预排整场题单。"
                color: root.colors.muted
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ContextPreviewList {
                id: planContextPartsView
                objectName: "interviewSetupContextList"
                theme: root.theme
                labelForPart: root.previewPartLabel
                detailForPart: root.previewPartSha
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.planContext.parts || []
            }
            Text {
                Layout.fillWidth: true
                text: "预计上下文：" + (root.planContext.estimated_tokens || 0)
                      + " tokens · SHA " + String(root.planContext.context_sha256 || "").slice(0, 12)
                color: root.colors.muted
                font.pixelSize: root.theme ? root.theme.fontCaption : 12
                wrapMode: Text.Wrap
            }
        }
    }

    Dialog {
        id: personalizedPlanDialog
        objectName: "personalizedInterviewPlanDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(720, root.width - 48)
        height: Math.min(620, root.height - 48)
        title: "确认冻结 AI 个性化面试计划"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: app.interviewPlanPreview.user_message || "请检查计划。"
                color: root.colors.text
                wrapMode: Text.Wrap
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                text: "岗位：" + (app.interviewPlanPreview.role_title || "")
                      + " · 总时长：" + (app.interviewPlanPreview.duration_minutes || 0) + " 分钟"
                      + "\n材料：" + ((app.interviewPlanPreview.material_refs || []).length)
                      + " 份逐场授权 · 上下文 SHA："
                      + String(app.interviewPlanPreview.plan_context_sha256 || "").slice(0, 12)
                color: root.colors.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 10
                    Repeater {
                        model: app.interviewPlanPreview.questions || []
                        delegate: LabCard {
                            required property var modelData
                            width: parent.width
                            cardColor: root.colors.surfaceAlt
                            borderColor: modelData.source.kind === "catalog_problem"
                                         || modelData.source.kind === "process_opening"
                                         ? root.colors.accent : root.colors.border
                            Text {
                                width: parent.width
                                text: modelData.source.kind === "catalog_problem"
                                      ? "已验证题库 Coding"
                                      : modelData.source.kind === "process_opening"
                                        ? "本地流程开场题"
                                        : "AI 生成 · " + root.roundTypeText(modelData.kind)
                                      + " · " + modelData.timebox_minutes + " 分钟"
                                color: modelData.source.kind === "catalog_problem"
                                       || modelData.source.kind === "process_opening"
                                       ? root.colors.accent : root.colors.muted
                                font.pixelSize: 11
                                font.bold: true
                            }
                            Text {
                                width: parent.width
                                text: modelData.title
                                color: root.colors.text
                                font.pixelSize: 16
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Text {
                                width: parent.width
                                text: modelData.prompt
                                color: root.colors.muted
                                wrapMode: Text.Wrap
                                maximumLineCount: 4
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "取消"
                    onClicked: {
                        app.cancelPersonalizedInterviewPlan()
                        personalizedPlanDialog.close()
                    }
                }
                Button {
                    objectName: "confirmPersonalizedInterviewPlan"
                    text: "确认并开始计时"
                    highlighted: true
                    enabled: app.interviewPlanPreview.status === "ready" && !app.busy
                    onClicked: {
                        if (app.confirmPersonalizedInterviewPlan())
                            personalizedPlanDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: startInterviewDialog
        objectName: "startInterviewConfirmationDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(500, root.width - 48)
        implicitHeight: 300
        height: implicitHeight
        title: "确认冻结本场面试？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            // Keep the boundary authoritative even if a stale dialog remains
            // open while the user changes the interviewer selector.  No-AI
            // can run Practice, but must never create a faux interview
            // session from the fixed fallback content.
            if (aiMode.currentValue === "disabled") {
                app.navigate("connections")
                return
            }
            if (useMaterial.checked)
                app.createTailoredInterview(
                    role.currentValue,
                    seniority.currentValue,
                    difficulty.currentValue,
                    material.currentValue,
                    consent.checked,
                    aiMode.currentValue
                )
            else
                app.createConfiguredInterview(
                    role.currentValue,
                    seniority.currentValue,
                    difficulty.currentValue,
                    aiMode.currentValue
                )
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "开始后会创建一份不可静默改题的本地 session，并启动本地计时。"
                color: root.colors.text
                wrapMode: Text.Wrap
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                text: "岗位：" + (role.currentText || "未选择")
                      + "\n求职阶段：" + root.seniorityText(seniority.currentValue)
                      + "\n难度：" + root.difficultyText(difficulty.currentValue)
                      + "\n面试官：" + (aiMode.currentText || "手动 / 无 AI")
                color: root.colors.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "固定题目环节：" + ((root.configuration.rounds || []).length || "按岗位蓝图")
                      + " · 题目组合和公开 Rubric 会在创建时冻结。"
                color: root.colors.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            Text {
                Layout.fillWidth: true
                visible: useMaterial.checked
                text: "材料：仅使用你勾选并同意的精确 ID / SHA；不会读取其他材料。"
                color: root.colors.warning
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            Text {
                Layout.fillWidth: true
                text: "确认后才会写入当前 Profile；取消不会创建 session。"
                color: root.colors.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
        }
    }

    Dialog {
        id: nonCodingInterviewDialog
        objectName: "nonCodingInterviewConfirmationDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(540, root.width - 48)
        height: Math.min(500, root.height - 48)
        title: "这不是完整岗位蓝图"
        onOpened: fallbackBackButton.forceActiveFocus()
        contentItem: Flickable {
            id: fallbackDialogViewport
            clip: true
            contentWidth: width
            contentHeight: fallbackDialogContent.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: fallbackDialogContent
                width: Math.max(0, fallbackDialogViewport.width - 12)
                spacing: 10
                Text {
                    Layout.fillWidth: true
                    text: "当前环境缺少完整蓝图所需的 PyTorch 代码环节。你可以明确选择只完成其余固定非代码轮次。"
                    color: root.colors.text
                    wrapMode: Text.Wrap
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "包含：" + root.fallbackRoundSummary(root.nonCodingFallback().included_rounds)
                          + "\n省略：" + root.fallbackRoundSummary(root.nonCodingFallback().omitted_rounds)
                          + "\n专项时长：" + Number(root.nonCodingFallback().duration_minutes || 0) + " 分钟"
                          + "\n蓝图证据覆盖：" + root.fallbackCoveragePercent() + "%"
                    color: root.colors.text
                    wrapMode: Text.Wrap
                    lineHeight: 1.4
                }
                Text {
                    Layout.fillWidth: true
                    text: "各轮仍保留原蓝图权重，不会重新归一化。即使所有专项问题都完成，本场也始终标记为未完整，只形成部分面试证据。"
                    color: root.colors.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "技术状态：incomplete / partial evidence"
                    color: root.colors.muted
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                Text {
                    Layout.fillWidth: true
                    text: "专项结果不会改变 Practice mastery。需要完整岗位面试时，需先克隆源码并进入仓库根目录，再运行：python -m pip install -e \".[torch,dev]\""
                    color: root.colors.muted
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: 12
                }
                Text {
                    objectName: "interviewFallbackSourceEnvironmentLink"
                    Layout.fillWidth: true
                    text: "<a href=\"https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md\">查看源码环境说明</a>"
                    textFormat: Text.RichText
                    color: root.colors.accent
                    font.pixelSize: 12
                    onLinkActivated: Qt.openUrlExternally(link)
                }
                Text {
                    Layout.fillWidth: true
                    visible: useMaterial.checked
                    text: "材料：仅使用你勾选并同意的精确 ID / SHA；不会读取其他材料。"
                    color: root.colors.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                }
            }
        }
        footer: DialogButtonBox {
            spacing: 8
            alignment: Qt.AlignRight
            Button {
                id: fallbackBackButton
                objectName: "nonCodingInterviewBackButton"
                text: "返回"
                focus: true
                onClicked: nonCodingInterviewDialog.reject()
            }
            Button {
                objectName: "nonCodingInterviewConfirmButton"
                text: "确认开始专项"
                highlighted: true
                enabled: !app.busy
                         && aiMode.currentValue !== "disabled"
                onClicked: {
                    if (aiMode.currentValue === "disabled") {
                        nonCodingInterviewDialog.close()
                        return
                    }
                    nonCodingInterviewDialog.close()
                    app.createNonCodingInterview(
                        role.currentValue,
                        seniority.currentValue,
                        difficulty.currentValue,
                        aiMode.currentValue,
                        useMaterial.checked ? material.currentValue : "",
                        useMaterial.checked ? consent.checked : false
                    )
                }
            }
        }
    }

    LabDialog {
        id: finishDialog
        theme: root.theme
        objectName: "interviewFinishDialog"
        modal: true
        anchors.centerIn: parent
        title: "结束本场面试？"
        width: Math.min(440, root.width - 48)
        primaryText: "结束并留档"
        secondaryText: "继续面试"
        onAccepted: app.finishInterview()
        message: "已完成：" + (app.interview.completed_questions || 0)
                  + " / " + (app.interview.total_questions || 0)
                  + "\n未回答：" + (app.interview.unanswered_questions || 0)
                  + "\n已回答但未评分：" + (app.interview.unscored_questions || 0)
                  + "\n代码环节未完成：" + (app.interview.coding_incomplete || 0)
                  + "\n\n" + root.finishDialogMessage()
    }
}
