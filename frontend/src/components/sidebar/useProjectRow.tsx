import React, { useEffect, useState } from 'react';
import { fetchGroups } from '../../api/projectApi';
import { useChatStore } from '../../stores/chatStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { Group } from '../../types/project';
import { ProjectRowProps } from './ProjectRowParts';
export function useProjectRow({
  project,
  threads,
  activeThreadId,
  onSelectThread,
  onNewDraftInProject,
  onContextMenu,
  onPinProject,
  onEditProject,
  onDeleteProject,
  editingThreadId = null,
  onRenameThread,
}: ProjectRowProps) {
  const { rightCollapsed, toggleRight } = useRightSidebarLayout();
  const { openTab } = useToolTabsStore();
  const [isExpanded, setIsExpanded] = useState(true);
  const [limit, setLimit] = useState(5);
  const [projectGroups, setProjectGroups] = useState<Group[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [groupThreadLimits, setGroupThreadLimits] = useState<Record<string, number>>({});
  const [menuPosition, setMenuPosition] = useState<{ left: number; top: number } | null>(null);
  useEffect(() => {
    if (!menuPosition) return;
    const close = () => setMenuPosition(null);
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    window.addEventListener('resize', close);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
      window.removeEventListener('resize', close);
    };
  }, [menuPosition]);
  const openMenu = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    setMenuPosition({
      left: Math.min(rect.right - 174, window.innerWidth - 182),
      top: Math.min(rect.bottom + 4, window.innerHeight - 116),
    });
  };
  useEffect(() => {
    if (!isExpanded) return;
    let active = true;
    const loadProjectGroups = async () => {
      try {
        const result = await fetchGroups(project.id);
        if (!active) return;
        await useChatStore.getState().loadThreads();
        if (!active) return;
        const orchestrationGroups = (result.groups || []).filter(
          (group) => group.group_mode === 'workflow' || group.group_mode === 'architecture',
        );
        setProjectGroups(orchestrationGroups);
        setExpandedGroups((current) => {
          const next = { ...current };
          orchestrationGroups.forEach((group) => {
            if (next[group.group_id] === undefined) next[group.group_id] = true;
          });
          return next;
        });
      } catch {
        if (active) setProjectGroups([]);
      }
    };
    void loadProjectGroups();
    const refresh = (event: Event) => {
      const detail = (event as CustomEvent<{ projectId?: string }>).detail;
      if (!detail?.projectId || detail.projectId === project.id) void loadProjectGroups();
    };
    window.addEventListener('orchestration:instances-updated', refresh);
    return () => {
      active = false;
      window.removeEventListener('orchestration:instances-updated', refresh);
    };
  }, [isExpanded, project.id]);
  const orchestrationIds = new Set(projectGroups.map((group) => group.group_id));
  const ordinaryThreads = threads.filter((thread) => !thread.group_id || !orchestrationIds.has(thread.group_id));
  const editGroupInstance = (group: Group) => {
    if (rightCollapsed) toggleRight();
    openTab('workflow', '流程编排', undefined, project.id);
    window.setTimeout(
      () =>
        window.dispatchEvent(
          new CustomEvent('orchestration:edit-instance', {
            detail: { projectId: project.id, groupId: group.group_id },
          }),
        ),
      100,
    );
  };
  const visibleThreads = ordinaryThreads.slice(0, limit);
  const hasMore = ordinaryThreads.length > limit;
  return {
    project,
    threads,
    activeThreadId,
    onSelectThread,
    onNewDraftInProject,
    onContextMenu,
    onPinProject,
    onEditProject,
    onDeleteProject,
    editingThreadId,
    onRenameThread,
    rightCollapsed,
    toggleRight,
    openTab,
    isExpanded,
    setIsExpanded,
    limit,
    setLimit,
    projectGroups,
    expandedGroups,
    setExpandedGroups,
    groupThreadLimits,
    setGroupThreadLimits,
    menuPosition,
    setMenuPosition,
    openMenu,
    ordinaryThreads,
    editGroupInstance,
    visibleThreads,
    hasMore,
  };
}
