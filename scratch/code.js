
const page = penpot.currentPage;
while (page.root.children.length > 0) {
    page.root.children[0].remove();
}

// 1. Upload User Logo Image
const b64 = "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";
const binStr = atob(b64);
const len = binStr.length;
const bytes = new Uint8Array(len);
for (let i = 0; i < len; i++) {
    bytes[i] = binStr.charCodeAt(i);
}
let logoData = null;
try {
    logoData = await penpot.uploadMediaData("vera_v_logo.png", bytes, "image/png");
} catch (e) {
    console.error("Logo upload failed", e);
}

// Helper Functions
function createBoard(parent, { name, x, y, w, h, fill, stroke, radius, shadow }) {
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
}

function createRect(parent, { name, x, y, w, h, fill, stroke, radius, shadow }) {
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
}

function createEllipse(parent, { name, x, y, w, h, fill, blur }) {
    const e = penpot.createEllipse();
    e.name = name || "Glow_Orb";
    e.resize(w, h);
    if (fill) e.fills = [fill];
    if (blur) e.blur = blur;
    parent.appendChild(e);
    penpotUtils.setParentXY(e, x, y);
    return e;
}

function createText(parent, { name, text, x, y, size = "13", weight = "400", color = "#F8FAFC", align = "left" }) {
    const t = penpot.createText(text);
    t.name = name || text.substring(0, 20);
    t.fontFamily = "Inter";
    t.fontSize = String(size);
    t.fontWeight = String(weight);
    t.fills = [{ fillColor: color, fillOpacity: 1 }];
    if (align) t.align = align;
    parent.appendChild(t);
    penpotUtils.setParentXY(t, x, y);
    return t;
}

function createPill(parent, { name, text, x, y, w, h, bg = "#1E293B", bgOpacity = 0.6, border = "#334155", textColor = "#E2E8F0", textSize = "12", textWeight = "500", radius = 6 }) {
    const rect = createRect(parent, {
        name: name || text,
        x, y, w, h,
        fill: bg ? { fillColor: bg, fillOpacity: bgOpacity } : null,
        stroke: border ? { strokeColor: border, strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 1 } : null,
        radius
    });
    const txt = createText(parent, {
        name: text + "_label",
        text,
        x: x + 8,
        y: y + Math.max(2, Math.floor((h - parseInt(textSize) * 1.3) / 2)),
        size: textSize,
        weight: textWeight,
        color: textColor
    });
    return { rect, txt };
}

// ============================================================
// MAIN ARTBOARD (1600 x 960) - GLASSMORPHISM COSMIC OBSIDIAN
// ============================================================
const main = createBoard(page.root, {
    name: "界面 1：智能体协作主工作台 (Glassmorphism)",
    x: 0, y: 0, w: 1600, h: 960,
    fill: { fillColor: "#090D16", fillOpacity: 1 },
    stroke: { strokeColor: "#1E293B", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 1 },
    radius: 12
});

// Ambient Glowing Mesh Orbs (The soul of Glassmorphism)
createEllipse(main, {
    name: "Ambient_Cyan_Orb",
    x: -120, y: -100, w: 500, h: 500,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.16 },
    blur: { value: 110 }
});

createEllipse(main, {
    name: "Ambient_Purple_Orb",
    x: 1240, y: -80, w: 500, h: 500,
    fill: { fillColor: "#D500F9", fillOpacity: 0.13 },
    blur: { value: 110 }
});

createEllipse(main, {
    name: "Ambient_Blue_Orb",
    x: 600, y: 620, w: 560, h: 440,
    fill: { fillColor: "#2563EB", fillOpacity: 0.14 },
    blur: { value: 120 }
});

// ============================================================
// COLUMN 1: LEFT NAVIGATION SIDEBAR (260px) - TRANSLUCENT GLASS
// ============================================================
createRect(main, {
    name: "Sidebar_Glass_Panel",
    x: 0, y: 0, w: 260, h: 960,
    fill: { fillColor: "#0D1322", fillOpacity: 0.78 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 }
});

// Logo Image (User's custom uploaded V gradient logo)
if (logoData) {
    const logoShape = penpot.createRectangle();
    logoShape.name = "Vera_Logo_Icon";
    logoShape.resize(28, 28);
    logoShape.fills = [{ fillImage: logoData, fillOpacity: 1 }];
    main.appendChild(logoShape);
    penpotUtils.setParentXY(logoShape, 18, 16);
} else {
    createText(main, { text: "V", x: 22, y: 16, size: "20", weight: "700", color: "#00E5FF" });
}

