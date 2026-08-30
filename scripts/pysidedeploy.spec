[app]
title = LLMInterviewLab
project_dir = ..
input_file = src/llm_interview_lab/desktop/main.py
exec_directory = dist/desktop
project_file = 
icon = dist/icons/LLMInterviewLab.ico

[python]
python_path = 
packages = Nuitka==4.2,zstandard==0.25.0,ordered-set==4.1.0
android_packages = 

[qt]
qml_files = src/llm_interview_lab/desktop/qml/Main.qml,src/llm_interview_lab/desktop/qml/components/LabCard.qml,src/llm_interview_lab/desktop/qml/components/StatusPill.qml,src/llm_interview_lab/desktop/qml/components/AppTheme.qml,src/llm_interview_lab/desktop/qml/components/EmptyState.qml,src/llm_interview_lab/desktop/qml/components/InlineNotice.qml,src/llm_interview_lab/desktop/qml/components/LabBusyIndicator.qml,src/llm_interview_lab/desktop/qml/components/LabButton.qml,src/llm_interview_lab/desktop/qml/components/LabComboBox.qml,src/llm_interview_lab/desktop/qml/components/LabDialog.qml,src/llm_interview_lab/desktop/qml/components/LabDivider.qml,src/llm_interview_lab/desktop/qml/components/LabIconButton.qml,src/llm_interview_lab/desktop/qml/components/LabScrollBar.qml,src/llm_interview_lab/desktop/qml/components/LabSurface.qml,src/llm_interview_lab/desktop/qml/components/LabText.qml,src/llm_interview_lab/desktop/qml/components/LabTextField.qml,src/llm_interview_lab/desktop/qml/components/NavItem.qml,src/llm_interview_lab/desktop/qml/components/SectionHeader.qml,src/llm_interview_lab/desktop/qml/pages/OnboardingPage.qml,src/llm_interview_lab/desktop/qml/pages/HomePage.qml,src/llm_interview_lab/desktop/qml/pages/CareerPage.qml,src/llm_interview_lab/desktop/qml/pages/LearnPage.qml,src/llm_interview_lab/desktop/qml/pages/ExercisePage.qml,src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml,src/llm_interview_lab/desktop/qml/pages/CoachPage.qml,src/llm_interview_lab/desktop/qml/pages/ProgressPage.qml,src/llm_interview_lab/desktop/qml/pages/ConnectionsPage.qml,src/llm_interview_lab/desktop/qml/pages/SettingsPage.qml
excluded_qml_plugins = QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Qml,Quick,QuickControls2,Svg
plugins = 

[android]
wheel_pyside = 
wheel_shiboken = 
plugins = 

[nuitka]
macos.permissions = 
mode = standalone
extra_args = --quiet --assume-yes-for-downloads --noinclude-qt-translations --windows-console-mode=attach --include-package=llm_interview_lab --include-package=pytest --include-package=keyring --include-package=httpx --nofollow-import-to=any_llm --nofollow-import-to=anthropic --nofollow-import-to=google.genai --nofollow-import-to=ollama --nofollow-import-to=openai --include-data-dir=src/llm_interview_lab/desktop/resources=llm_interview_lab/desktop/resources --include-data-dir=curriculum=runtime_assets/curriculum --include-data-files=curriculum/problems=runtime_assets/curriculum/problems/=**/*.py --include-data-files=curriculum/retention=runtime_assets/curriculum/retention/=**/*.py --include-data-dir=workspace/schema=runtime_assets/workspace/schema --include-data-dir=workspace/templates=runtime_assets/workspace/templates --include-data-dir=coach=runtime_assets/coach --include-data-files=AGENTS.md=runtime_assets/AGENTS.md --include-data-files=.gitignore=runtime_assets/.gitignore --report=desktop-nuitka-report.xml

[buildozer]
mode = debug
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 

