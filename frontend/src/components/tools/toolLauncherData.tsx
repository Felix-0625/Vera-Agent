import React from 'react';
import {
  FileText,
  Terminal as TerminalIcon,
  Folder,
  MessageSquare,
  Bot,
  Sparkles,
  GitBranch,
  Users,
} from 'lucide-react';
import { ToolTabId } from '../../types/tool';

export interface ToolLauncherItem {
  id: ToolTabId;
  title: string;
  icon: React.ReactNode;
  iconColor: string;
  iconBg: string;
  borderColor: string;
}

/**
 * 右侧工具发射器磁贴数据配置
 * 右侧工具快捷入口
 */
export const TOOL_LAUNCHER_ITEMS: ToolLauncherItem[] = [
  {
    id: 'subagents',
    title: '子智能体',
    icon: <Bot size={17} color="#A78BFA" />,
    iconColor: '#A78BFA',
    iconBg: 'rgba(167, 139, 250, 0.08)',
    borderColor: 'rgba(167, 139, 250, 0.25)',
  },
  {
    id: 'sidechat',
    title: '侧边聊天',
    icon: <MessageSquare size={17} color="#A855F7" />,
    iconColor: '#A855F7',
    iconBg: 'rgba(168, 85, 247, 0.08)',
    borderColor: 'rgba(168, 85, 247, 0.25)',
  },
  {
    id: 'files',
    title: '文件',
    icon: <Folder size={17} color="#06B6D4" />,
    iconColor: '#06B6D4',
    iconBg: 'rgba(6, 182, 212, 0.08)',
    borderColor: 'rgba(6, 182, 212, 0.25)',
  },
  {
    id: 'terminal',
    title: '终端',
    icon: <TerminalIcon size={17} color="#10B981" />,
    iconColor: '#10B981',
    iconBg: 'rgba(16, 185, 129, 0.08)',
    borderColor: 'rgba(16, 185, 129, 0.25)',
  },
  {
    id: 'metrics',
    title: '数据看板',
    icon: <Sparkles size={17} color="#F59E0B" />,
    iconColor: '#F59E0B',
    iconBg: 'rgba(245, 158, 11, 0.08)',
    borderColor: 'rgba(245, 158, 11, 0.25)',
  },
  {
    id: 'diff',
    title: '变更',
    icon: <FileText size={17} color="#F59E0B" />,
    iconColor: '#F59E0B',
    iconBg: 'rgba(245, 158, 11, 0.08)',
    borderColor: 'rgba(245, 158, 11, 0.25)',
  },
  {
    id: 'workflow',
    title: '分组管理',
    icon: <Users size={17} color="#8B5CF6" />,
    iconColor: '#8B5CF6',
    iconBg: 'rgba(139, 92, 246, 0.08)',
    borderColor: 'rgba(139, 92, 246, 0.25)',
  },
  {
    id: 'gitflow',
    title: 'GitFlow',
    icon: <GitBranch size={17} color="#06B6D4" />,
    iconColor: '#06B6D4',
    iconBg: 'rgba(6, 182, 212, 0.08)',
    borderColor: 'rgba(6, 182, 212, 0.25)',
  },
];