// Brand Name
createText(main, { text: "Vera", x: 52, y: 18, size: "17", weight: "700", color: "#F8FAFC" });

// Window Navigation Controls [折叠] [后退] [前进]
createPill(main, { text: "[折叠]", x: 122, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 });
createPill(main, { text: "[后退]", x: 164, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 });
createPill(main, { text: "[前进]", x: 206, y: 18, w: 38, h: 22, bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "10", radius: 4 });

// Primary Button: + 新建对话 (Glassmorphic Cyan Accent Pill)
createRect(main, {
    name: "Btn_New_Conversation_Glass",
    x: 16, y: 58, w: 228, h: 42,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.12 },
    stroke: { strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.45 },
    radius: 10,
    shadow: { style: "drop-shadow", offsetX: 0, offsetY: 4, blur: 14, spread: 0, color: { color: "#00E5FF", opacity: 0.18 } }
});
createText(main, { text: "+ 新建对话", x: 74, y: 69, size: "14", weight: "600", color: "#38BDF8" });

// Navigation List (Normal list items, NOT cards)
createText(main, { text: "历史对话", x: 22, y: 118, size: "13", weight: "500", color: "#CBD5E1" });
createText(main, { text: "计划任务", x: 22, y: 148, size: "13", weight: "500", color: "#CBD5E1" });

// Divider
createRect(main, { x: 16, y: 180, w: 228, h: 1, fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 } });

// Section 1: 项目
createText(main, { text: "项目", x: 18, y: 196, size: "12", weight: "600", color: "#64748B" });
createText(main, { text: "[筛选]  [+]", x: 186, y: 196, size: "11", weight: "500", color: "#64748B" });

// Project Item (Normal list row, NOT card)
createText(main, { text: "[<(项目名称)>]", x: 20, y: 224, size: "13", weight: "600", color: "#F1F5F9" });
createText(main, { text: "[!]  [+]", x: 196, y: 224, size: "11", weight: "500", color: "#94A3B8" });

// Indented Session under Project
createRect(main, { x: 20, y: 254, w: 220, h: 32, fill: { fillColor: "#FFFFFF", fillOpacity: 0.04 }, radius: 6 });
createText(main, { text: "└─ [<(会话名称)>]", x: 30, y: 262, size: "12", weight: "500", color: "#38BDF8" });
createText(main, { text: "[...] [📌] [+]", x: 172, y: 262, size: "10", weight: "400", color: "#64748B" });

// Divider
createRect(main, { x: 16, y: 298, w: 228, h: 1, fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 } });

// Section 2: 会话
createText(main, { text: "会话", x: 18, y: 314, size: "12", weight: "600", color: "#64748B" });
createText(main, { text: "[+]", x: 224, y: 314, size: "12", weight: "600", color: "#64748B" });

// Conversation Item (Normal list row)
createRect(main, { x: 20, y: 338, w: 220, h: 32, fill: { fillColor: "#FFFFFF", fillOpacity: 0.03 }, radius: 6 });
createText(main, { text: "[<(会话名称)>]", x: 28, y: 346, size: "12", weight: "500", color: "#E2E8F0" });
createText(main, { text: "[...] [📌] [+]", x: 172, y: 346, size: "10", weight: "400", color: "#64748B" });

// Bottom Bar: 设置 (No archive box entry)
createText(main, { text: "设置", x: 22, y: 914, size: "13", weight: "500", color: "#94A3B8" });

// ============================================================
// COLUMN 2: CENTER MAIN INTERACTIVE WORKSPACE (960px)
// ============================================================
createRect(main, {
    name: "Center_Glass_Canvas",
    x: 260, y: 0, w: 960, h: 960,
    fill: { fillColor: "#0B0F19", fillOpacity: 0.65 }
});

// Top Layout Icons (Right of center workspace, matching collage)
createPill(main, {
    text: "[ ◫  ⛶ ]",
    x: 1146, y: 16, w: 60, h: 26,
    bg: "#FFFFFF", bgOpacity: 0.04, border: "#FFFFFF", textColor: "#94A3B8", textSize: "11", radius: 6
});

// Floating Project Selector Capsule Above Input Card
createPill(main, {
    name: "Floating_Project_Capsule",
    text: "[<(选择项目 ▾)>]",
    x: 320, y: 418, w: 140, h: 30,
    bg: "#FFFFFF", bgOpacity: 0.06,
    border: "#FFFFFF",
    textColor: "#E2E8F0",
    textSize: "12",
    textWeight: "500",
    radius: 15
});

