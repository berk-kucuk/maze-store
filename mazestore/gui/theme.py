"""OLED glass palette shared with the rest of the Maze suite.

Greys are Maze Guard's / Maze Cloak's so the windows sit together; the
background drops to true black because a store is mostly empty space between
cards, and on an OLED panel that space should be pixels that are off. The one
only contrast is white: the single action a page offers (Get / Update) is the
one solid white button, so the eye always lands on it. No hue anywhere —
Maze is black and white.

Surfaces are glass: translucent white over the light fields painted by
`glass.GlassBackground`. Cards and panels are painted by `glass.GlassFrame`,
status pills by `pill.Pill`; this sheet only covers what QSS can do on its own.
"""
from __future__ import annotations

P = {
    "bg":          "#000000",
    "surface":     "#0b0b0b",
    "elevated":    "#141414",
    "border":      "#1c1c1c",
    "border2":     "#2c2c2c",
    "focus":       "#4a4a4a",
    "text":        "#f2f2f4",
    "text_mid":    "#9a9a9a",
    "label":       "#8a8a8a",
    "text_dim":    "#4a4a4a",
    "accent":      "#f2f2f4",
    "accent_hi":   "#ffffff",
    "accent_text": "#000000",
    "danger":      "#d8d8dc",
    "warn":        "#bdbdc2",
}

MONO = '"JetBrains Mono", "DejaVu Sans Mono", monospace'

