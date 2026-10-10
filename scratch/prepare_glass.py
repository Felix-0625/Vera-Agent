# -*- coding: utf-8 -*-
with open(r"c:\Users\FAST\Desktop\Multi-agents\scratch\logo_64.txt", "r") as f:
    logo_b64 = f.read().strip()

js_code = f"""
const page = penpot.currentPage;
while (page.root.children.length > 0) {{
    page.root.children[0].remove();
}}

// 1. Upload User Logo Image
const b64 = "{logo_b64}";
const binStr = atob(b64);
const len = binStr.length;
const bytes = new Uint8Array(len);
for (let i = 0; i < len; i++) {{
    bytes[i] = binStr.charCodeAt(i);
}}
let logoData = null;
try {{
    logoData = await penpot.uploadMediaData("vera_v_logo.png", bytes, "image/png");
}} catch (e) {{
    console.error("Logo upload failed", e);
}}

// Helper Functions
function createBoard(parent, {{ name, x, y, w, h, fill, stroke, radius, shadow }}) {{
    const b = penpot.createBoard();
    b.name = name || "Board";
    b.resize(w, h);
    b.x = x;
    b.y = y;
    if (fill) b.fills = [fill];
    else b.fills = [];
    if (stroke) b.strokes = [stroke];
    if (radius) b.borderRadius = radius;
    if (shadow) b.shadows = [shadow];
    parent.appendChild(b);
    return b;
}}

function createRect(parent, {{ name, x, y, w, h, fill, stroke, radius, shadow }}) {{
    const r = penpot.createRectangle();
    r.name = name || "Rect";
    r.resize(w, h);
    if (fill) r.fills = [fill];
    else r.fills = [];
    if (stroke) r.strokes = [stroke];
    if (radius) r.borderRadius = radius;
    if (shadow) r.shadows = [shadow];
    parent.appendChild(r);
    penpotUtils.setParentXY(r, x, y);
    return r;
}}

function createEllipse(parent, {{ name, x, y, w, h, fill, blur }}) {{
    const e = penpot.createEllipse();
    e.name = name || "Glow_Orb";
    e.resize(w, h);
    if (fill) e.fills = [fill];
    if (blur) e.blur = blur;
    parent.appendChild(e);
    penpotUtils.setParentXY(e, x, y);
    return e;
}}

function createText(parent, {{ name, text, x, y, size = "13", weight = "400", color = "#F8FAFC", align = "left" }}) {{
    const t = penpot.createText(text);
    t.name = name || text.substring(0, 20);
    t.fontFamily = "Inter";
    t.fontSize = String(size);
    t.fontWeight = String(weight);
    t.fills = [{{ fillColor: color, fillOpacity: 1 }}];
    if (align) t.align = align;
    parent.appendChild(t);
    penpotUtils.setParentXY(t, x, y);
    return t;
}}

function createPill(parent, {{ name, text, x, y, w, h, bg = "#1E293B", bgOpacity = 0.6, border = "#334155", textColor = "#E2E8F0", textSize = "12", textWeight = "500", radius = 6 }}) {{
    const rect = createRect(parent, {{
        name: name || text,
        x, y, w, h,
        fill: bg ? {{ fillColor: bg, fillOpacity: bgOpacity }} : null,
        stroke: border ? {{ strokeColor: border, strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 1 }} : null,
        radius
    }});
    const txt = createText(parent, {{
        name: text + "_label",
        text,
        x: x + 8,
        y: y + Math.max(2, Math.floor((h - parseInt(textSize) * 1.3) / 2)),
        size: textSize,
        weight: textWeight,
        color: textColor
    }});
    return {{ rect, txt }};
}}

// ============================================================
// MAIN ARTBOARD (1600 x 960) - GLASSMORPHISM COSMIC OBSIDIAN
// ============================================================
const main = createBoard(page.root, {{
    name: "界面 1：智能体协作主工作台 (Glassmorphism)",
    x: 0, y: 0, w: 1600, h: 960,
    fill: {{ fillColor: "#090D16", fillOpacity: 1 }},
    stroke: {{ strokeColor: "#1E293B", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 1 }},
    radius: 12
}});

// Ambient Glowing Mesh Orbs (The soul of Glassmorphism)
createEllipse(main, {{
    name: "Ambient_Cyan_Orb",
    x: -120, y: -100, w: 500, h: 500,
    fill: {{ fillColor: "#00E5FF", fillOpacity: 0.16 }},
    blur: {{ value: 110 }}
}});

createEllipse(main, {{
    name: "Ambient_Purple_Orb",
    x: 1240, y: -80, w: 500, h: 500,
    fill: {{ fillColor: "#D500F9", fillOpacity: 0.13 }},
    blur: {{ value: 110 }}
}});

createEllipse(main, {{
    name: "Ambient_Blue_Orb",
    x: 600, y: 620, w: 560, h: 440,
    fill: {{ fillColor: "#2563EB", fillOpacity: 0.14 }},
    blur: {{ value: 120 }}
}});

// ============================================================
// COLUMN 1: LEFT NAVIGATION SIDEBAR (260px) - TRANSLUCENT GLASS
// ============================================================
createRect(main, {{
    name: "Sidebar_Glass_Panel",
    x: 0, y: 0, w: 260, h: 960,
    fill: {{ fillColor: "#0D1322", fillOpacity: 0.78 }},
    stroke: {{ strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 }}
}});

// Logo Image (User's custom uploaded V gradient logo)
if (logoData) {{
    const logoShape = penpot.createRectangle();
    logoShape.name = "Vera_Logo_Icon";
    logoShape.resize(28, 28);
    logoShape.fills = [{{ fillImage: logoData, fillOpacity: 1 }}];
    main.appendChild(logoShape);
    penpotUtils.setParentXY(logoShape, 18, 16);
}} else {{
    createText(main, {{ text: "V", x: 22, y: 16, size: "20", weight: "700", color: "#00E5FF" }});
}}

// Brand Name
createText(main, {{ text: "Vera", x: 52, y: 18, size: "17", weight: "700", color: "#F8FAFC" }});

// Window Navigation Controls [折叠] [后退] [前进]
createPill(main, {{ text: "[折叠]", x: 122, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 }});
createPill(main, {{ text: "[后退]", x: 164, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 }});
createPill(main, {{ text: "[前进]", x: 206, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 }});

// Primary Button: + 新建对话 (Glassmorphic Cyan Accent Pill)
createRect(main, {{
    name: "Btn_New_Conversation_Glass",
    x: 16, y: 58, w: 228, h: 42,
    fill: {{ fillColor: "#00E5FF", fillOpacity: 0.12 }},
    stroke: {{ strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.45 }},
    radius: 10,
    shadow: {{ style: "drop-shadow", offsetX: 0, offsetY: 4, blur: 14, spread: 0, color: {{ color: "#00E5FF", opacity: 0.18 }} }}
}});
createText(main, {{ text: "+ 新建对话", x: 74, y: 69, size: "14", weight: "600", color: "#38BDF8" }});

// Navigation List (Normal list items, NOT cards)
createText(main, {{ text: "历史对话", x: 22, y: 118, size: "13", weight: "500", color: "#CBD5E1" }});
createText(main, {{ text: "计划任务", x: 22, y: 148, size: "13", weight: "500", color: "#CBD5E1" }});

// Divider
createRect(main, {{ x: 16, y: 180, w: 228, h: 1, fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.06 }} }});

// Section 1: 项目
createText(main, {{ text: "项目", x: 18, y: 196, size: "12", weight: "600", color: "#64748B" }});
createText(main, {{ text: "[筛选]  [+]", x: 186, y: 196, size: "11", weight: "500", color: "#64748B" }});

// Project Item (Normal list row, NOT card)
createText(main, {{ text: "[<(项目名称)>]", x: 20, y: 224, size: "13", weight: "600", color: "#F1F5F9" }});
createText(main, {{ text: "[!]  [+]", x: 196, y: 224, size: "11", weight: "500", color: "#94A3B8" }});

// Indented Session under Project
createRect(main, {{ x: 20, y: 254, w: 220, h: 32, fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.04 }}, radius: 6 }});
createText(main, {{ text: "└─ [<(会话名称)>]", x: 30, y: 262, size: "12", weight: "500", color: "#38BDF8" }});
createText(main, {{ text: "[...] [📌] [+]", x: 172, y: 262, size: "10", weight: "400", color: "#64748B" }});

// Divider
createRect(main, {{ x: 16, y: 298, w: 228, h: 1, fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.06 }} }});

// Section 2: 会话
createText(main, {{ text: "会话", x: 18, y: 314, size: "12", weight: "600", color: "#64748B" }});
createText(main, {{ text: "[+]", x: 224, y: 314, size: "12", weight: "600", color: "#64748B" }});

// Conversation Item (Normal list row)
createRect(main, {{ x: 20, y: 338, w: 220, h: 32, fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.03 }}, radius: 6 }});
createText(main, {{ text: "[<(会话名称)>]", x: 28, y: 346, size: "12", weight: "500", color: "#E2E8F0" }});
createText(main, {{ text: "[...] [📌] [+]", x: 172, y: 346, size: "10", weight: "400", color: "#64748B" }});

// Bottom Bar: 设置 (No archive box entry)
createText(main, {{ text: "设置", x: 22, y: 914, size: "13", weight: "500", color: "#94A3B8" }});

// ============================================================
// COLUMN 2: CENTER MAIN INTERACTIVE WORKSPACE (960px)
// ============================================================
createRect(main, {{
    name: "Center_Glass_Canvas",
    x: 260, y: 0, w: 960, h: 960,
    fill: {{ fillColor: "#0B0F19", fillOpacity: 0.65 }}
}});

// Top Layout Icons (Right of center workspace, matching collage)
createPill(main, {{
    text: "[ ◫  ⛶ ]",
    x: 1146, y: 16, w: 60, h: 26,
    bg: "#FFFFFF", bgOpacity: 0.04, border: "#FFFFFF", textColor: "#94A3B8", textSize: "11", radius: 6
}});

// Floating Project Selector Capsule Above Input Card
createPill(main, {{
    name: "Floating_Project_Capsule",
    text: "[<(选择项目 ▾)>]",
    x: 320, y: 418, w: 140, h: 30,
    bg: "#FFFFFF", bgOpacity: 0.06,
    border: "#FFFFFF",
    textColor: "#E2E8F0",
    textSize: "12",
    textWeight: "500",
    radius: 15
}});

// Center Signature Input Card (Iconic Glassmorphism Floating Card)
createRect(main, {{
    name: "Glass_Signature_Input_Card",
    x: 320, y: 456, w: 840, h: 146,
    fill: {{ fillColor: "#0F172A", fillOpacity: 0.62 }},
    stroke: {{ strokeColor: "#FFFFFF", strokeWidth: 1.5, strokeAlignment: "inner", strokeOpacity: 0.16 }},
    radius: 18,
    shadow: {{
        style: "drop-shadow",
        offsetX: 0,
        offsetY: 12,
        blur: 36,
        spread: 0,
        color: {{ color: "#000000", opacity: 0.45 }}
    }}
}});

// Input Placeholder Text
createText(main, {{
    text: "Ask anything, / for actions",
    x: 346, y: 480, size: "15", weight: "400", color: "#64748B"
}});

// Card Bottom Controls
// [+] 唤醒能力
createPill(main, {{
    text: "+",
    x: 344, y: 550, w: 30, h: 30,
    bg: "#FFFFFF", bgOpacity: 0.06, border: "#FFFFFF", textColor: "#94A3B8", textSize: "15", textWeight: "600", radius: 15
}});

// [<(模型切换 ▾)>]
createPill(main, {{
    text: "[<(模型切换 ▾)>]",
    x: 386, y: 549, w: 140, h: 32,
    bg: "#FFFFFF", bgOpacity: 0.06, border: "#FFFFFF", textColor: "#E2E8F0", textSize: "12", textWeight: "500", radius: 8
}});

// [语音] (Mic)
createPill(main, {{
    text: "[语音]",
    x: 1056, y: 549, w: 46, h: 32,
    bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "11", radius: 8
}});

// [发送] (Cyan Glowing Send Button)
createRect(main, {{
    name: "Btn_Send_Glass",
    x: 1110, y: 548, w: 34, h: 34,
    fill: {{ fillColor: "#00E5FF", fillOpacity: 0.25 }},
    stroke: {{ strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.6 }},
    radius: 17,
    shadow: {{ style: "drop-shadow", offsetX: 0, offsetY: 2, blur: 10, spread: 0, color: {{ color: "#00E5FF", opacity: 0.3 }} }}
}});
createText(main, {{ text: "→", x: 1121, y: 555, size: "15", weight: "700", color: "#00E5FF" }});

// ============================================================
// COLUMN 3: RIGHT SIDEBAR - CODEX TOOLS (380px)
// ============================================================
createRect(main, {{
    name: "Codex_Sidebar_Glass",
    x: 1220, y: 0, w: 380, h: 960,
    fill: {{ fillColor: "#0D1322", fillOpacity: 0.82 }},
    stroke: {{ strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 }}
}});

// Top Tab Bar
createRect(main, {{
    x: 1220, y: 0, w: 380, h: 44,
    fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.02 }},
    stroke: {{ strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.05 }}
}});

// Active Tab: [新标签页 x]
createRect(main, {{
    x: 1220, y: 0, w: 120, h: 44,
    fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.06 }}
}});
createRect(main, {{
    x: 1220, y: 0, w: 120, h: 2,
    fill: {{ fillColor: "#00E5FF", fillOpacity: 1 }}
}});
createText(main, {{ text: "[新标签页 x]", x: 1238, y: 15, size: "12", weight: "600", color: "#F8FAFC" }});
createText(main, {{ text: "[+]", x: 1350, y: 14, size: "14", weight: "600", color: "#64748B" }});
createText(main, {{ text: "[⛶]  [折叠]", x: 1516, y: 15, size: "11", weight: "400", color: "#64748B" }});

// Tools Section Header
createText(main, {{ text: "工具", x: 1238, y: 68, size: "14", weight: "700", color: "#F8FAFC" }});

// Helper for Glass Tool Card
function createGlassToolCard(x, y, title, shortcut) {{
    createRect(main, {{
        name: "Tool_Card_" + title,
        x, y, w: 166, h: 56,
        fill: {{ fillColor: "#FFFFFF", fillOpacity: 0.04 }},
        stroke: {{ strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.1 }},
        radius: 10,
        shadow: {{
            style: "drop-shadow",
            offsetX: 0,
            offsetY: 4,
            blur: 14,
            spread: 0,
            color: {{ color: "#000000", opacity: 0.25 }}
        }}
    }});
    createText(main, {{ text: "[" + title + "]", x: x + 14, y: y + 18, size: "13", weight: "600", color: "#F8FAFC" }});
    if (shortcut) {{
        createPill(main, {{
            text: shortcut,
            x: x + 88, y: y + 16, w: 68, h: 22,
            bg: "#FFFFFF", bgOpacity: 0.05,
            border: "#FFFFFF",
            textColor: "#94A3B8",
            textSize: "10",
            radius: 4
        }});
    }}
}}

// 8 Tool Cards (4 Rows x 2 Columns)
// Row 1
createGlassToolCard(1238, 98, "变更", "Ctrl+Shift+G");
createGlassToolCard(1414, 98, "终端", "Ctrl+`");

// Row 2
createGlassToolCard(1238, 166, "文件", "Ctrl+P");
createGlassToolCard(1414, 166, "侧边聊天", "Ctrl+Alt+S");

// Row 3
createGlassToolCard(1238, 234, "子智能体", "只读");
createGlassToolCard(1414, 234, "指标监控", "实时");

// Row 4 (MCP 市场 & Skill 市场)
createGlassToolCard(1238, 302, "MCP 市场", "工具");
createGlassToolCard(1414, 302, "Skill 市场", "生态");

return {{ success: true }};
"""

with open(r"c:\Users\FAST\Desktop\Multi-agents\scratch\run_glass.py", "w", encoding="utf-8") as f:
    f.write(f'# -*- coding: utf-8 -*-\ncode = """{js_code}"""\nprint("Length of code:", len(code))\n')

print("Created run_glass.py successfully")
