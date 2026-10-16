import React from 'react';
import { VeraLogo } from '../common/VeraLogo';

/**
 * 中间工作区欢迎空态界面
 * 严格按照 Penpot 原型 "VeraAgent · Conversation Workspace"
 * 仅包含品牌 Logo (54x51) 与文字 "开  始  创  造  吧  ！"，去除一切多余圆圈框
 */
export const WelcomeBanner: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px var(--space-5) 40px',
        userSelect: 'none',
      }}
    >
      {/* 纯净品牌 Logo，无额外圆圈外框与阴影 */}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <VeraLogo size={52} />
      </div>

      {/* 标题严格对齐 Penpot 字符与间距 */}
      <h1
        style={{
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: '3px',
          color: 'var(--text-primary)',
          textAlign: 'center',
          margin: 0,
        }}
      >
        开  始  创  造  吧  ！
      </h1>
    </div>
  );
};
