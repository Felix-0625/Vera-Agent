
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

// Core Helper Functions
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

function addSvg(parent, svgString, x, y, name = "SvgIcon") {
    try {
        const shape = penpot.createShapeFromSvg(svgString);
        if (shape) {
            shape.name = name;
            parent.appendChild(shape);
            penpotUtils.setParentXY(shape, x, y);
            return shape;
        }
    } catch (e) {
        console.error("Failed to add SVG:", name, e);
    }
    return null;
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
// MAIN ARTBOARD (1600 x 960) - DARK GLASSMORPHISM
// ============================================================
const main = createBoard(page.root, {
    name: "界面 1：智能体协作主工作台 (Glassmorphism Prototype)",
    x: 0, y: 0, w: 1600, h: 960,
    fill: { fillColor: "#090D16", fillOpacity: 1 },
    stroke: { strokeColor: "#1E293B", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 1 },
    radius: 12
});

// Ambient Glowing Mesh Orbs (The signature glass background)
createEllipse(main, {
    name: "Ambient_Cyan_Orb",
    x: -120, y: -100, w: 520, h: 520,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.16 },
    blur: { value: 110 }
});

createEllipse(main, {
    name: "Ambient_Purple_Orb",
    x: 1240, y: -80, w: 520, h: 520,
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
// COLUMN 1: LEFT NAVIGATION SIDEBAR (260px)
// ============================================================
createRect(main, {
    name: "Sidebar_Glass_Panel",
    x: 0, y: 0, w: 260, h: 960,
    fill: { fillColor: "#0D1322", fillOpacity: 0.82 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 }
});

// 1. Logo
if (logoData) {
    const logoShape = penpot.createRectangle();
    logoShape.name = "Vera_Logo_Icon";
    logoShape.resize(26, 26);
    logoShape.fills = [{ fillImage: logoData, fillOpacity: 1 }];
    main.appendChild(logoShape);
    penpotUtils.setParentXY(logoShape, 18, 16);
} else {
    createText(main, { text: "V", x: 20, y: 16, size: "20", weight: "700", color: "#00E5FF" });
}
createText(main, { text: "Vera", x: 50, y: 19, size: "16", weight: "700", color: "#F8FAFC" });

// Window Navigation Controls (Sidebar layout toggles & navigation)
addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>`, 160, 21, "Sidebar_Icon");
addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>`, 192, 21, "Nav_Back_Icon");
addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>`, 222, 21, "Nav_Forward_Icon");

createRect(main, {
    name: "Btn_New_Conversation_Glass",
    x: 16, y: 58, w: 228, h: 42,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.12 },
    stroke: { strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.45 },
    radius: 10,
    shadow: { style: "drop-shadow", offsetX: 0, offsetY: 4, blur: 14, spread: 0, color: { color: "#00E5FF", opacity: 0.18 } }
});
addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 64, 71, "Plus_New_Conv");
createText(main, { text: "新建对话", x: 86, y: 70, size: "14", weight: "600", color: "#38BDF8" });

// Navigation List (Normal sleek list items)
addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`, 20, 118, "History_Icon");
createText(main, { text: "历史对话", x: 44, y: 118, size: "13", weight: "500", color: "#CBD5E1" });

addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`, 20, 148, "Tasks_Icon");
createText(main, { text: "计划任务", x: 44, y: 148, size: "13", weight: "500", color: "#CBD5E1" });

// Divider
createRect(main, { x: 16, y: 180, w: 228, h: 1, fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 } });

createText(main, { text: "项目", x: 18, y: 196, size: "12", weight: "600", color: "#64748B" });
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>`, 196, 196, "Filter_Icon");
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 222, 196, "Plus_Project");

// Project Item (Normal list row)
addSvg(main, `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`, 20, 224, "Folder_Icon");
createText(main, { text: "vera-agent", x: 40, y: 223, size: "13", weight: "600", color: "#F1F5F9" });
addSvg(main, `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`, 198, 224, "Info_Icon");
addSvg(main, `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 222, 224, "Plus_Icon");

// Indented Session under Project
createRect(main, { x: 20, y: 254, w: 220, h: 32, fill: { fillColor: "#FFFFFF", fillOpacity: 0.04 }, radius: 6 });
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`, 28, 263, "Chat_Icon");
createText(main, { text: "优化工作树执行流", x: 48, y: 262, size: "12", weight: "500", color: "#38BDF8" });
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>`, 174, 264, "Dots_Icon");
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.89A2 2 0 0 1 15 10.77V5h1V3H8v2h1v5.77a2 2 0 0 1-1.11 1.79l-1.78.89A2 2 0 0 0 5 15.24Z"/></svg>`, 198, 264, "Pin_Icon");
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 222, 264, "Plus_Icon");

// Divider
createRect(main, { x: 16, y: 298, w: 228, h: 1, fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 } });

createText(main, { text: "会话", x: 18, y: 314, size: "12", weight: "600", color: "#64748B" });
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 222, 314, "Plus_Icon");

