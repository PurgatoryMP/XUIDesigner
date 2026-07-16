from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression
from config import CONFIG

class XMLHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        cols = CONFIG["syntax_colors"]

        header_fmt = QTextCharFormat()
        header_fmt.setForeground(QColor(cols["header"]))
        self.highlighting_rules.append((QRegularExpression(r"<\?xml.*\?>"), header_fmt))

        tag_fmt = QTextCharFormat()
        tag_fmt.setForeground(QColor(cols["tag"]))
        self.highlighting_rules.append((QRegularExpression(r"</?[a-zA-Z0-9_.-]+"), tag_fmt))
        self.highlighting_rules.append((QRegularExpression(r"/?>"), tag_fmt))

        attr_fmt = QTextCharFormat()
        attr_fmt.setForeground(QColor(cols["attribute"]))
        self.highlighting_rules.append((QRegularExpression(r"\b[a-zA-Z0-9_.-]+(?=\=)"), attr_fmt))

        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor(cols["string"]))
        self.highlighting_rules.append((QRegularExpression(r"\"[^\"]*\""), str_fmt))

        comm_fmt = QTextCharFormat()
        comm_fmt.setForeground(QColor(cols["comment"]))
        self.highlighting_rules.append((QRegularExpression(r""), comm_fmt))

        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, text_format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)