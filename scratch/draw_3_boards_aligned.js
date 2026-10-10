// ==============================================================================
// 3 Sub-Interfaces: 左侧边栏, 中间主工作区, 右侧边栏
// Strictly aligned with user mockup collage & KokonutUI aesthetics
// ==============================================================================

// 1. Clean existing boards on Page 1
const existing = penpot.currentPage.findShapes().filter(s => s.type === 'board');
for (const b of existing) {
  try { b.remove(); } catch (e) {}
}

// Helper: safe add child
function addChildTo(parent, child, x, y) {
  if (!child) return;
  parent.appendChild(child);
  penpotUtils.setParentXY(child, x, y);
}

// Helper: safe SVG creation
function createSvgIn(parent, svgStr, x, y) {
  try {
    const shape = penpot.createShapeFromSvg(svgStr);
    if (shape) {
      addChildTo(parent, shape, x, y);
      return shape;
    }
  } catch (e) {
    console.log("SVG error:", e);
  }
  return null;
}

// ==============================================================================
// BOARD 1: 左侧边栏 (Left Sidebar) - 250 x 900
// ==============================================================================
const board1 = penpot.createBoard();
board1.name = "1. 左侧边栏 (Left Sidebar)";
board1.x = 0;
board1.y = 0;
board1.resize(250, 900);
board1.fills = [{ fillColor: "#111217" }];
board1.strokes = [{ strokeColor: "#1E2028", strokeWidth: 1 }];

// Top Row: V Logo + 3 Controls [ ◫ ] [ ← ] [ → ]
const vLogoSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="7" fill="#1A1C26" stroke="#2E3245" stroke-width="1"/>
  <path d="M8 9 L16 23 L24 9" fill="none" stroke="#818CF8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
createSvgIn(board1, vLogoSvg, 16, 16);

// Nav buttons [ ◫ ] [ ← ] [ → ]
const sidebarIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>`;
createSvgIn(board1, sidebarIconSvg, 48, 20);

const backSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>`;
createSvgIn(board1, backSvg, 72, 20);

const forwardSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>`;
createSvgIn(board1, forwardSvg, 96, 20);

// '+ 新建对话' Button (Capsule)
const newChatBtn = penpot.createRectangle();
newChatBtn.name = "New_Chat_Btn";
newChatBtn.resize(218, 36);
newChatBtn.borderRadius = 8;
newChatBtn.fills = [{ fillColor: "#1A1C24" }];
newChatBtn.strokes = [{ strokeColor: "#2A2C38", strokeWidth: 1 }];
addChildTo(board1, newChatBtn, 16, 56);

const plusSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, plusSvg, 28, 68);

const newChatText = penpot.createText("+ 新建对话");
newChatText.fontSize = 12;
newChatText.fontWeight = "600";
newChatText.fills = [{ fillColor: "#ECEEF2" }];
addChildTo(board1, newChatText, 46, 66);

// History & Tasks List Rows
const histSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
createSvgIn(board1, histSvg, 20, 108);

const histText = penpot.createText("历史对话");
histText.fontSize = 12;
histText.fills = [{ fillColor: "#8E929E" }];
addChildTo(board1, histText, 42, 107);

const taskSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`;
createSvgIn(board1, taskSvg, 20, 142);

const taskText = penpot.createText("计划任务");
taskText.fontSize = 12;
taskText.fills = [{ fillColor: "#8E929E" }];
addChildTo(board1, taskText, 42, 141);

// Section: 项目 (Projects)
const projHeader = penpot.createText("项目");
projHeader.fontSize = 11;
projHeader.fontWeight = "600";
projHeader.fills = [{ fillColor: "#636779" }];
addChildTo(board1, projHeader, 16, 186);

// Filter icon [ ☷ ] and Add icon [ + ] on right of '项目'
const filterSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>`;
createSvgIn(board1, filterSvg, 194, 187);

const addSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, addSvg1, 216, 187);

// Item: 📁 项目名称
const folderSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`;
createSvgIn(board1, folderSvg1, 18, 212);

const projNameText = penpot.createText("项目名称");
projNameText.fontSize = 12;
projNameText.fontWeight = "600";
projNameText.fills = [{ fillColor: "#ECEEF2" }];
addChildTo(board1, projNameText, 38, 211);

// Icons on right of 项目名称: [ ! ] and [ + ]
const alertSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>`;
createSvgIn(board1, alertSvg, 194, 213);

const addSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, addSvg2, 216, 213);

// Nested Active Conversation Card: 对话 [ ⋮ ] [ 📌 ] [ + ]
const activeChatBox = penpot.createRectangle();
activeChatBox.name = "Active_Chat_Box";
activeChatBox.resize(206, 32);
activeChatBox.borderRadius = 6;
activeChatBox.fills = [{ fillColor: "#161822" }];
activeChatBox.strokes = [{ strokeColor: "#3B4254", strokeWidth: 1 }];
addChildTo(board1, activeChatBox, 28, 238);

const activeChatText = penpot.createText("对话");
activeChatText.fontSize = 12;
activeChatText.fontWeight = "600";
activeChatText.fills = [{ fillColor: "#F4F4F6" }];
addChildTo(board1, activeChatText, 40, 246);

// [ ⋮ ] [ 📌 ] [ + ]
const dotsSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>`;
createSvgIn(board1, dotsSvg1, 168, 248);

const pinSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="17" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>`;
createSvgIn(board1, pinSvg1, 188, 248);

const addSvg3 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, addSvg3, 208, 248);

// Section: 会话 (Conversations)
const convHeader = penpot.createText("会话");
convHeader.fontSize = 11;
convHeader.fontWeight = "600";
convHeader.fills = [{ fillColor: "#636779" }];
addChildTo(board1, convHeader, 16, 296);

const addSvg4 = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, addSvg4, 216, 297);

// Standalone Conversation item: 对话 [ ⋮ ] [ 📌 ] [ + ]
const convItemText = penpot.createText("对话");
convItemText.fontSize = 12;
convItemText.fills = [{ fillColor: "#8E929E" }];
addChildTo(board1, convItemText, 24, 324);

const dotsSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>`;
createSvgIn(board1, dotsSvg2, 168, 325);

const pinSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="17" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>`;
createSvgIn(board1, pinSvg2, 188, 325);

const addSvg5 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board1, addSvg5, 208, 325);

// Bottom: ⚙ 设置
const settingsSvg1 = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`;
createSvgIn(board1, settingsSvg1, 18, 862);

const settingsText = penpot.createText("设置");
settingsText.fontSize = 12;
settingsText.fills = [{ fillColor: "#8E929E" }];
addChildTo(board1, settingsText, 38, 861);


// ==============================================================================
// BOARD 2: 中间区域 (Center Workspace) - 860 x 900
// ==============================================================================
const board2 = penpot.createBoard();
board2.name = "2. 中间区域 (Center Workspace)";
board2.x = 280;
board2.y = 0;
board2.resize(860, 900);
board2.fills = [{ fillColor: "#0D0E12" }];

// Subtle Ambient Nocturne Glow
const glow2 = penpot.createRectangle();
glow2.resize(500, 350);
glow2.borderRadius = 175;
glow2.fills = [{ fillColor: "#1E1B4B", fillOpacity: 0.12 }];
glow2.blur = { type: "layer", value: 100 };
addChildTo(board2, glow2, 180, 200);

// Top Right IDE Layout Controls: [ ◫  ⛶ ]
const layoutCapsule = penpot.createRectangle();
layoutCapsule.resize(58, 26);
layoutCapsule.borderRadius = 6;
layoutCapsule.fills = [{ fillColor: "#131C24" }];
layoutCapsule.strokes = [{ strokeColor: "#155E75", strokeWidth: 1 }];
addChildTo(board2, layoutCapsule, 786, 16);

const splitSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/></svg>`;
createSvgIn(board2, splitSvg2, 794, 23);

const fullSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>`;
createSvgIn(board2, fullSvg2, 822, 23);

// Floating Project Selector Capsule: [ 📁 选择项目 ]
// Exactly positioned on the left side, above input card!
const projCapsule = penpot.createRectangle();
projCapsule.name = "Project_Capsule";
projCapsule.resize(116, 32);
projCapsule.borderRadius = 6;
projCapsule.fills = [{ fillColor: "#161720" }];
projCapsule.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
addChildTo(board2, projCapsule, 60, 420);

const folderSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`;
createSvgIn(board2, folderSvg2, 72, 429);

const projCapsuleText = penpot.createText("选择项目");
projCapsuleText.fontSize = 12;
projCapsuleText.fontWeight = "600";
projCapsuleText.fills = [{ fillColor: "#ECEEF2" }];
addChildTo(board2, projCapsuleText, 94, 428);

// Floating Signature Input Card (Width: 740, Height: 116)
const inputCard = penpot.createRectangle();
inputCard.name = "Main_Input_Card";
inputCard.resize(740, 116);
inputCard.borderRadius = 16;
inputCard.fills = [{ fillColor: "#14151D" }];
inputCard.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
inputCard.shadows = [{
  type: "drop-shadow",
  color: "#000000",
  x: 0,
  y: 12,
  blur: 32,
  spread: 0,
  hidden: false
}];
addChildTo(board2, inputCard, 60, 464);

// Placeholder: Ask anything, / for actions
const placeholderText = penpot.createText("Ask anything, / for actions");
placeholderText.fontSize = 14;
placeholderText.fills = [{ fillColor: "#636779" }];
addChildTo(board2, placeholderText, 84, 486);

// Bottom row inside input card:
// '+' button
const plusActionSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8E929E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board2, plusActionSvg, 84, 542);

// Model Switch Dropdown Capsule: 模型切换 ▾
const modelSwitchText = penpot.createText("模型切换 ▾");
modelSwitchText.fontSize = 12;
modelSwitchText.fontWeight = "600";
modelSwitchText.fills = [{ fillColor: "#ECEEF2" }];
addChildTo(board2, modelSwitchText, 140, 541);

// Microphone icon on right
const micSvg2 = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>`;
createSvgIn(board2, micSvg2, 706, 541);