// Conversation Item (Normal list row)
createRect(main, { x: 20, y: 338, w: 220, h: 32, fill: { fillColor: "#FFFFFF", fillOpacity: 0.03 }, radius: 6 });
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`, 28, 347, "Chat_Icon_2");
createText(main, { text: "GitFlow 架构动态重构", x: 48, y: 346, size: "12", weight: "500", color: "#E2E8F0" });
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>`, 174, 348, "Dots_Icon");
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.89A2 2 0 0 1 15 10.77V5h1V3H8v2h1v5.77a2 2 0 0 1-1.11 1.79l-1.78.89A2 2 0 0 0 5 15.24Z"/></svg>`, 198, 348, "Pin_Icon");
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 222, 348, "Plus_Icon");

addSvg(main, `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`, 20, 914, "Settings_Icon");
createText(main, { text: "设置", x: 44, y: 914, size: "13", weight: "500", color: "#94A3B8" });

// ============================================================
// COLUMN 2: CENTER MAIN INTERACTIVE WORKSPACE (960px)
// ============================================================
createRect(main, {
    name: "Center_Glass_Canvas",
    x: 260, y: 0, w: 960, h: 960,
    fill: { fillColor: "#0B0F19", fillOpacity: 0.65 }
});

// Top Layout Icons (Right of center workspace)
createRect(main, {
    x: 1146, y: 16, w: 60, h: 26,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.04 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 },
    radius: 6
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M15 3v18"/></svg>`, 1154, 22, "Layout_Split");
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`, 1180, 22, "Maximize_Icon");

// Floating Project Selector Capsule Above Input Card
createRect(main, {
    name: "Floating_Project_Capsule",
    x: 320, y: 418, w: 170, h: 30,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.15 },
    radius: 15
});
addSvg(main, `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`, 332, 426, "Folder_Capsule_Icon");
createText(main, { text: "选择项目: vera-agent", x: 352, y: 425, size: "12", weight: "500", color: "#E2E8F0" });
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`, 470, 427, "Chevron_Project");

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
createRect(main, {
    x: 344, y: 550, w: 30, h: 30,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.1 },
    radius: 15
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 352, 558, "Plus_Action");

// Model Switcher Capsule: DeepSeek-V3 ▾
createRect(main, {
    x: 386, y: 549, w: 140, h: 32,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.14 },
    radius: 8
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>`, 396, 558, "Sparkle_Model");
createText(main, { text: "DeepSeek-V3", x: 418, y: 557, size: "12", weight: "500", color: "#E2E8F0" });
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`, 506, 559, "Chevron_Model");

createRect(main, {
    x: 1056, y: 549, w: 34, h: 32,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.05 },
    stroke: { strokeColor: "#FFFFFF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.08 },
    radius: 8
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`, 1066, 558, "Mic_Icon");

createRect(main, {
    name: "Btn_Send_Glass",
    x: 1104, y: 548, w: 34, h: 34,
    fill: { fillColor: "#00E5FF", fillOpacity: 0.25 },
    stroke: { strokeColor: "#00E5FF", strokeWidth: 1, strokeAlignment: "inner", strokeOpacity: 0.6 },
    radius: 17,
    shadow: { style: "drop-shadow", offsetX: 0, offsetY: 2, blur: 10, spread: 0, color: { color: "#00E5FF", opacity: 0.3 } }
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`, 1114, 558, "Send_Arrow");

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

createRect(main, {
    x: 1220, y: 0, w: 124, h: 44,
    fill: { fillColor: "#FFFFFF", fillOpacity: 0.06 }
});
createRect(main, {
    x: 1220, y: 0, w: 124, h: 2,
    fill: { fillColor: "#00E5FF", fillOpacity: 1 }
});
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`, 1230, 15, "Globe_Tab");
createText(main, { text: "新标签页", x: 1250, y: 15, size: "12", weight: "600", color: "#F8FAFC" });
addSvg(main, `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`, 1324, 16, "Close_Tab");

addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`, 1356, 15, "Plus_Tab");
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>`, 1520, 15, "Minimize_Sidebar");
addSvg(main, `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>`, 1546, 15, "Collapse_Sidebar");

// Tools Section Header
createText(main, { text: "工具", x: 1238, y: 68, size: "14", weight: "700", color: "#F8FAFC" });

// Helper for Glass Tool Card with SVG Icon
function createGlassToolCard(x, y, title, shortcut, svgIconStr) {
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
    if (svgIconStr) {
        addSvg(main, svgIconStr, x + 12, y + 18, "Icon_" + title);
    }
    createText(main, { text: title, x: x + 34, y: y + 18, size: "13", weight: "600", color: "#F8FAFC" });
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

// 8 Tool Cards (4 Rows x 2 Columns) with Authentic SVG Icons
// Row 1
createGlassToolCard(1238, 98, "变更", "Ctrl+Shift+G", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/></svg>`);
createGlassToolCard(1414, 98, "终端", "Ctrl+`", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`);

// Row 2
createGlassToolCard(1238, 166, "文件", "Ctrl+P", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>`);
createGlassToolCard(1414, 166, "侧边聊天", "Ctrl+Alt+S", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>`);

// Row 3
createGlassToolCard(1238, 234, "子智能体", "只读", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`);
createGlassToolCard(1414, 234, "指标监控", "实时", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`);

// Row 4
createGlassToolCard(1238, 302, "MCP 市场", "工具", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`);
createGlassToolCard(1414, 302, "Skill 市场", "生态", `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#EC4899" stroke-width="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>`);

return { success: true };