QSS = """
QWidget {{
    font-size: 13px;
    font-family: "Inter", "Segoe UI", sans-serif;
    color: {text};
    background: transparent;
}}
QMainWindow {{ background-color: {bg}; }}

/* chrome: frosted strips over the background */
QWidget#header {{
    background-color: rgba(0, 0, 0, 0.72);
    border-bottom: 1px solid rgba(255, 255, 255, 0.055);
}}
QWidget#sidebar {{
    background-color: rgba(0, 0, 0, 0.55);
    border-right: 1px solid rgba(255, 255, 255, 0.045);
}}
QWidget#footer {{
    background-color: rgba(0, 0, 0, 0.85);
    border-top: 1px solid rgba(255, 255, 255, 0.045);
}}
QLabel#wordmark {{ font-size: 13px; font-weight: bold; letter-spacing: 4px; }}

/* window buttons, as in Maze Guard / Maze Cloak — monochrome close hover */
QPushButton#win_btn, QPushButton#win_close {{
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
    min-width: 46px; max-width: 46px;
    min-height: 50px; max-height: 50px;
}}
QPushButton#win_btn:hover {{ background-color: rgba(255, 255, 255, 0.07); }}
QPushButton#win_close:hover {{ background-color: #f2f2f4; }}

QLineEdit#search {{
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 17px;
    min-height: 34px; max-height: 34px;
    padding: 0 14px;
    color: {text};
    selection-background-color: {accent};
    selection-color: {accent_text};
}}
QLineEdit#search:hover {{ border-color: rgba(255, 255, 255, 0.16); background-color: rgba(255, 255, 255, 0.06); }}
QLineEdit#search:focus {{ border-color: rgba(255, 255, 255, 0.40); background-color: rgba(255, 255, 255, 0.06); }}

/* sidebar */
QPushButton#nav {{
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    padding: 0;
}}
QPushButton#nav:hover {{ background-color: rgba(255, 255, 255, 0.035); }}
QPushButton#nav:checked {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 255, 255, 0.09), stop:1 rgba(255, 255, 255, 0.02));
    border: 1px solid rgba(255, 255, 255, 0.08);
}}
QLabel#nav_text {{ font-size: 13px; }}
QLabel#nav_count {{ color: {label}; font-size: 11px; font-weight: bold; }}
QLabel#navlabel {{
    color: #6e6e74; font-size: 10px; font-weight: bold; letter-spacing: 2px;
    padding: 14px 12px 6px 12px;
}}

/* buttons */
QPushButton {{
    background-color: rgba(255, 255, 255, 0.06);
    color: {text};
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 7px 16px;
}}
QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.11); border-color: rgba(255, 255, 255, 0.24); }}
QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.03); }}
QPushButton:disabled {{ color: {text_dim}; border-color: rgba(255, 255, 255, 0.05); background: transparent; }}

/* Pill buttons. Heights are fixed so the radius is exactly half of them —
   Qt draws square corners if it is any larger. */
QPushButton#get, QPushButton#get_lg {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #dcdce0);
    color: #000000;
    border: 1px solid #ffffff;
    font-weight: 800;
    letter-spacing: 0.8px;
}}
QPushButton#get {{ min-height: 30px; max-height: 30px; border-radius: 15px; padding: 0 18px; font-size: 12px; }}
QPushButton#get_lg {{ min-height: 40px; max-height: 40px; border-radius: 20px; padding: 0 30px; font-size: 13px; }}
QPushButton#get:hover, QPushButton#get_lg:hover {{ background-color: #ffffff; }}
QPushButton#get:pressed, QPushButton#get_lg:pressed {{ background-color: #cfcfd4; }}
QPushButton#get:disabled, QPushButton#get_lg:disabled {{
    background-color: rgba(255, 255, 255, 0.06); color: {text_mid}; border-color: rgba(255, 255, 255, 0.10);
}}

QPushButton#open, QPushButton#open_lg, QPushButton#secondary, QPushButton#secondary_lg {{
    background-color: rgba(255, 255, 255, 0.055);
    color: {text};
    border: 1px solid rgba(255, 255, 255, 0.12);
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QPushButton#open {{ min-height: 30px; max-height: 30px; border-radius: 15px; padding: 0 18px; font-size: 12px; }}
QPushButton#open_lg, QPushButton#secondary_lg {{ min-height: 40px; max-height: 40px; border-radius: 20px; padding: 0 26px; font-size: 13px; }}
QPushButton#secondary {{ min-height: 34px; max-height: 34px; border-radius: 17px; padding: 0 16px; font-weight: 600; letter-spacing: 0; }}
QPushButton#open:hover, QPushButton#open_lg:hover, QPushButton#secondary:hover, QPushButton#secondary_lg:hover {{
    background-color: rgba(255, 255, 255, 0.15); border-color: rgba(255, 255, 255, 0.30);
}}

QPushButton#round {{
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 0;
}}
QPushButton#round:hover {{ background-color: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.24); }}

QPushButton#ghost {{
    border: 1px solid transparent; background: transparent; color: #bdbdc2;
    padding: 0 14px; min-height: 34px; max-height: 34px; border-radius: 17px;
}}
QPushButton#ghost:hover {{ color: {text}; background-color: rgba(255, 255, 255, 0.07); border-color: rgba(255, 255, 255, 0.10); }}

QFrame#vline {{ background-color: rgba(255, 255, 255, 0.08); border: none; }}
QLabel#dot {{ border-radius: 3px; }}

QLabel#eyebrow {{ color: #8f8f95; font-size: 10px; font-weight: bold; letter-spacing: 2.2px; }}
QLabel#h2 {{ font-size: 21px; font-weight: 700; letter-spacing: -0.3px; }}
QLabel#h2_sub {{ color: #8f8f95; font-size: 12px; }}
QLabel#feature_title {{ font-size: 19px; font-weight: 700; letter-spacing: -0.2px; }}
QLabel#tagline_lg {{ color: #9a9aa0; font-size: 13px; }}

QLabel#hero_title {{ font-size: 34px; line-height: 1.1; font-weight: bold; letter-spacing: -0.5px; }}
QLabel#hero_sub {{ color: #9a9aa0; font-size: 13px; }}

QLabel#title {{ font-size: 14px; font-weight: 700; }}
QLabel#big_title {{ font-size: 32px; font-weight: 800; letter-spacing: -0.5px; }}
QLabel#tagline {{ color: #8f8f95; font-size: 12px; }}
QLabel#detail_tagline {{ color: #c4c4ca; font-size: 16px; }}
QLabel#section {{
    color: {label}; font-size: 10px; font-weight: bold; letter-spacing: 2px;
}}
QLabel#meta {{ color: {label}; font-size: 11px; }}
QLabel#stat {{ font-size: 16px; font-weight: 700; }}
QLabel#body {{ color: {text}; font-size: 13px; }}
QLabel#mono {{ font-family: {mono}; color: {text_mid}; font-size: 12px; }}
QLabel#command {{
    font-family: {mono};
    font-size: 13px;
    color: {accent};
    background-color: rgba(0, 0, 0, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 12px 14px;
}}
QLabel#empty {{ color: {text_mid}; font-size: 14px; }}
QLabel#statusbar {{ color: {label}; font-size: 11px; }}

QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget,
QStackedWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 6px; border: none; margin: 0; }}
QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.14); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.28); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QToolTip {{
    background-color: #141416; color: {text};
    border: 1px solid rgba(255, 255, 255, 0.14); padding: 6px 9px; border-radius: 8px;
}}
QMessageBox {{ background-color: #0b0b0c; }}
QMessageBox QLabel {{ color: {text}; }}
"""


def stylesheet() -> str:
    return QSS.format(mono=MONO, **P)
