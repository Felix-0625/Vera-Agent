import { Brain, FileText, Pencil, Plus, Trash2, UserRound } from 'lucide-react';
import { UserMemory } from '../../api/settingsApi';
import { Button } from '../common/Button';
import { SelectField, TextArea } from '../common/Field';
import { IconButton } from '../common/IconButton';
import { Modal } from '../common/Modal';
import { PageHeading } from '../common/PageHeading';
import { Switch } from '../common/Switch';
import { cardStyle, categories } from './SettingsRulesTabParts';
import { useSettingsRulesTab } from './useSettingsRulesTab';
export function SettingsRulesTabView({
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
}: ReturnType<typeof useSettingsRulesTab>) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4-5)' }}>
      <PageHeading
        title="规则与记忆"
        description="系统约束由 VeraAgent 管理；你可以设置个人规则、项目指令和可查看的用户记忆。"
      />

      {error && (
        <div role="alert" style={{ fontSize: 'var(--font-size-sm)', color: 'var(--accent-rose)' }}>
          {error}
        </div>
      )}

      <section
        className="glass-card"
        style={{ ...cardStyle, display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)' }}
      >
        <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
          项目指令
        </div>
        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4-5)' }}
        >
          <div>
            <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 500, color: 'var(--text-primary)' }}>
              读取当前项目的 AGENTS.md
            </div>
            <div
              style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-0-75)' }}
            >
              按当前项目工作目录加载 AGENTS.md；Git 项目只在仓库范围内查找。只读，不会被此界面覆盖。
            </div>
          </div>
          <Switch
            label="读取当前项目的 AGENTS.md"
            checked={settings.include_agents_md}
            disabled={busy}
            onChange={(checked) => void toggleSetting('include_agents_md', checked)}
          />
        </div>
      </section>

      <section className="glass-card" style={cardStyle}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-3)',
          }}
        >
          <div>
            <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
              用户规则
            </div>
            <div
              style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-0-75)' }}
            >
              适用于所有项目，独立保存；与项目指令冲突时优先遵守用户规则。
            </div>
          </div>
          <Button onClick={openRules} variant="primary" size="sm" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
            {settings.user_rules ? <Pencil size={13} /> : <Plus size={13} />}
            {settings.user_rules ? '编辑' : '创建'}
          </Button>
        </div>
        {settings.user_rules ? (
          <button
            onClick={openRules}
            style={{
              width: '100%',
              padding: 'var(--space-3) var(--space-3-5)',
              textAlign: 'left',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md-plus)',
              color: 'var(--text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2-5)',
            }}
          >
            <FileText size={15} color="var(--accent-primary)" />
            <span style={{ fontSize: 'var(--font-size-sm)', whiteSpace: 'pre-wrap' }}>
              {settings.user_rules.slice(0, 180)}
              {settings.user_rules.length > 180 ? '…' : ''}
            </span>
          </button>
        ) : (
          <div
            style={{
              padding: 'var(--space-4) var(--space-3)',
              textAlign: 'center',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--text-muted)',
            }}
          >
            还没有个人规则，例如回答风格、沟通语言或通用协作偏好。
          </div>
        )}
      </section>

      <section className="glass-card" style={cardStyle}>
        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4-5)' }}
        >
          <div>
            <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
              用户记忆
            </div>
            <div
              style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-0-75)' }}
            >
              Agent
              可沉淀你明确表达或确认的背景、偏好、习惯和反馈。记忆保存在本机，可随时编辑或删除；不包含项目规则或临时任务状态。
            </div>
          </div>
          <Switch
            label="启用用户记忆"
            checked={settings.memory_enabled}
            disabled={busy}
            onChange={(checked) => void toggleSetting('memory_enabled', checked)}
          />
        </div>
        <div
          style={{
            borderTop: '1px solid var(--border-subtle)',
            marginTop: 'var(--space-3-5)',
            paddingTop: 'var(--space-3)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 'var(--space-2)',
            }}
          >
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              已整理的记忆 · {memories.length}
            </div>
            <Button onClick={() => openMemory()} variant="ghost" size="sm">
              <Plus size={13} />
              添加
            </Button>
          </div>
          {!memories.length ? (
            <div
              style={{
                padding: 'var(--space-4-5) var(--space-2-5)',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <Brain size={18} style={{ display: 'block', margin: '0 auto var(--space-1-5)' }} />
              暂无用户记忆。对话中出现稳定偏好或明确要求记住的信息时，Agent 可以自动整理。
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-2-5) var(--space-0-5)',
                    borderTop: '1px solid var(--border-subtle)',
                  }}
                >
                  <UserRound size={15} color="var(--accent-primary)" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 'var(--font-size-compact)',
                        color: 'var(--text-muted)',
                        marginBottom: 'var(--space-0-5)',
                      }}
                    >
                      {categories.find((item) => item.value === memory.category)?.label || memory.category}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                      {memory.content}
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--text-muted)',
                        marginTop: 'var(--space-0-75)',
                      }}
                    >
                      {memory.source === 'agent' || (!memory.source && memory.source_thread_id)
                        ? 'Agent 整理'
                        : '手动维护'}{' '}
                      · 更新于 {new Date(memory.updated_at * 1000).toLocaleString()}
                    </div>
                  </div>
                  <IconButton label="编辑记忆" onClick={() => openMemory(memory)} size="sm">
                    <Pencil size={13} />
                  </IconButton>
                  <IconButton label="删除记忆" tone="danger" onClick={() => setMemoryToDelete(memory)} size="sm">
                    <Trash2 size={13} />
                  </IconButton>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <Modal isOpen={rulesOpen} onClose={() => setRulesOpen(false)} title="编辑用户规则" width={760}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
            独立保存在 VeraAgent 用户设置中，不会修改项目的 AGENTS.md。用户规则优先于项目说明。
          </div>
          <TextArea
            autoFocus
            className="ui-field--code"
            value={rulesDraft}
            onChange={(event) => setRulesDraft(event.target.value)}
            maxLength={50000}
            spellCheck={false}
            placeholder={'例如：\n- 默认使用中文回答。\n- 先概述影响，再解释实现细节。'}
            rows={16}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button onClick={() => setRulesOpen(false)} variant="ghost" size="sm">
              取消
            </Button>
            <Button disabled={busy} onClick={() => void handleSaveRules()} variant="primary" size="sm">
              {busy ? '保存中…' : '保存规则'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={memoryOpen}
        onClose={() => setMemoryOpen(false)}
        title={memoryDraft.id ? '编辑用户记忆' : '添加用户记忆'}
        width={620}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <label
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-1-5)',
              color: 'var(--text-secondary)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            类型
            <SelectField
              value={memoryDraft.category}
              onChange={(event) =>
                setMemoryDraft((current) => ({ ...current, category: event.target.value as UserMemory['category'] }))
              }
            >
              {categories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </SelectField>
          </label>
          <label
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-1-5)',
              color: 'var(--text-secondary)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            内容
            <TextArea
              autoFocus
              value={memoryDraft.content}
              maxLength={500}
              onChange={(event) => setMemoryDraft((current) => ({ ...current, content: event.target.value }))}
              rows={4}
              placeholder="记录可帮助 Agent 在未来对话中更好地理解你的稳定信息。"
            />
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button onClick={() => setMemoryOpen(false)} variant="ghost" size="sm">
              取消
            </Button>
            <Button
              disabled={busy || !memoryDraft.content.trim()}
              onClick={() => void handleSaveMemory()}
              variant="primary"
              size="sm"
            >
              {busy ? '保存中…' : '保存记忆'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={memoryToDelete !== null}
        onClose={() => setMemoryToDelete(null)}
        title="确认删除用户记忆"
        width={480}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            删除后，Agent 将不再使用这条记忆。
          </div>
          {memoryToDelete && (
            <div
              style={{
                padding: 'var(--space-3)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-sm)',
                whiteSpace: 'pre-wrap',
              }}
            >
              {memoryToDelete.content}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button disabled={busy} onClick={() => setMemoryToDelete(null)} variant="ghost" size="sm">
              取消
            </Button>
            <Button disabled={busy} onClick={() => void handleDeleteMemory()} variant="danger" size="sm">
              {busy ? '删除中…' : '确认删除'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
