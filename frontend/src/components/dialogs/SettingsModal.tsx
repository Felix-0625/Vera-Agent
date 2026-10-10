import React, { useEffect, useState } from 'react';
import { Shield, Cpu, Box, Sparkles, BookOpen } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { VeraLogo } from '../common/VeraLogo';
import { SettingsPermissionsTab } from './SettingsPermissionsTab';
import { SettingsMcpTab } from './SettingsMcpTab';
import { SettingsSkillsTab } from './SettingsSkillsTab';
import { SettingsModelsTab } from './SettingsModelsTab';
import { SettingsRulesTab } from './SettingsRulesTab';
import {
  fetchPermissions,
  savePermissions,
  fetchModels,
  patchModel,
  deleteModel,
  fetchMcpServers,
  fetchMcpMarket,
  createMcpServer,
  toggleMcpServer,
  restartMcpServer,
  deleteMcpServer,
  fetchSkills,
  deleteSkill,
} from '../../api/settingsApi';
import { ModelConfig, McpServerConfig, SkillItem, PermissionsConfig } from '../../types/settings';
import { McpMarketList } from '../tools/McpMarketList';

/**
 * 全局系统设置中心弹窗
 * 严格对齐 Penpot 5 大系统设置画板
 */
export const SettingsModal: React.FC = () => {
  const { settingsOpen, closeSettings, settingsTab, openSettings, openModelConfig, openMcpConfig } = useLayoutStore();

  const [permissions, setPermissions] = useState<PermissionsConfig>({ default_mode: 'confirm', whitelist_actions: ['read', 'create', 'edit', 'delete', 'terminal', 'mcp'] });
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServerConfig[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [mcpMarketOpen, setMcpMarketOpen] = useState(false);
  const [mcpMarket, setMcpMarket] = useState<Array<{ id: string; name: string; description: string; category: string }>>([]);

  const loadAll = async () => {
    try {
      const [p, m, mcp, sk] = await Promise.all([
        fetchPermissions(),
        fetchModels(),
        fetchMcpServers(),
        fetchSkills(),
      ]);
      setPermissions(p);
      setModels(m.models || []);
      setMcpServers(mcp.servers || []);
      setSkills(sk.skills || []);
    } catch {
      // 保持静默
    }
  };

  useEffect(() => {
    if (settingsOpen) loadAll();
  }, [settingsOpen, settingsTab]);

  const handleSavePermissions = async (mode: 'confirm' | 'yolo' | 'human', whitelistActions = permissions.whitelist_actions, maxToolAttempts = permissions.max_tool_attempts ?? 3, operationScope = permissions.operation_scope ?? 'project_write_external_readonly') => {
    const updated = { ...permissions, default_mode: mode, whitelist_actions: whitelistActions, max_tool_attempts: maxToolAttempts, operation_scope: operationScope };
    setPermissions(updated);
    await savePermissions(updated);
  };

  const openMcpMarket = async () => {
    setMcpMarketOpen(true);
    try { const result = await fetchMcpMarket(); setMcpMarket(result.market || []); } catch { setMcpMarket([]); }
  };

  const tabs = [
    { key: 'permissions', label: '权限审批', icon: <Shield size={15} /> },
    { key: 'mcp', label: 'MCP', icon: <Cpu size={15} /> },
    { key: 'models', label: '模型', icon: <Box size={15} /> },
    { key: 'skills', label: 'Skill', icon: <Sparkles size={15} /> },
    { key: 'rules', label: '规则与记忆', icon: <BookOpen size={15} /> },
  ];

  return (
    <>
    <Modal isOpen={settingsOpen} onClose={closeSettings} title="" width="96vw" hideHeader>
      <div style={{ display: 'flex', height: 'min(820px, calc(90vh - 40px))', minHeight: 460, gap: 20 }}>
        {/* 左侧导航栏严格对齐 Penpot 布局 */}
        <div
          style={{
            width: 264,
            flex: '0 0 264px',
            borderRight: '1px solid var(--border-subtle)',
            paddingRight: 14,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            {/* 顶部品牌区 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <VeraLogo size={22} />
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
                  VeraAgent
                </div>
                <div style={{ fontSize: 9.5, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.6px' }}>
                  AGENT WORKSPACE
                </div>
              </div>
            </div>

            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, paddingLeft: 6 }}>
              设置
            </div>

            {/* 导航按钮组 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {tabs.map((t) => {
                const isActive = settingsTab === t.key;
                return (
                  <button
                    key={t.key}
                    onClick={() => openSettings(t.key)}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 12.5,
                      fontWeight: isActive ? 600 : 400,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 9,
                      backgroundColor: isActive ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                      color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                      border: isActive ? '1px solid var(--border-default)' : '1px solid transparent',
                      justifyContent: 'flex-start',
                      cursor: 'pointer',
                    }}
                  >
                    {t.icon}
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 底部工作空间说明 */}
          <div style={{ fontSize: 11, color: 'var(--text-disabled)', paddingLeft: 6 }}>
            工作空间设置
          </div>
        </div>

        {/* 右侧 Tab 内容面板 */}
        <div style={{ flex: 1, minWidth: 0, overflowY: 'auto', padding: '0 8px 0 14px' }}>
          {settingsTab === 'permissions' && (
            <SettingsPermissionsTab permissions={permissions} onSave={handleSavePermissions} />
          )}
          {settingsTab === 'mcp' && (
            <SettingsMcpTab
              servers={mcpServers}
              onToggle={async (s) => { await toggleMcpServer(s.id); loadAll(); }}
              onEdit={(s) => openMcpConfig(s)}
              onDelete={async (id) => { await deleteMcpServer(id); loadAll(); }}
              onRestart={async (id) => { await restartMcpServer(id); loadAll(); }}
              onAdd={() => openMcpConfig(null)}
              onOpenMarket={() => void openMcpMarket()}
            />
          )}
          {settingsTab === 'models' && (
            <SettingsModelsTab
              models={models}
              onEdit={(m) => openModelConfig(m)}
              onDelete={async (id) => { await deleteModel(id); loadAll(); }}
              onToggle={async (model) => { await patchModel(model.id, { enabled: model.enabled === false }); await loadAll(); }}
              onAdd={() => openModelConfig(null)}
            />
          )}
          {settingsTab === 'skills' && (
            <SettingsSkillsTab
              skills={skills}
              onDelete={async (name) => { await deleteSkill(name); loadAll(); }}
              onNewSkill={() => { void loadAll(); }}
            />
          )}
          {settingsTab === 'rules' && <SettingsRulesTab />}
        </div>
      </div>
    </Modal>
    <Modal isOpen={mcpMarketOpen} onClose={() => setMcpMarketOpen(false)} title="MCP Marketplace" width={760}>
      <McpMarketList dialog market={mcpMarket} onInstall={async (item) => { await createMcpServer({ id: item.id, name: item.name, type: 'stdio', status: 'stopped', enabled: true, command: 'python', args: ['server.py'], tools: [{ name: item.id, description: item.description }] }); setMcpMarketOpen(false); await loadAll(); }} />
    </Modal>
    </>
  );
};
