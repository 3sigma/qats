#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module implementing a logger class

@author: perl
"""
import logging
from PyQt5.QtWidgets import QTextBrowser


class QLogger(logging.Handler):
    """
    Logger handler
    """
    def __init__(self, parent):
        super().__init__()
        self.widget = QTextBrowser(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        """
        Append logger record to text browser

        Parameters
        ----------
        record : str
            logger record

        """
        record = self.format(record)
        self.widget.append(record)

