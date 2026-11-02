import { useEffect, useState } from 'react';
import {
  deleteUserMemory,
  fetchRules,
  fetchUserMemories,
  saveContextSettings,
  saveRules,
  saveUserMemory,
  UserContextSettings,
  UserMemory,
} from '../../api/settingsApi';
export function useSettingsRulesTab() {
  const [settings, setSettings] = useState<UserContextSettings>({
    user_rules: '',
    include_agents_md: true,
    memory_enabled: true,
  });
  const [memories, setMemories] = useState<UserMemory[]>([]);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memoryToDelete, setMemoryToDelete] = useState<UserMemory | null>(null);
  const [rulesDraft, setRulesDraft] = useState('');
  const [memoryDraft, setMemoryDraft] = useState<{ id?: string; category: UserMemory['category']; content: string }>({
    category: 'preference',
    content: '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const load = async () => {
    try {
      const [context, profile] = await Promise.all([fetchRules(), fetchUserMemories()]);
      setSettings(context);
      setMemories(profile.memories || []);
      setError('');
    } catch {
      setError('读取规则与记忆设置失败，请检查服务连接。');
    }
  };
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Load persisted settings when this tab mounts.
    void load();
  }, []);
  const toggleSetting = async (key: 'include_agents_md' | 'memory_enabled', checked: boolean) => {
    setBusy(true);
    setError('');
    try {
      setSettings(await saveContextSettings({ [key]: checked }));
    } catch {
      setError('保存设置失败，请稍后重试。');
    } finally {
      setBusy(false);
    }
  };
  const openRules = () => {
    setRulesDraft(settings.user_rules);
    setError('');
    setRulesOpen(true);
  };
  const handleSaveRules = async () => {
    setBusy(true);
    setError('');
    try {
      await saveRules(rulesDraft);
      setSettings((current) => ({ ...current, user_rules: rulesDraft }));
      setRulesOpen(false);
    } catch {
      setError('保存用户规则失败，请稍后重试。');
    } finally {
      setBusy(false);
    }
  };
  const openMemory = (memory?: UserMemory) => {
    setMemoryDraft(
      memory
        ? { id: memory.id, category: memory.category, content: memory.content }
        : { category: 'preference', content: '' },
    );
    setError('');
    setMemoryOpen(true);
  };
  const handleSaveMemory = async () => {
    setBusy(true);
    setError('');
    try {
      await saveUserMemory({ category: memoryDraft.category, content: memoryDraft.content }, memoryDraft.id);
      setMemoryOpen(false);
      setMemories((await fetchUserMemories()).memories);
    } catch {
      setError('保存记忆失败，请检查内容后重试。');
    } finally {
      setBusy(false);
    }
  };
  const handleDeleteMemory = async () => {
    if (!memoryToDelete) return;
    const memory = memoryToDelete;
    setBusy(true);
    setError('');
    try {
      await deleteUserMemory(memory.id);
      setMemories((current) => current.filter((item) => item.id !== memory.id));
      setMemoryToDelete(null);
    } catch {
      setError('删除记忆失败，请稍后重试。');
    } finally {
      setBusy(false);
    }
  };
  return {
    settings,
    memories,
    rulesOpen,
    setRulesOpen,
    memoryOpen,
    setMemoryOpen,
    memoryToDelete,
    setMemoryToDelete,
    rulesDraft,
    setRulesDraft,
    memoryDraft,
    setMemoryDraft,
    busy,
    error,
    toggleSetting,
    openRules,
    handleSaveRules,
    openMemory,
    handleSaveMemory,
    handleDeleteMemory,
  };
}
