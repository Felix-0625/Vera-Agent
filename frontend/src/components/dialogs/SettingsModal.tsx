import { BookOpen, Box, Cpu, Shield, Sparkles } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import {
  deleteMcpServer,
  deleteModel,
  deleteSkill,
  fetchMcpMarket,
  fetchMcpServers,
  fetchModels,
  fetchPermissions,
  fetchSkills,
  installMcpFromMarket,
  McpMarketItem,
  patchModel,
  restartMcpServer,
  savePermissions,
  toggleMcpServer,
} from '../../api/settingsApi';
import { useLayoutStore } from '../../stores/layoutStore';
import { McpServerConfig, ModelConfig, PermissionsConfig, SkillItem } from '../../types/settings';
import { Modal } from '../common/Modal';
import { VeraLogo } from '../common/VeraLogo';
import { McpMarketList } from '../tools/McpMarketList';
import { SettingsMcpTab } from './SettingsMcpTab';
import { SettingsModelsTab } from './SettingsModelsTab';
import { SettingsPermissionsTab } from './SettingsPermissionsTab';
import { SettingsRulesTab } from './SettingsRulesTab';
import { SettingsSkillsTab } from './SettingsSkillsTab';

export const SettingsModal: React.FC = () => {
  const {
    settingsOpen,
    closeSettings,
    settingsTab,
    openSettings,
    openModelConfig,
    openMcpConfig,
    modelCatalogVersion,
    mcpCatalogVersion,
    notifyModelCatalogChanged,
  } = useLayoutStore();

  const [permissions, setPermissions] = useState<PermissionsConfig>({
    default_mode: 'manual',
    approval_actions: ['create', 'edit', 'terminal', 'search', 'mcp', 'delegation'],
    operation_scope: 'project_write_external_readonly',
    max_tool_attempts: 3,
  });
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServerConfig[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [mcpMarketOpen, setMcpMarketOpen] = useState(false);
  const [mcpMarket, setMcpMarket] = useState<McpMarketItem[]>([]);
  const [mcpMarketError, setMcpMarketError] = useState('');
  const [mcpMarketCursor, setMcpMarketCursor] = useState<string | null>(null);
  const [mcpMarketQuery, setMcpMarketQuery] = useState('');
  const [loadingMcpMarket, setLoadingMcpMarket] = useState(false);

  const loadAll = async () => {
    try {
      const [p, m, mcp, sk] = await Promise.all([fetchPermissions(), fetchModels(), fetchMcpServers(), fetchSkills()]);
      setPermissions(p);
      setModels(m.models || []);
      setMcpServers(mcp.servers || []);
      setSkills(sk.skills || []);
    } catch {}
  };

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Settings data must refresh when the dialog, tab, or MCP catalog changes.
    if (settingsOpen) loadAll();
  }, [settingsOpen, settingsTab, mcpCatalogVersion]);

  useEffect(() => {
    if (!settingsOpen) return;
    fetchModels()
      .then((data) => setModels(data.models || []))
      .catch(() => setModels([]));
  }, [settingsOpen, modelCatalogVersion]);

  const handleSavePermissions = async (
    mode: PermissionsConfig['default_mode'],
    approvalActions = permissions.approval_actions,
    operationScope = permissions.operation_scope ?? 'project_write_external_readonly',
    maxToolAttempts = permissions.max_tool_attempts ?? 3,
  ) => {
    const updated = {
      ...permissions,
      default_mode: mode,
      approval_actions: approvalActions,
      operation_scope: operationScope,
      max_tool_attempts: maxToolAttempts,
    };
    setPermissions(updated);
    await savePermissions(updated);
  };

  const openMcpMarket = async () => {
    setMcpMarketOpen(true);
    setMcpMarketError('');
    setMcpMarketQuery('');
    setMcpMarketCursor(null);
    setLoadingMcpMarket(true);
    try {
      const result = await fetchMcpMarket();
      setMcpMarket(result.market || []);
      setMcpMarketCursor(result.next_cursor || null);
    } catch (error) {
      setMcpMarket([]);
      setMcpMarketError(error instanceof Error ? error.message : 'MCP Registry 暂时不可用。');
    } finally {
      setLoadingMcpMarket(false);
    }
  };
  const searchMcpMarket = async (query: string) => {
    setMcpMarketQuery(query);
    setMcpMarketCursor(null);
    setMcpMarketError('');
    setLoadingMcpMarket(true);
    try {
      const result = await fetchMcpMarket(query);
      setMcpMarket(result.market || []);
      setMcpMarketCursor(result.next_cursor || null);
    } catch (error) {
      setMcpMarketError(error instanceof Error ? error.message : 'MCP Registry 暂时不可用。');
    } finally {
      setLoadingMcpMarket(false);
    }
  };
  const loadMoreMcpMarket = async () => {
    if (!mcpMarketCursor) return;
    setMcpMarketError('');
    setLoadingMcpMarket(true);
    try {
      const result = await fetchMcpMarket(mcpMarketQuery, mcpMarketCursor);
      setMcpMarket((current) => [...current, ...(result.market || [])]);
      setMcpMarketCursor(result.next_cursor || null);
    } catch (error) {
      setMcpMarketError(error instanceof Error ? error.message : 'MCP Registry 暂时不可用。');
    } finally {
      setLoadingMcpMarket(false);
    }
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
        <div className="settings-layout">
          {}
          <div className="settings-sidebar">
            <div>
              {}
              <div className="settings-sidebar-brand">
                <VeraLogo size={22} />
                <div>
                  <div className="settings-sidebar-brand-name">VeraAgent</div>
                  <div className="settings-sidebar-brand-caption">AGENT WORKSPACE</div>
                </div>
              </div>

              <div className="settings-sidebar-label">设置</div>

              {}
              <div className="settings-nav">
                {tabs.map((t) => {
                  const isActive = settingsTab === t.key;
                  return (
                    <button
                      key={t.key}
                      onClick={() => openSettings(t.key)}
                      className={`settings-nav-button${isActive ? ' is-active' : ''}`}
                    >
                      {t.icon}
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {}
            <div className="settings-sidebar-footer">工作空间设置</div>
          </div>

          {}
          <div className="settings-content">
            {settingsTab === 'permissions' && (
              <SettingsPermissionsTab permissions={permissions} onSave={handleSavePermissions} />
            )}
            {settingsTab === 'mcp' && (
              <SettingsMcpTab
                servers={mcpServers}
                onToggle={async (s) => {
                  await toggleMcpServer(s.id);
                  loadAll();
                }}
                onEdit={(s) => openMcpConfig(s)}
                onDelete={async (id) => {
                  await deleteMcpServer(id);
                  loadAll();
                }}
                onRestart={async (id) => {
                  await restartMcpServer(id);
                  loadAll();
                }}
                onAdd={() => openMcpConfig(null)}
                onOpenMarket={() => void openMcpMarket()}
              />
            )}
            {settingsTab === 'models' && (
              <SettingsModelsTab
                models={models}
                onEdit={(m) => openModelConfig(m)}
                onDelete={async (id) => {
                  await deleteModel(id);
                  notifyModelCatalogChanged();
                  await loadAll();
                }}
                onToggle={async (model) => {
                  await patchModel(model.id, { enabled: model.enabled === false });
                  notifyModelCatalogChanged();
                  await loadAll();
                }}
                onAdd={() => openModelConfig(null)}
              />
            )}
            {settingsTab === 'skills' && (
              <SettingsSkillsTab
                skills={skills}
                onDelete={async (name) => {
                  await deleteSkill(name);
                  loadAll();
                }}
                onNewSkill={() => {
                  void loadAll();
                }}
              />
            )}
            {settingsTab === 'rules' && <SettingsRulesTab />}
          </div>
        </div>
      </Modal>
      <Modal isOpen={mcpMarketOpen} onClose={() => setMcpMarketOpen(false)} title="MCP Marketplace" width={760}>
        <McpMarketList
          dialog
          market={mcpMarket}
          error={mcpMarketError}
          loading={loadingMcpMarket}
          hasMore={!!mcpMarketCursor}
          onLoadMore={loadMoreMcpMarket}
          installedIds={mcpServers.map((server) => server.registry_id || '')}
          onSearch={searchMcpMarket}
          onInstall={async (item) => {
            await installMcpFromMarket(item);
            setMcpMarketOpen(false);
            await loadAll();
          }}
        />
      </Modal>
    </>
  );
};
