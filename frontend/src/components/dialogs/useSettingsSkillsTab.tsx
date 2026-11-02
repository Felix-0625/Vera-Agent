import { useState } from 'react';
import { fetchSkillsMarket, installSkill, SkillMarketItem } from '../../api/settingsApi';
import { SettingsSkillsTabProps } from './SettingsSkillsTabParts';
export function useSettingsSkillsTab({ skills, onDelete, onNewSkill }: SettingsSkillsTabProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [dialog, setDialog] = useState<'market' | 'create' | null>(null);
  const [market, setMarket] = useState<SkillMarketItem[]>([]);
  const [marketSearch, setMarketSearch] = useState('');
  const [loadingMarket, setLoadingMarket] = useState(false);
  const [skillName, setSkillName] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('# Skill 指南\n\n');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const openMarket = async () => {
    setDialog('market');
    setError('');
    setMarketSearch('');
    setLoadingMarket(true);
    try {
      const res = await fetchSkillsMarket();
      setMarket(res.market || []);
    } catch {
      setError('技能市场加载失败，请检查服务连接。');
    } finally {
      setLoadingMarket(false);
    }
  };
  const createSkill = async () => {
    const name = skillName.trim();
    if (!name) {
      setError('请输入 Skill 名称。');
      return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      setError('名称仅支持英文字母、数字、连字符和下划线。');
      return;
    }
    if (skills.some((skill) => skill.name.toLowerCase() === name.toLowerCase())) {
      setError('同名 Skill 已存在，请使用其他名称。');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await installSkill({ name, description: description.trim() || name, instructions });
      setDialog(null);
      setSkillName('');
      setDescription('');
      setInstructions('# Skill 指南\n\n');
      await onNewSkill?.();
    } catch {
      setError('保存失败，请检查名称或服务连接。');
    } finally {
      setBusy(false);
    }
  };
  const installMarketSkill = async (skill: SkillMarketItem) => {
    setBusy(true);
    setError('');
    try {
      await installSkill(skill);
      await onNewSkill?.();
      setMarket((current) => current.filter((item) => item.market_id !== skill.market_id));
    } catch {
      setError(`安装 ${skill.name} 失败，请检查服务连接。`);
    } finally {
      setBusy(false);
    }
  };
  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase()),
  );
  return {
    skills,
    onDelete,
    searchTerm,
    setSearchTerm,
    dialog,
    setDialog,
    market,
    marketSearch,
    setMarketSearch,
    loadingMarket,
    skillName,
    setSkillName,
    description,
    setDescription,
    instructions,
    setInstructions,
    busy,
    error,
    setError,
    openMarket,
    createSkill,
    installMarketSkill,
    filtered,
  };
}
