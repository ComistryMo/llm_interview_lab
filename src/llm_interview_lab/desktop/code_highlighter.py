"""Small native Python highlighting for both practice and interview editors."""
import keyword
import re

from PySide6.QtCore import QObject, Property, Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "InterviewLab.Editor"
QML_IMPORT_MAJOR_VERSION = 1

_TOKENS = re.compile(r"#[^\n]*|(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b")


class _PythonSyntax(QSyntaxHighlighter):
    dark = False

    def highlightBlock(self, text):
        colors = ("#91b5dc", "#b2c6a2", "#9d9d9d", "#d6b785") if self.dark else ("#315e8b", "#476538", "#777777", "#865b21")
        for token in _TOKENS.finditer(text):
            word = token.group()
            kind = (0 if keyword.iskeyword(word) else 1 if word[:1] in {"'", '"'}
                    else 2 if word.startswith("#") else 3 if word[0].isdigit() else None)
            if kind is not None:
                style = QTextCharFormat()
                style.setForeground(QColor(colors[kind]))
                self.setFormat(token.start(), len(word), style)


@QmlElement
class PythonCodeHighlighter(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document = None
        self._syntax = None
        self._dark = False

    @Property(QObject, notify=changed)
    def document(self):
        return self._document

    @document.setter
    def document(self, value):
        if value is self._document:
            return
        if self._syntax:
            self._syntax.setDocument(None)
            self._syntax.deleteLater()
        self._document = value
        self._syntax = _PythonSyntax(value.textDocument()) if value else None
        if self._syntax:
            self._syntax.dark = self._dark
            self._syntax.rehighlight()
        self.changed.emit()

    @Property(bool, notify=changed)
    def dark(self):
        return self._dark

    @dark.setter
    def dark(self, value):
        if value == self._dark:
            return
        self._dark = value
        if self._syntax:
            self._syntax.dark = value
            self._syntax.rehighlight()
        self.changed.emit()
