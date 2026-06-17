#!/usr/bin/env python3
import html
import re
import sys
from pathlib import Path


MODIFIERS = {
    "LC": "Ctl",
    "LS": "Sft",
    "LA": "Alt",
    "LG": "Gui",
    "RC": "RCtl",
    "RS": "RSft",
    "RA": "RAlt",
    "RG": "RGui",
}

KEY_LABELS = {
    "C_VOL_UP": "Vol Up",
    "C_VOL_DN": "Vol Down",
    "PG_UP": "Pg Up",
    "PG_DN": "Pg Dn",
    "SCRL_RIGHT": "Scroll Right",
    "SCRL_LEFT": "Scroll Left",
    "SCRL_DOWN": "Scroll Down",
    "SCRL_UP": "Scroll Up",
}


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*", "", text)


def split_cells(text: str) -> list[str]:
    return re.findall(r"&[A-Za-z0-9_]+|[A-Za-z0-9_]+(?:\([^<>&;\s]+\))*", text)


def format_key(token: str) -> str:
    token = token.strip()
    if token.startswith("&kp "):
        token = token[4:].strip()
    if token.startswith("&msc "):
        token = token[5:].strip()
    if token in KEY_LABELS:
        return KEY_LABELS[token]

    match = re.fullmatch(r"([LR][CSAG])\((.+)\)", token)
    if match:
        mod, key = match.groups()
        return f"{MODIFIERS.get(mod, mod)}+{format_key(key)}"

    return token.replace("_", " ").title() if "_" in token else token


def find_sensor_behaviors(keymap: str) -> dict[str, tuple[str, str]]:
    behaviors = {}
    pattern = re.compile(
        r"(?P<label>[A-Za-z0-9_]+):\s*[A-Za-z0-9_]+\s*\{(?P<body>.*?)\n\s*\};",
        re.S,
    )
    for match in pattern.finditer(keymap):
        body = match.group("body")
        if 'compatible = "zmk,behavior-sensor-rotate"' not in body:
            continue
        bindings = re.search(r"bindings\s*=\s*<(?P<cw>[^>]+)>\s*,\s*<(?P<ccw>[^>]+)>", body, re.S)
        if not bindings:
            continue
        behaviors[match.group("label")] = (
            format_key(bindings.group("cw").strip()),
            format_key(bindings.group("ccw").strip()),
        )
    return behaviors


