
// ==============================================================================
// Design Reference: KokonutUI Dashboard & StyleKit Nocturne Glass
// ==============================================================================

// 1. Clean existing boards
const existingBoards = penpot.currentPage.findShapes().filter(s => s.type === 'board' && s.name.includes('界面 1'));
for (const b of existingBoards) {
  try { b.remove(); } catch (e) {}
}

// 2. Upload User Logo
let logoMedia = null;
try {
  const b64 = "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";
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  logoMedia = await penpot.uploadMediaData("vera_logo_v.png", bytes, "image/png");
} catch (e) {
  console.log("Logo upload warning:", e);
}

// 3. Create Root Board (1600 x 960)
const board = penpot.createBoard();
board.name = "界面 1：智能体协作主工作台 (KokonutUI 极简玻璃拟态)";
board.x = 0;
board.y = 0;
board.resize(1600, 960);
board.fills = [{ fillColor: "#0D0E12" }];

// Helper: safe add child
function addChild(child, x, y) {
  if (!child) return;
  board.appendChild(child);
  penpotUtils.setParentXY(child, x, y);
}

// Helper: safe SVG creation
function createSvg(svgStr, x, y) {
  try {
    const shape = penpot.createShapeFromSvg(svgStr);
    if (shape) {
      addChild(shape, x, y);
      return shape;
    }
  } catch (e) {
    console.log("SVG create error:", e);
  }
  return null;
}

// 4. Background Ambient Glow (Subtle & Restrained Nocturne Atmosphere)
const ambientGlow = penpot.createRectangle();
ambientGlow.name = "Ambient_Nocturne_Glow";
ambientGlow.resize(700, 500);
ambientGlow.fills = [{ fillColor: "#1E1B4B", fillOpacity: 0.12 }];
ambientGlow.borderRadius = 250;
ambientGlow.blur = { type: "layer", value: 120 };
addChild(ambientGlow, 550, 200);

// ==============================================================================
// 5. Left Sidebar (260px wide, KokonutUI Minimal Nav)
// ==============================================================================
const sidebarBg = penpot.createRectangle();
sidebarBg.name = "Left_Sidebar_Surface";
sidebarBg.resize(260, 960);
sidebarBg.fills = [{ fillColor: "#111217" }];
sidebarBg.strokes = [{ strokeColor: "#1E2028", strokeWidth: 1 }];
addChild(sidebarBg, 0, 0);

// Top Brand Header
if (logoMedia) {
  const logo = penpot.createMedia(logoMedia);
  logo.name = "Brand_Logo";
  logo.resize(28, 28);
  addChild(logo, 20, 20);
}

const brandTitle = penpot.createText("Vera Agent");
brandTitle.name = "Brand_Title";
brandTitle.fontSize = 15;
brandTitle.fontWeight = "700";
brandTitle.fills = [{ fillColor: "#F4F4F6" }];
addChild(brandTitle, 56, 25);

const versionPill = penpot.createRectangle();
versionPill.name = "Version_Pill";
versionPill.resize(38, 18);
versionPill.borderRadius = 9;
versionPill.fills = [{ fillColor: "#1C1D24" }];
addChild(versionPill, 142, 25);

const versionText = penpot.createText("v0.18");
versionText.fontSize = 10;
versionText.fontWeight = "500";
versionText.fills = [{ fillColor: "#8E929E" }];
addChild(versionText, 148, 27);

const newChatBtn = penpot.createRectangle();
newChatBtn.name = "New_Chat_Btn";
newChatBtn.resize(220, 38);
newChatBtn.borderRadius = 8;
newChatBtn.fills = [{ fillColor: "#1A1C24" }];
newChatBtn.strokes = [{ strokeColor: "#2A2C38", strokeWidth: 1 }];
addChild(newChatBtn, 20, 68);

const plusSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvg(plusSvg, 32, 80);

