"""
This module provides the XMLHighlighter class, which extends QSyntaxHighlighter
to apply real-time, regex-based color formatting to XML markup. Color palettes
are dynamically loaded from the global application configuration.
"""

from typing import List, Tuple

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import (
    QColor,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)

from config import CONFIG


class XMLHighlighter(QSyntaxHighlighter):
    """Real-time syntax highlighter for XML documents.

    Applies color formatting to XML headers, tag names, attribute keys,
    quoted string values, and comments by evaluating regular expressions
    against blocks of text in a QTextDocument.

    Attributes:
        highlighting_rules (List[Tuple[QRegularExpression, QTextCharFormat]]):
            A list of compiled regular expressions paired with their corresponding
            text formatting styles.
    """

    def __init__(self, document: QTextDocument) -> None:
        """Initializes the XML syntax highlighter and compiles formatting rules.

        Loads color codes from the global CONFIG dictionary and builds regex
        matching rules for standard XML syntax tokens. Triggers an immediate
        rehighlight of the target document upon initialization.

        Args:
            document: The target QTextDocument to apply live syntax highlighting to.
        """
        super().__init__(document)
        self.highlighting_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []

        cols = CONFIG["syntax_colors"]

        # Rule for XML declaration headers (e.g., <?xml version="1.0"?>)
        header_fmt = QTextCharFormat()
        header_fmt.setForeground(QColor(cols["header"]))
        self.highlighting_rules.append((QRegularExpression(r"<\?xml.*\?>"), header_fmt))

        # Rules for opening/closing XML tags and self-closing delimiters
        tag_fmt = QTextCharFormat()
        tag_fmt.setForeground(QColor(cols["tag"]))
        self.highlighting_rules.append((QRegularExpression(r"</?[a-zA-Z0-9_.-]+"), tag_fmt))
        self.highlighting_rules.append((QRegularExpression(r"/?>"), tag_fmt))

        # Rule for attribute key names immediately preceding an equals sign
        attr_fmt = QTextCharFormat()
        attr_fmt.setForeground(QColor(cols["attribute"]))
        self.highlighting_rules.append((QRegularExpression(r"\b[a-zA-Z0-9_.-]+(?=\=)"), attr_fmt))

        # Rule for attribute values enclosed in double quotes
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor(cols["string"]))
        self.highlighting_rules.append((QRegularExpression(r"\"[^\"]*\""), str_fmt))

        # Rule for XML comment blocks
        comm_fmt = QTextCharFormat()
        comm_fmt.setForeground(QColor(cols["comment"]))
        self.highlighting_rules.append((QRegularExpression(r""), comm_fmt))

        # Force an initial pass over the document to apply styles immediately
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Applies syntax highlighting rules to a single line or block of text.

        Called automatically by the Qt text engine whenever a block of text
        changes or requires repainting. Iterates through all compiled regex
        rules and applies character formats to matching substring ranges.

        Args:
            text: The raw string content of the text block being evaluated.
        """
        for pattern, text_format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), text_format
                )