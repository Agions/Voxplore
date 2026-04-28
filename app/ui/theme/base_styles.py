"""
Voxplore 基础样式系统
所有样式基于 tokens.py，不硬编码颜色值
"""

def get_base_qss() -> str:
    """返回全局基础 QSS"""
    return """
    /* === 全局 === */
    QWidget {
        background-color: var(--color-bg-base);
        color: var(--color-text-primary);
        font-family: var(--font-family);
        font-size: var(--font-size-md);
    }

    /* === 按钮 === */
    QPushButton {
        background-color: var(--color-bg-elevated);
        color: var(--color-text-primary);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 8px 16px;
        font-size: var(--font-size-md);
        transition: all var(--transition-fast);
    }
    QPushButton:hover {
        background-color: var(--color-bg-overlay);
        border-color: var(--color-border-strong);
    }
    QPushButton:pressed {
        background-color: var(--color-bg-surface);
    }
    QPushButton:disabled {
        color: var(--color-text-disabled);
        border-color: var(--color-border-subtle);
    }

    /* 主按钮 */
    QPushButton.primary {
        background-color: var(--color-primary);
        color: white;
        border: none;
    }
    QPushButton.primary:hover {
        background-color: var(--color-primary-hover);
    }
    QPushButton.primary:pressed {
        background-color: var(--color-primary-pressed);
    }

    /* 次要按钮 */
    QPushButton.secondary {
        background-color: transparent;
        color: var(--color-text-secondary);
        border: 1px solid var(--color-border);
    }
    QPushButton.secondary:hover {
        color: var(--color-text-primary);
        border-color: var(--color-border-strong);
    }

    /* === 卡片 === */
    QFrame.card {
        background-color: var(--color-bg-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
    }

    /* === 输入框 === */
    QLineEdit {
        background-color: var(--color-bg-surface);
        color: var(--color-text-primary);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 8px 12px;
        font-size: var(--font-size-md);
    }
    QLineEdit:focus {
        border-color: var(--color-primary);
    }
    QLineEdit::placeholder {
        color: var(--color-text-muted);
    }

    /* === 标签 === */
    QLabel {
        background: transparent;
        color: var(--color-text-primary);
    }
    QLabel.subtitle {
        color: var(--color-text-secondary);
        font-size: var(--font-size-sm);
    }

    /* === 进度条 === */
    QProgressBar {
        background-color: var(--color-bg-surface);
        border: none;
        border-radius: var(--radius-full);
        height: 4px;
    }
    QProgressBar::chunk {
        background-color: var(--color-primary);
        border-radius: var(--radius-full);
    }

    /* === 滚动条 === */
    QScrollBar:vertical {
        background: transparent;
        width: 6px;
    }
    QScrollBar::handle:vertical {
        background: var(--color-border-strong);
        border-radius: 3px;
        min-height: 40px;
    }
    QScrollBar::handle:vertical:hover {
        background: var(--color-text-muted);
    }
    """