def parse_sensor_entries(raw: str, behaviors: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    tokens = split_cells(raw)
    entries = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("&"):
            i += 1
            continue

        ref = token[1:]
        if ref in behaviors:
            entries.append(behaviors[ref])
            i += 1
        elif ref == "inc_dec_kp" and i + 2 < len(tokens):
            entries.append((format_key(tokens[i + 1]), format_key(tokens[i + 2])))
            i += 3
        else:
            i += 1
    return entries


def find_layer_encoders(keymap: str) -> dict[str, list[tuple[str, str]]]:
    keymap = strip_comments(keymap)
    behaviors = find_sensor_behaviors(keymap)
    layers = {}
    pattern = re.compile(
        r"(?P<node>[A-Za-z0-9_]+)\s*\{(?P<body>.*?display-name\s*=\s*\"(?P<name>[^\"]+)\";.*?\n\s*\};)",
        re.S,
    )
    for match in pattern.finditer(keymap):
        body = match.group("body")
        sensor_bindings = re.search(r"sensor-bindings\s*=\s*<(?P<raw>.*?)>;", body, re.S)
        if not sensor_bindings:
            continue
        entries = parse_sensor_entries(sensor_bindings.group("raw"), behaviors)
        if entries:
            layers[match.group("name")] = entries
    return layers


def short_label(label: str) -> str:
    replacements = {
        "Scroll Right": "WhlRt",
        "Scroll Left": "WhlLt",
        "Scroll Down": "WhlDn",
        "Scroll Up": "WhlUp",
        "Vol Down": "Vol-",
        "Vol Up": "Vol+",
        "Gui+Sft+Z": "Redo",
        "Gui+Z": "Undo",
        "Gui+Sft+RBKT": "Next",
        "Gui+Sft+LBKT": "Prev",
        "Sft+TAB": "S-Tab",
        "RIGHT": "Right",
        "LEFT": "Left",
        "DOWN": "Down",
        "UP": "Up",
        "Pg Up": "PgUp",
        "Pg Dn": "PgDn",
        "Ctl+Sft+Gui+4": "Shot",
        "Gui+W": "Close",
    }
    return replacements.get(label, label)


def clean_svg_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text.replace("+ ", "+")


def extract_key_label(layer_block: str, keypos: int) -> str:
    match = re.search(
        rf'<g transform="translate\([^"]+\)" class="key[^"]* keypos-{keypos}">(?P<body>.*?)\n</g>',
        layer_block,
        re.S,
    )
    if not match:
        return ""
    text = " ".join(re.findall(r"<text[^>]*>(.*?)</text>", match.group("body"), re.S))
    return clean_svg_text(text)


def remove_keypos(layer_block: str, keypos: int) -> str:
    return re.sub(
        rf'\n<g transform="translate\([^"]+\)" class="key[^"]* keypos-{keypos}">.*?\n</g>',
        "",
        layer_block,
        count=1,
        flags=re.S,
    )


def encoder_svg(entries: list[tuple[str, str]], press_labels: list[str]) -> str:
    positions = [(310, "E1"), (560, "E2"), (435, "E3"), (685, "E4")]
    knob_y = 610
    action_y = knob_y - 14
    text_y = knob_y + 1
    press_y = knob_y + 54
    arrow_offset = 32
    out = ['<g class="encoders">']
    for index, (cw, ccw) in enumerate(entries):
        if index >= len(positions):
            break
        x, _name = positions[index]
        cw = html.escape(short_label(cw))
        ccw = html.escape(short_label(ccw))
        press = html.escape(short_label(press_labels[index])) if index < len(press_labels) else ""
        out.extend(
            [
                f'<rect x="{x - 108}" y="{action_y}" rx="4" ry="4" width="58" height="30" class="encoder-action"/>',
                f'<text x="{x - 79}" y="{text_y}" class="encoder-action-text">{ccw}</text>',
                f'<circle cx="{x}" cy="{knob_y}" r="22" class="encoder-knob"/>',
                f'<circle cx="{x}" cy="{knob_y}" r="16" class="encoder-knob-inner"/>',
                f'<path d="M {x - arrow_offset} {knob_y - 11} V {knob_y + 9}" class="encoder-straight-arrow"/>',
                f'<path d="M {x - arrow_offset} {knob_y + 13} l -6 -9 h 12 z" class="encoder-arrow"/>',
                f'<path d="M {x + arrow_offset} {knob_y - 9} V {knob_y + 11}" class="encoder-straight-arrow"/>',
                f'<path d="M {x + arrow_offset} {knob_y + 15} l -6 -9 h 12 z" class="encoder-arrow"/>',
                f'<rect x="{x + 50}" y="{action_y}" rx="4" ry="4" width="58" height="30" class="encoder-action"/>',
                f'<text x="{x + 79}" y="{text_y}" class="encoder-action-text">{cw}</text>',
            ]
        )
        if press:
            out.extend(
                [
                    f'<rect x="{x - 34}" y="{press_y - 15}" rx="4" ry="4" width="68" height="30" class="encoder-press"/>',
                    f'<text x="{x}" y="{press_y}" class="encoder-press-text">{press}</text>',
                ]
            )
    out.append("</g>")
    return "\n".join(out)


def shift_layers_for_encoders(svg: str, extra_gap: int = 120) -> str:
    marker = "<!-- encoder-layer-shifted -->"
    if marker in svg:
        return svg

    layer_pattern = re.compile(r'<g transform="translate\(30, (?P<y>\d+)\)" class="layer-')
    layers = list(layer_pattern.finditer(svg))
    if not layers:
        return svg

    index = -1

    def shift_match(match: re.Match) -> str:
        nonlocal index
        index += 1
        y = int(match.group("y")) + index * extra_gap
        return f'<g transform="translate(30, {y})" class="layer-'

    svg = layer_pattern.sub(shift_match, svg)
    added_height = extra_gap * (len(layers) - 1)

    svg = re.sub(
        r'(<svg width="\d+" height=")(\d+)(" viewBox="0 0 \d+ )(\d+)(")',
        lambda m: f"{m.group(1)}{int(m.group(2)) + added_height}{m.group(3)}{int(m.group(4)) + added_height}{m.group(5)}",
        svg,
        count=1,
    )
    return svg.replace("</svg>", f"{marker}\n</svg>", 1)


def annotate_svg(svg: str, layer_encoders: dict[str, list[tuple[str, str]]]) -> str:
    svg = re.sub(r'\n<g class="encoders">.*?</g>', "", svg, flags=re.S)

    if "encoder-knob" not in svg:
        svg = svg.replace(
            "</style>",
            "\n".join(
                [
                    "rect.encoder-action { fill: #f8fafc; stroke: #cbd5e1; stroke-width: 1; }",
                    "text.encoder-action-text { font-size: 12px; font-weight: 600; text-anchor: middle; fill: #374151; }",
                    "rect.encoder-press { fill: #ecfdf5; stroke: #22c55e; stroke-width: 1; }",
                    "text.encoder-press-text { font-size: 12px; font-weight: 700; text-anchor: middle; fill: #166534; }",
                    "circle.encoder-knob { fill: #f8fafc; stroke: #22c55e; stroke-width: 2; }",
                    "circle.encoder-knob-inner { fill: none; stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 4 3; }",
                    "path.encoder-straight-arrow { fill: none; stroke: #64748b; stroke-width: 2; stroke-linecap: round; }",
                    "path.encoder-arrow { fill: #64748b; }",
                    "</style>",
                ]
            ),
            1,
        )

    for layer, entries in layer_encoders.items():
        layer_attr = svg.find(f'class="layer-{layer}"')
        if layer_attr == -1:
            continue
        layer_start = svg.rfind("<g ", 0, layer_attr)
        if layer_start == -1:
            continue
        next_layer = svg.find('\n<g transform="translate(30, ', layer_start + 1)
        layer_end = svg.find("\n</svg>", layer_start) if next_layer == -1 else next_layer
        layer_block = svg[layer_start:layer_end]
        press_labels = [extract_key_label(layer_block, 30), extract_key_label(layer_block, 31)]
        layer_block = remove_keypos(remove_keypos(layer_block, 30), 31)
        insert_at = layer_block.rfind("\n</g>")
        if insert_at == -1:
            continue
        annotated = layer_block[:insert_at] + "\n" + encoder_svg(entries, press_labels) + layer_block[insert_at:]
        svg = svg[:layer_start] + annotated + svg[layer_end:]
    svg = remove_keypos(remove_keypos(svg, 30), 31)
    svg = shift_layers_for_encoders(svg)
    return svg


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: annotate-encoders.py <keymap> <svg>", file=sys.stderr)
        return 2

    keymap_path = Path(sys.argv[1])
    svg_path = Path(sys.argv[2])
    layer_encoders = find_layer_encoders(keymap_path.read_text())
    if not layer_encoders:
        return 0
    svg_path.write_text(annotate_svg(svg_path.read_text(), layer_encoders))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
