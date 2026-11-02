import { Check, ChevronDown, Folder, FolderOpen, FolderPlus, Plus, Trash2, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { selectProjectFolder } from '../../api/projectApi';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Button } from '../common/Button';
import { EmptyState } from '../common/EmptyState';
import { TextInput } from '../common/Field';
import { IconButton } from '../common/IconButton';
import { Modal } from '../common/Modal';

const projectBlue = 'var(--accent-primary)';
const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).at(-1) || path;

export const ProjectSelectorModal: React.FC = () => {
  const { projectSelectorOpen, projectSelectorView, editingProject, setProjectSelectorOpen } = useLayoutStore();
  const { currentProject, projectsHistory, bindProject, deleteProject, updateProject } = useProjectStore();
  const { openDraftConversation, setDraftProjectId, loadThreads } = useChatStore();
  const [name, setName] = useState('');
  const [folders, setFolders] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [folderPickerBusy, setFolderPickerBusy] = useState(false);
  const isEdit = projectSelectorView === 'edit';
  const isCreate = projectSelectorView === 'create';

  useEffect(() => {
    if (!projectSelectorOpen) return;
    // oxlint-disable-next-line react/set-state-in-effect -- Seed the editable form from the selected project whenever the dialog context changes.
    setError('');
    if (projectSelectorView === 'edit' && editingProject) {
      setName(editingProject.name || '');
      setFolders(editingProject.folders?.length ? editingProject.folders : [editingProject.path]);
    } else {
      setName('');
      setFolders([]);
    }
  }, [projectSelectorOpen, projectSelectorView, editingProject]);

  const browseFolder = async () => {
    if (busy || folderPickerBusy) return;
    setFolderPickerBusy(true);
    setError('');
    try {
      const result = await selectProjectFolder();
      if (result.path) setFolders((current) => (current.includes(result.path!) ? current : [...current, result.path!]));
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法打开系统文件夹选择器，请检查本地服务是否运行。');
    } finally {
      setFolderPickerBusy(false);
    }
  };

  const saveProject = async () => {
    if (!name.trim()) {
      setError('请输入项目名称。');
      return;
    }
    if (!folders.length) {
      setError('请至少选择一个源文件夹。');
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (isEdit && editingProject) {
        await updateProject(editingProject.id, { name: name.trim(), folders });
        const active = useProjectStore.getState().currentProject;
        if (active?.id === editingProject.id && folders[0] !== editingProject.path) {
          openDraftConversation(editingProject.id);
        }
      } else {
        await bindProject(folders[0], { name: name.trim(), folders });
        const created = useProjectStore.getState().currentProject;
        openDraftConversation(created?.id || null);
        await loadThreads();
      }
      setProjectSelectorOpen(false);
    } catch {
      setError('项目保存失败，请确认所选文件夹仍然存在。');
    } finally {
      setBusy(false);
    }
  };

  const selectExisting = async (id: string, path: string, projectName: string, projectFolders?: string[]) => {
    const previousProjectId = useProjectStore.getState().currentProject?.id;
    setBusy(true);
    setError('');
    try {
      await bindProject(path, { projectId: id, name: projectName, folders: projectFolders });
      if (previousProjectId !== id) openDraftConversation(id);
      else setDraftProjectId(id);
      await loadThreads();
      setProjectSelectorOpen(false);
    } catch {
      setError('打开项目失败，请检查项目目录是否仍然可用。');
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveProject = async () => {
    if (!editingProject) return;
    setBusy(true);
    try {
      await deleteProject(editingProject.id);
      setDraftProjectId(null);
      setProjectSelectorOpen(false);
    } catch {
      setError('移除项目失败，请稍后重试。');
    } finally {
      setBusy(false);
    }
  };

  const title = isEdit ? '编辑项目' : isCreate ? '创建项目' : '选择项目';
  return (
    <Modal
      isOpen={projectSelectorOpen}
      onClose={() => setProjectSelectorOpen(false)}
      title={title}
      width={isEdit ? 638 : isCreate ? 650 : 520}
      titleStyle={
        isEdit || isCreate ? { fontSize: 'var(--font-size-3xl)', fontWeight: 700, letterSpacing: '-.02em' } : undefined
      }
      headerStyle={isCreate ? { padding: 'var(--space-5) var(--space-6) var(--space-2)', borderBottom: 0 } : undefined}
      contentStyle={isCreate ? { padding: 'var(--space-3) var(--space-6) var(--space-5)' } : undefined}
    >
      {isEdit || isCreate ? (
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', minHeight: isCreate ? 309 : 324 }}
        >
          {error && (
            <div
              role="alert"
              style={{
                padding: 'var(--space-2) var(--space-2-5)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-danger-soft)',
                color: 'var(--accent-rose)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              {error}
            </div>
          )}
          <label style={{ position: 'relative', display: 'block' }}>
            <Folder size={17} color={projectBlue} style={{ position: 'absolute', left: 17, top: 16, zIndex: 1 }} />
            {isCreate && (
              <span
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  left: 49,
                  top: 1,
                  bottom: 1,
                  width: 1,
                  background: 'var(--border-default)',
                }}
              />
            )}
            <TextInput
              aria-label="项目名称"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="项目名称"
              className={`project-name-input${isCreate ? ' project-name-input--create' : ''}`}
            />
          </label>
          <div>
            <div
              style={{
                marginBottom: 'var(--space-2-25)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-control)',
                fontWeight: 600,
              }}
            >
              源文件夹
            </div>
            <div
              style={
                folders.length
                  ? {
                      border: '1px solid var(--border-default)',
                      borderRadius: 'var(--radius-lg-plus)',
                      overflow: 'hidden',
                      background: 'var(--bg-surface)',
                    }
                  : {
                      minHeight: 130,
                      border: '1px solid var(--border-default)',
                      borderRadius: 'var(--radius-lg-plus)',
                      background: 'var(--bg-surface)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 'var(--space-3)',
                    }
              }
            >
              {folders.map((path, index) => (
                <div
                  key={`${path}-${index}`}
                  style={{
                    minHeight: 54,
                    padding: 'var(--space-2-25) var(--space-3-5)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 11,
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <FolderOpen size={17} color={projectBlue} style={{ flex: '0 0 auto' }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{ fontSize: 'var(--font-size-control)', color: 'var(--text-primary)', fontWeight: 550 }}
                    >
                      {folderName(path)}
                    </div>
                    <div
                      title={path}
                      style={{
                        fontSize: 'var(--font-size-subtle)',
                        color: 'var(--text-muted)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {path}
                    </div>
                  </div>
                  <IconButton
                    label={`移除文件夹 ${folderName(path)}`}
                    onClick={() => setFolders((current) => current.filter((_, i) => i !== index))}
                    size="sm"
                  >
                    <X size={14} />
                  </IconButton>
                </div>
              ))}
              {folders.length ? (
                <Button
                  disabled={busy || folderPickerBusy}
                  onClick={() => void browseFolder()}
                  variant="ghost"
                  size="md"
                  className="project-folder-add-row"
                  icon={<FolderPlus size={17} color={projectBlue} aria-hidden="true" />}
                >
                  {folderPickerBusy ? '正在打开文件夹选择器…' : '添加文件夹'}
                </Button>
              ) : (
                <>
                  <Button
                    disabled={busy || folderPickerBusy}
                    onClick={() => void browseFolder()}
                    variant="ghost"
                    size="sm"
                    className="project-folder-empty-prompt"
                    icon={<ChevronDown size={14} color="var(--text-muted)" aria-hidden="true" />}
                  >
                    {folderPickerBusy ? '正在打开文件夹选择器…' : '在此电脑上添加文件夹'}
                  </Button>
                  <Button
                    disabled={busy || folderPickerBusy}
                    onClick={() => void browseFolder()}
                    variant="secondary"
                    size="sm"
                    className="project-folder-empty-action"
                    icon={<FolderPlus size={15} aria-hidden="true" />}
                  >
                    {folderPickerBusy ? '打开中…' : '添加'}
                  </Button>
                </>
              )}
            </div>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 'var(--space-3)',
              marginTop: 'auto',
              marginBottom: isCreate ? 5 : 0,
            }}
          >
            {isEdit ? (
              <Button disabled={busy} onClick={() => void handleRemoveProject()} variant="danger" size="sm">
                移除本地项目
              </Button>
            ) : (
              <span />
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: isCreate ? 20 : 10 }}>
              <Button
                disabled={busy}
                onClick={() => setProjectSelectorOpen(false)}
                variant="ghost"
                size="sm"
                style={isCreate ? { width: 52, padding: 0, color: 'var(--text-secondary)' } : undefined}
              >
                取消
              </Button>
              <Button
                disabled={busy}
                onClick={() => void saveProject()}
                variant="primary"
                size="sm"
                style={{
                  minWidth: isCreate ? 112 : 92,
                  height: isCreate ? 39 : undefined,
                  padding: isCreate ? '0 16px' : undefined,
                  fontWeight: 700,
                }}
              >
                {busy ? '保存中…' : isEdit ? '保存' : '创建项目'}
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2-25)' }}>
          <div
            style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-0-5)' }}
          >
            选择一个已绑定的本地项目，或创建项目。
          </div>
          {error && (
            <div
              role="alert"
              style={{
                padding: 'var(--space-2) var(--space-2-5)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-danger-soft)',
                color: 'var(--accent-rose)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              {error}
            </div>
          )}
          {projectsHistory.map((project) => {
            const selected = currentProject?.path === project.path || currentProject?.repo_root === project.path;
            return (
              <div
                key={project.id}
                className={`project-history-row${selected ? ' project-history-row--selected' : ''}`}
              >
                <Button
                  type="button"
                  aria-pressed={selected}
                  disabled={busy}
                  variant="ghost"
                  className="project-history-select"
                  onClick={() => void selectExisting(project.id, project.path, project.name, project.folders)}
                >
                  <span className="project-history-icon">
                    <FolderOpen size={16} color={projectBlue} />
                  </span>
                  <span className="project-history-copy">
                    <span className="project-history-name">{project.name}</span>
                    <span className="project-history-path">
                      {project.path}
                      {project.folders && project.folders.length > 1 ? ` · ${project.folders.length} 个文件夹` : ''}
                    </span>
                  </span>
                  {selected && <Check size={15} color={projectBlue} aria-hidden="true" />}
                </Button>
                <IconButton
                  label={`删除 ${project.name} 项目记录`}
                  disabled={busy}
                  onClick={() => void deleteProject(project.id)}
                  tone="danger"
                  size="sm"
                >
                  <Trash2 size={13} />
                </IconButton>
              </div>
            );
          })}
          {!projectsHistory.length && <EmptyState className="project-history-empty" description="还没有绑定项目" />}
          <Button
            onClick={() => useLayoutStore.getState().openProjectCreate()}
            variant="outline"
            size="md"
            className="project-history-create"
            icon={<Plus size={15} aria-hidden="true" />}
          >
            新建项目并选择文件夹
          </Button>
        </div>
      )}
    </Modal>
  );
};