const newChatText = penpot.createText("新建对话");
newChatText.fontSize = 13;
newChatText.fontWeight = "600";
newChatText.fills = [{ fillColor: "#F4F4F6" }];
addChild(newChatText, 52, 79);

const newChatShortcut = penpot.createText("Ctrl+N");
newChatShortcut.fontSize = 10;
newChatShortcut.fills = [{ fillColor: "#5C6170" }];
addChild(newChatShortcut, 188, 81);

const navHeader = penpot.createText("概览 OVERVIEW");
navHeader.fontSize = 10;
navHeader.fontWeight = "700";
navHeader.fills = [{ fillColor: "#636779" }];
addChild(navHeader, 24, 126);

// Helper for clean list row
function createNavRow(name, label, iconSvg, y, isActive) {
  if (isActive) {
    const activeBg = penpot.createRectangle();
    activeBg.name = name + "_Active_Bg";
    activeBg.resize(220, 36);
    activeBg.borderRadius = 6;
    activeBg.fills = [{ fillColor: "#1A1C26" }];
    addChild(activeBg, 20, y);

    const indicator = penpot.createRectangle();
    indicator.name = name + "_Indicator";
    indicator.resize(3, 18);
    indicator.borderRadius = 2;
    indicator.fills = [{ fillColor: "#6366F1" }];
    addChild(indicator, 20, y + 9);
  }

  createSvg(iconSvg, 32, y + 10);

  const t = penpot.createText(label);
  t.name = name + "_Label";
  t.fontSize = 13;
  t.fontWeight = isActive ? "600" : "400";
  t.fills = [{ fillColor: isActive ? "#F4F4F6" : "#8E929E" }];
  addChild(t, 56, y + 10);
}

// Nav items
const homeSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`;
createNavRow("Nav_Dashboard", "主工作台", homeSvg, 148, true);

const historySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
createNavRow("Nav_History", "历史对话 (包含归档)", historySvg, 188, false);

const taskSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`;
createNavRow("Nav_Tasks", "计划任务", taskSvg, 228, false);

const projectSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`;
createNavRow("Nav_Projects", "项目空间", projectSvg, 268, false);

const sessionHeader = penpot.createText("最近会话 SESSIONS");
sessionHeader.fontSize = 10;
sessionHeader.fontWeight = "700";
sessionHeader.fills = [{ fillColor: "#636779" }];
addChild(sessionHeader, 24, 322);

const msgSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>`;
createNavRow("Session_1", "优化工作树执行流", msgSvg1, 344, false);

const msgSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>`;
createNavRow("Session_2", "Docker 沙箱内存隔离", msgSvg2, 384, false);

const msgSvg3 = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>`;
createNavRow("Session_3", "PydanticAI 契约核重构", msgSvg3, 424, false);

// Bottom User Profile & Settings (KokonutUI Bottom Bar)
const bottomDivider = penpot.createRectangle();
bottomDivider.resize(220, 1);
bottomDivider.fills = [{ fillColor: "#1E2028" }];
addChild(bottomDivider, 20, 890);

const userAvatar = penpot.createRectangle();
userAvatar.resize(32, 32);
userAvatar.borderRadius = 16;
userAvatar.fills = [{ fillColor: "#2A2C38" }];
addChild(userAvatar, 20, 908);

const userInitials = penpot.createText("FA");
userInitials.fontSize = 11;
userInitials.fontWeight = "700";
userInitials.fills = [{ fillColor: "#ECEEF2" }];
addChild(userInitials, 28, 917);

const userName = penpot.createText("FAST");
userName.fontSize = 12;
userName.fontWeight = "600";
userName.fills = [{ fillColor: "#F4F4F6" }];
addChild(userName, 60, 912);

const userRole = penpot.createText("Lead Developer");
userRole.fontSize = 10;
userRole.fills = [{ fillColor: "#636779" }];
addChild(userRole, 60, 927);

const settingsSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`;
createSvg(settingsSvg, 218, 916);

// ==============================================================================
// 6. Right Panel (340px wide, KokonutUI 8-Tool Matrix)
// ==============================================================================
const rightBg = penpot.createRectangle();
rightBg.name = "Right_Panel_Surface";
rightBg.resize(340, 960);
rightBg.fills = [{ fillColor: "#111217" }];
rightBg.strokes = [{ strokeColor: "#1E2028", strokeWidth: 1 }];
addChild(rightBg, 1260, 0);

// Top Tab Bar
const tabActive = penpot.createRectangle();
tabActive.name = "Tab_Active";
tabActive.resize(100, 32);
tabActive.borderRadius = 6;
tabActive.fills = [{ fillColor: "#1A1C24" }];
addChild(tabActive, 1276, 14);

const tabTitle = penpot.createText("新标签页");
tabTitle.fontSize = 12;
tabTitle.fontWeight = "600";
tabTitle.fills = [{ fillColor: "#F4F4F6" }];
addChild(tabTitle, 1288, 22);

const closeSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
createSvg(closeSvg, 1356, 24);

const addTabSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvg(addTabSvg, 1386, 23);

// Window controls [ ◫  ⛶ ]
const splitSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/></svg>`;
createSvg(splitSvg, 1546, 23);

const fullSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>`;
createSvg(fullSvg, 1570, 23);

const tabDivider = penpot.createRectangle();
tabDivider.resize(340, 1);
tabDivider.fills = [{ fillColor: "#1E2028" }];
addChild(tabDivider, 1260, 56);

const toolsHeaderSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`;
createSvg(toolsHeaderSvg, 1276, 74);

const toolsHeader = penpot.createText("快捷工具 (TOOLS)");
toolsHeader.fontSize = 12;
toolsHeader.fontWeight = "700";
toolsHeader.fills = [{ fillColor: "#F4F4F6" }];
addChild(toolsHeader, 1296, 73);

// 8 Tool Cards in a 4 rows x 2 columns Matrix
// Uniform Dark Container + KokonutUI Soft Pastel Squircle Badge
function createKokonutToolCard(x, y, title, subtitle, shortcut, squircleBg, iconColor, iconSvgStr) {
  // Unified Dark Container
  const card = penpot.createRectangle();
  card.name = "Tool_Card_" + title;
  card.resize(146, 72);
  card.borderRadius = 10;
  card.fills = [{ fillColor: "#161720" }];
  card.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
  addChild(card, x, y);

  // Soft Pastel Squircle (KokonutUI Signature)
  const squircle = penpot.createRectangle();
  squircle.name = title + "_Squircle";
  squircle.resize(26, 26);
  squircle.borderRadius = 7;
  squircle.fills = [{ fillColor: squircleBg }];
  addChild(squircle, x + 10, y + 10);

  // Icon
  createSvg(iconSvgStr, x + 15, y + 15);

  // Title
  const t = penpot.createText(title);
  t.fontSize = 12;
  t.fontWeight = "600";
  t.fills = [{ fillColor: "#ECEEF2" }];
  addChild(t, x + 44, y + 10);

  // Subtitle
  const sub = penpot.createText(subtitle);
  sub.fontSize = 9;
  sub.fills = [{ fillColor: "#5C6170" }];
  addChild(sub, x + 44, y + 25);

  // Bottom Shortcut Badge (KokonutUI Micro Pill)
  const badgeBg = penpot.createRectangle();
  badgeBg.resize(68, 16);
  badgeBg.borderRadius = 4;
  badgeBg.fills = [{ fillColor: "#1C1E27" }];
  badgeBg.strokes = [{ strokeColor: "#262936", strokeWidth: 0.5 }];
  addChild(badgeBg, x + 10, y + 46);

  const badgeText = penpot.createText(shortcut);
  badgeText.fontSize = 9;
  badgeText.fontWeight = "500";
  badgeText.fills = [{ fillColor: "#7E8494" }];
  addChild(badgeText, x + 14, y + 48);
}

const diffSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9"/><path d="M12 12v3"/></svg>`;
createKokonutToolCard(1276, 104, "变更", "Git 暂存审查", "Ctrl+Shift+G", "#1E1B4B", "#818CF8", diffSvg);

const termSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>`;
createKokonutToolCard(1438, 104, "终端", "沙箱 Bash", "Ctrl+`", "#064E3B", "#34D399", termSvg);

const fileSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>`;
createKokonutToolCard(1276, 188, "文件", "工作区文件树", "Ctrl+P", "#1E3A8A", "#60A5FA", fileSvg);

const sideChatSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C084FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
createKokonutToolCard(1438, 188, "侧边聊天", "独立对话沙盒", "Ctrl+Alt+S", "#581C87", "#C084FC", sideChatSvg);

const subagentSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F472B6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;
createKokonutToolCard(1276, 272, "子智能体", "调研与质检员", "只读协作", "#831843", "#F472B6", subagentSvg);

const metricsSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`;
createKokonutToolCard(1438, 272, "指标监控", "Token 与成本", "实时跟踪", "#78350F", "#FBBF24", metricsSvg);

const mcpSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6"/><path d="m4.93 4.93 4.24 4.24"/><path d="M2 12h6"/><path d="m4.93 19.07 4.24-4.24"/><path d="M12 22v-6"/><path d="m19.07 19.07-4.24-4.24"/><path d="M22 12h-6"/><path d="m19.07 4.93-4.24 4.24"/></svg>`;
createKokonutToolCard(1276, 356, "MCP 市场", "协议工具扩展", "已就绪", "#164E63", "#22D3EE", mcpSvg);

const skillSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#A78BFA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`;
createKokonutToolCard(1438, 356, "Skill 市场", "工作流生态", "已同步", "#4C1D95", "#A78BFA", skillSvg);

const statusCard = penpot.createRectangle();
statusCard.resize(308, 140);
statusCard.borderRadius = 10;
statusCard.fills = [{ fillColor: "#161720" }];
statusCard.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
addChild(statusCard, 1276, 448);

const statusTitle = penpot.createText("系统运行状态 (SYSTEM STATUS)");
statusTitle.fontSize = 11;
statusTitle.fontWeight = "700";
statusTitle.fills = [{ fillColor: "#8E929E" }];
addChild(statusTitle, 1290, 462);

const statusRow1 = penpot.createText("Docker 沙箱: 运行中 (v24.0.7)");
statusRow1.fontSize = 11;
statusRow1.fills = [{ fillColor: "#34D399" }];
addChild(statusRow1, 1290, 486);

const statusRow2 = penpot.createText("Git Worktree: feature/auth-refactor");
statusRow2.fontSize = 11;
statusRow2.fills = [{ fillColor: "#ECEEF2" }];
addChild(statusRow2, 1290, 508);

const statusRow3 = penpot.createText("上下文水位: 4,210 / 128,000 tokens (3.2%)");
statusRow3.fontSize = 11;
statusRow3.fills = [{ fillColor: "#7E8494" }];
addChild(statusRow3, 1290, 530);

const statusRow4 = penpot.createText("已挂载 MCP 工具: 14 个 | 活跃 Skills: 3 个");
statusRow4.fontSize = 11;
statusRow4.fills = [{ fillColor: "#7E8494" }];
addChild(statusRow4, 1290, 552);

// ==============================================================================
// 7. Center Workspace (Focused, Calm, Floating Glass Console)
// ==============================================================================
// Top Breadcrumb & Controls
const breadcrumb = penpot.createText("vera-agent  /  主工作台  /  优化工作树执行流");
breadcrumb.fontSize = 13;
breadcrumb.fontWeight = "500";
breadcrumb.fills = [{ fillColor: "#8E929E" }];
addChild(breadcrumb, 290, 24);

