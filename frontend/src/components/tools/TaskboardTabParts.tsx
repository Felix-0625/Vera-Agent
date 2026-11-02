import { WorkItemPriority, WorkItemStatus } from '../../types/tool';
import './taskboard.css';
export const COLUMNS: Array<{ id: WorkItemStatus; title: string }> = [
  { id: 'backlog', title: '待规划' },
  { id: 'todo', title: '待办' },
  { id: 'in_progress', title: '进行中' },
  { id: 'blocked', title: '受阻' },
  { id: 'in_review', title: '待确认' },
  { id: 'done', title: '已完成' },
  { id: 'canceled', title: '已取消' },
];

export const PRIORITIES: Array<{ id: WorkItemPriority; title: string }> = [
  { id: 'urgent', title: '紧急' },
  { id: 'high', title: '高' },
  { id: 'medium', title: '普通' },
  { id: 'low', title: '低' },
  { id: 'none', title: '无' },
];

export interface TaskboardTabProps {
  projectId: string | null;
}

export interface Draft {
  title: string;
  description: string;
  priority: WorkItemPriority;
  labels: string;
}

export const EMPTY_DRAFT: Draft = { title: '', description: '', priority: 'medium', labels: '' };

export function parseLabels(value: string): string[] | null {
  const labels = [
    ...new Set(
      value
        .split(',')
        .map((label) => label.trim())
        .filter(Boolean),
    ),
  ];
  return labels.length <= 20 && labels.every((label) => label.length <= 48) ? labels : null;
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value));
}
