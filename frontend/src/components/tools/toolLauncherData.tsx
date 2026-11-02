import {
  Bot,
  Brain,
  FileText,
  FlaskConical,
  Folder,
  GitBranch,
  GitCommitVertical,
  MessageSquare,
  Sparkles,
  Terminal as TerminalIcon,
  Users,
} from 'lucide-react';
import React from 'react';
import { ToolTabId } from '../../types/tool';

export interface ToolLauncherItem {
  id: ToolTabId;
  title: string;
  icon: React.ReactNode;
  iconColor: string;
  iconBg: string;
  borderColor: string;
}

export const TOOL_LAUNCHER_ITEMS: ToolLauncherItem[] = [
  {
    id: 'subagents',
    title: '子智能体',
    icon: <Bot size={17} color="var(--accent-primary)" />,
    iconColor: 'var(--accent-primary)',
    iconBg: 'var(--bg-accent-soft)',
    borderColor: 'color-mix(in srgb, var(--accent-primary) 25%, var(--border-subtle))',
  },
  {
    id: 'sidechat',
    title: '侧边聊天',
    icon: <MessageSquare size={17} color="var(--accent-primary)" />,
    iconColor: 'var(--accent-primary)',
    iconBg: 'var(--bg-skill-soft)',
    borderColor: 'color-mix(in srgb, var(--accent-skill) 25%, var(--border-subtle))',
  },
  {
    id: 'files',
    title: '文件',
    icon: <Folder size={17} color="var(--accent-primary)" />,
    iconColor: 'var(--accent-cyan)',
    iconBg: 'var(--bg-info-soft)',
    borderColor: 'var(--border-info-soft)',
  },
  {
    id: 'terminal',
    title: '终端',
    icon: <TerminalIcon size={17} color="var(--accent-emerald)" />,
    iconColor: 'var(--accent-emerald)',
    iconBg: 'var(--bg-success-soft)',
    borderColor: 'var(--border-success-soft)',
  },
  {
    id: 'metrics',
    title: '数据看板',
    icon: <Sparkles size={17} color="var(--accent-amber)" />,
    iconColor: 'var(--accent-amber)',
    iconBg: 'var(--bg-warning-soft)',
    borderColor: 'var(--border-warning-soft)',
  },
  {
    id: 'diff',
    title: '变更',
    icon: <FileText size={17} color="var(--accent-amber)" />,
    iconColor: 'var(--accent-amber)',
    iconBg: 'var(--bg-warning-soft)',
    borderColor: 'var(--border-warning-soft)',
  },
  {
    id: 'workflow',
    title: '流程编排',
    icon: <Users size={17} color="var(--accent-primary)" />,
    iconColor: 'var(--accent-primary)',
    iconBg: 'var(--bg-accent-soft)',
    borderColor: 'color-mix(in srgb, var(--accent-primary) 25%, var(--border-subtle))',
  },
  {
    id: 'gitflow',
    title: 'GitFlow',
    icon: <GitBranch size={17} color="var(--accent-primary)" />,
    iconColor: 'var(--accent-cyan)',
    iconBg: 'var(--bg-info-soft)',
    borderColor: 'var(--border-info-soft)',
  },
  {
    id: 'traces',
    title: '执行记录',
    icon: <GitCommitVertical size={17} color="var(--accent-cyan)" />,
    iconColor: 'var(--accent-cyan)',
    iconBg: 'var(--bg-info-soft)',
    borderColor: 'var(--border-info-soft)',
  },
  {
    id: 'memory',
    title: '长期记忆',
    icon: <Brain size={17} color="var(--accent-emerald)" />,
    iconColor: 'var(--accent-emerald)',
    iconBg: 'var(--bg-success-soft)',
    borderColor: 'var(--border-success-soft)',
  },
  {
    id: 'evolution',
    title: '改进提案',
    icon: <FlaskConical size={17} color="var(--accent-amber)" />,
    iconColor: 'var(--accent-amber)',
    iconBg: 'var(--bg-warning-soft)',
    borderColor: 'var(--border-warning-soft)',
  },
];