// Center Signature Input Card (Iconic Glassmorphism Floating Card)
createRect(main, {
    name: "Glass_Signature_Input_Card",
    x: 320, y: 456, w: 840, h: 146,
    fill: { fillColor: "#0F172A", fillOpacity: 0.62 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1.5, strokeAlignment: "inner", strokeOpacity: 0.16 },
    radius: 18,
    shadow: {
        style: "drop-shadow",
        offsetX: 0,
        offsetY: 12,
        blur: 36,
        spread: 0,
        color: { color: "#000000", opacity: 0.45 }
    }
});

// Input Placeholder Text
createText(main, {
    text: "Ask anything, / for actions",
    x: 346, y: 480, size: "15", weight: "400", color: "#64748B"
});

// Card Bottom Controls
// [+] 唤醒能力
createPill(main, {
    text: "+",
    x: 344, y: 550, w: 30, h: 30,
    bg: "#FFFFFF", bgOpacity: 0.06, border: "#FFFFFF", textColor: "#94A3B8", textSize: "15", textWeight: "600", radius: 15
});

// [<(模型切换 ▾)>]
createPill(main, {
    text: "[<(模型切换 ▾)>]",
    x: 386, y: 549, w: 140, h: 32,
    bg: "#FFFFFF", bgOpacity: 0.06, border: "#FFFFFF", textColor: "#E2E8F0", textSize: "12", textWeight: "500", radius: 8
});

// [语音] (Mic)
createPill(main, {
    text: "[语音]",
    x: 1056, y: 549, w: 46, h: 32,
    bg: "#FFFFFF", bgOpacity: 0.05, border: "#FFFFFF", textColor: "#94A3B8", textSize: "11", radius: 8
});

// [发送] (Cyan Glowing Send Button)
createRect(main, {
    name: "Btn_Send_Glass",
    x: 1110, y: 548, w: 34, h: 34,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.25 },
    stroke: { strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.6 },
    radius: 17,
    shadow: { style: "drop-shadow", offsetX: 0, offsetY: 2, blur: 10, spread: 0, color: { color: "#00E5FF", opacity: 0.3 } }
});
createText(main, { text: "→", x: 1121, y: 555, size: "15", weight: "700", color: "#00E5FF" });

// ============================================================
// COLUMN 3: RIGHT SIDEBAR - CODEX TOOLS (380px)
// ============================================================
createRect(main, {
    name: "Codex_Sidebar_Glass",
    x: 1220, y: 0, w: 380, h: 960,
    fill: { fillColor: "#0D1322", fillOpacity: 0.82 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 }
});

// Top Tab Bar
createRect(main, {
    x: 1220, y: 0, w: 380, h: 44,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.02 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.05 }
});

// Active Tab: [新标签页 x]
createRect(main, {
    x: 1220, y: 0, w: 120, h: 44,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 }
});
createRect(main, {
    x: 1220, y: 0, w: 120, h: 2,
    fill: { fillColor: "#00E5FF", fillOpacity: 1 }
});
createText(main, { text: "[新标签页 x]", x: 1238, y: 15, size: "12", weight: "600", color: "#F8FAFC" });
createText(main, { text: "[+]", x: 1350, y: 14, size: "14", weight: "600", color: "#64748B" });
createText(main, { text: "[⛶]  [折叠]", x: 1516, y: 15, size: "11", weight: "400", color: "#64748B" });

// Tools Section Header
createText(main, { text: "工具", x: 1238, y: 68, size: "14", weight: "700", color: "#F8FAFC" });

// Helper for Glass Tool Card
function createGlassToolCard(x, y, title, shortcut) {
    createRect(main, {
        name: "Tool_Card_" + title,
        x, y, w: 166, h: 56,
        fill: { fillColor: "#FFFFFF", fillOpacity: 0.04 },
        stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.1 },
        radius: 10,
        shadow: {
            style: "drop-shadow",
            offsetX: 0,
            offsetY: 4,
            blur: 14,
            spread: 0,
            color: { color: "#000000", opacity: 0.25 }
        }
    });
    createText(main, { text: "[" + title + "]", x: x + 14, y: y + 18, size: "13", weight: "600", color: "#F8FAFC" });
    if (shortcut) {
        createPill(main, {
            text: shortcut,
            x: x + 88, y: y + 16, w: 68, h: 22,
            bg: "#FFFFFF", bgOpacity: 0.05,
            border: "#FFFFFF",
            textColor: "#94A3B8",
            textSize: "10",
            radius: 4
        });
    }
}

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

return { success: true };