// Send Button '→' (Rounded circle/squircle)
const sendBtn2 = penpot.createRectangle();
sendBtn2.resize(30, 30);
sendBtn2.borderRadius = 15;
sendBtn2.fills = [{ fillColor: "#222530" }];
addChildTo(board2, sendBtn2, 744, 534);

const sendArrowSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ECEEF2" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
createSvgIn(board2, sendArrowSvg, 752, 542);


// ==============================================================================
// BOARD 3: 右侧边栏 (Right Sidebar) - 480 x 900
// ==============================================================================
const board3 = penpot.createBoard();
board3.name = "3. 右侧边栏 (Right Sidebar)";
board3.x = 1170;
board3.y = 0;
board3.resize(480, 900);
board3.fills = [{ fillColor: "#111217" }];
board3.strokes = [{ strokeColor: "#1E2028", strokeWidth: 1 }];

// Top Tab Bar: ⊕ 新标签页 x   +           [ ⛶ ] [ ◫ ]
const tabBg = penpot.createRectangle();
tabBg.resize(130, 32);
tabBg.borderRadius = 6;
tabBg.fills = [{ fillColor: "#1A1C24" }];
addChildTo(board3, tabBg, 16, 14);

const globeSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`;
createSvgIn(board3, globeSvg, 26, 23);

const tabName = penpot.createText("新标签页");
tabName.fontSize = 12;
tabName.fontWeight = "600";
tabName.fills = [{ fillColor: "#F4F4F6" }];
addChildTo(board3, tabName, 44, 22);

const closeSvg3 = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
createSvgIn(board3, closeSvg3, 126, 24);

const addTabSvg3 = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`;
createSvgIn(board3, addTabSvg3, 160, 23);

// Window controls [ ⛶ ] [ ◫ ] on far right of right sidebar
const maxSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>`;
createSvgIn(board3, maxSvg, 420, 23);

const panelSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#717688" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M15 3v18"/></svg>`;
createSvgIn(board3, panelSvg, 448, 23);

// Divider line
const divider3 = penpot.createRectangle();
divider3.resize(480, 1);
divider3.fills = [{ fillColor: "#1E2028" }];
addChildTo(board3, divider3, 0, 56);

// Section: 工具 (Header)
const toolsTitle = penpot.createText("工具");
toolsTitle.fontSize = 15;
toolsTitle.fontWeight = "700";
toolsTitle.fills = [{ fillColor: "#F4F4F6" }];
addChildTo(board3, toolsTitle, 16, 76);

// 8 Tool Cards in 4 rows x 2 cols
// Width: 218px each, Gap: 12px, Height: 52px
function createToolItem(x, y, iconSvg, title) {
  const card = penpot.createRectangle();
  card.resize(218, 52);
  card.borderRadius = 8;
  card.fills = [{ fillColor: "#161720" }];
  card.strokes = [{ strokeColor: "#222530", strokeWidth: 1 }];
  addChildTo(board3, card, x, y);

  if (iconSvg) {
    createSvgIn(board3, iconSvg, x + 16, y + 18);
    const t = penpot.createText(title);
    t.fontSize = 13;
    t.fontWeight = "600";
    t.fills = [{ fillColor: "#ECEEF2" }];
    addChildTo(board3, t, x + 40, y + 17);
  } else {
    const t = penpot.createText(title);
    t.fontSize = 13;
    t.fontWeight = "600";
    t.fills = [{ fillColor: "#ECEEF2" }];
    addChildTo(board3, t, x + 16, y + 17);
  }
}

// Row 1: 变更 | 终端
const diffIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9"/><path d="M12 12v3"/></svg>`;
createToolItem(16, 110, diffIcon, "变更");

const termIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>`;
createToolItem(246, 110, termIcon, "终端");

// Row 2: 文件 | 侧边聊天
const fileIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>`;
createToolItem(16, 174, fileIcon, "文件");

const chatIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#C084FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
createToolItem(246, 174, chatIcon, "侧边聊天");

// Row 3: 子智能体 | 指标监控
const subagentIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F472B6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;
createToolItem(16, 238, subagentIcon, "子智能体");

createToolItem(246, 238, null, "指标监控");

// Row 4: MCP 市场 | SKILL 市场
createToolItem(16, 302, null, "MCP 市场");

createToolItem(246, 302, null, "SKILL 市场");

return {
  success: true,
  boards: [board1.name, board2.name, board3.name],
  totalShapes: penpot.currentPage.findShapes().length
};