// Workspace Center Info (Empty state / waiting prompt)
const welcomeTitle = penpot.createText("智能体协作就绪");
welcomeTitle.fontSize = 22;
welcomeTitle.fontWeight = "700";
welcomeTitle.fills = [{ fillColor: "#F4F4F6" }];
addChild(welcomeTitle, 700, 320);

const welcomeSub = penpot.createText("在下方输入任务目标，或按 / 调用专业子智能体 (调研员 / 审查员)");
welcomeSub.fontSize = 13;
welcomeSub.fills = [{ fillColor: "#636779" }];
addChild(welcomeSub, 595, 355);

// Floating Project Selector Capsule
const projectCapsule = penpot.createRectangle();
projectCapsule.name = "Project_Selector_Capsule";
projectCapsule.resize(230, 32);
projectCapsule.borderRadius = 16;
projectCapsule.fills = [{ fillColor: "#14161F" }];
projectCapsule.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
addChild(projectCapsule, 645, 660);

const folderSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`;
createSvg(folderSvg, 658, 670);

const projectLabel = penpot.createText("当前项目: vera-agent ▾");
projectLabel.fontSize = 12;
projectLabel.fontWeight = "500";
projectLabel.fills = [{ fillColor: "#ECEEF2" }];
addChild(projectLabel, 678, 668);

// Floating Signature Glass Console (Width: 720, Height: 124)
const consoleCard = penpot.createRectangle();
consoleCard.name = "Main_Prompt_Console";
consoleCard.resize(720, 124);
consoleCard.borderRadius = 16;
consoleCard.fills = [{ fillColor: "#13141D" }];
consoleCard.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
consoleCard.shadows = [{
  type: "drop-shadow",
  color: "#000000",
  x: 0,
  y: 12,
  blur: 32,
  spread: 0,
  hidden: false
}];
addChild(consoleCard, 400, 706);

// Inner Text Placeholder
const promptPlaceholder = penpot.createText("Ask anything, / for actions, @ to mention subagents...");
promptPlaceholder.fontSize = 14;
promptPlaceholder.fills = [{ fillColor: "#5A5F70" }];
addChild(promptPlaceholder, 424, 726);

// Bottom Action Bar inside console
// Left '+' button
const attachBtn = penpot.createRectangle();
attachBtn.resize(28, 28);
attachBtn.borderRadius = 7;
attachBtn.fills = [{ fillColor: "#1A1C25" }];
attachBtn.strokes = [{ strokeColor: "#262936", strokeWidth: 1 }];
addChild(attachBtn, 424, 786);

const attachSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8E929E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvg(attachSvg, 431, 793);

// Model Selector Capsule
const modelCapsule = penpot.createRectangle();
modelCapsule.resize(130, 28);
modelCapsule.borderRadius = 7;
modelCapsule.fills = [{ fillColor: "#1A1C25" }];
modelCapsule.strokes = [{ strokeColor: "#262936", strokeWidth: 1 }];
addChild(modelCapsule, 460, 786);

const sparkSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`;
createSvg(sparkSvg, 468, 793);

const modelText = penpot.createText("DeepSeek-V3 ▾");
modelText.fontSize = 11;
modelText.fontWeight = "500";
modelText.fills = [{ fillColor: "#ECEEF2" }];
addChild(modelText, 486, 792);

// Right Microphone
const micSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>`;
createSvg(micSvg, 1028, 792);

// Right Send Button (KokonutUI Gradient Accent Button)
const sendBtn = penpot.createRectangle();
sendBtn.name = "Send_Button";
sendBtn.resize(34, 34);
sendBtn.borderRadius = 9;
sendBtn.fills = [{ fillColor: "#6366F1" }];
addChild(sendBtn, 1064, 783);

const sendSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
createSvg(sendSvg, 1073, 792);

return {
  success: true,
  boardId: board.id,
  shapesCreated: penpot.currentPage.findShapes().length
};
