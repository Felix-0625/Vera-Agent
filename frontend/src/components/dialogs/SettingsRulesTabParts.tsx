import React from 'react';
import { UserMemory } from '../../api/settingsApi';
export const categories: Array<{ value: UserMemory['category']; label: string }> = [
  { value: 'profile', label: '用户背景' },
  { value: 'preference', label: '偏好' },
  { value: 'habit', label: '习惯' },
  { value: 'feedback', label: '已确认的反馈' },
];

export const cardStyle: React.CSSProperties = {
  padding: 'var(--space-4) var(--space-4-5)',
  borderRadius: 'var(--radius-md)',
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
};
