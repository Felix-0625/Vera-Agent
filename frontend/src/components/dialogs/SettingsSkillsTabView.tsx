import { Check, Grid, Plus, Sparkles, Trash2 } from 'lucide-react';
import { Button } from '../common/Button';
import { SearchField, TextArea, TextInput } from '../common/Field';
import { Modal } from '../common/Modal';
import { PageHeading } from '../common/PageHeading';
import { useSettingsSkillsTab } from './useSettingsSkillsTab';
export function SettingsSkillsTabView({
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
}: ReturnType<typeof useSettingsSkillsTab>) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4-5)' }}>
      <PageHeading title="Skill" description="管理 Agent 可调用的技能。" />

      {}
      <div
        className="settings-skills-toolbar"
        style={{ display: 'flex', gap: 'var(--space-2-5)', alignItems: 'center' }}
      >
        <SearchField
          wrapperClassName="settings-skill-search"
          aria-label="搜索 Skills"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="搜索 Skills…"
        />

        <Button
          onClick={() => {
            void openMarket();
          }}
          variant="secondary"
          size="sm"
        >
          <Grid size={13} />
          <span>浏览技能市场</span>
        </Button>

        <Button
          onClick={() => {
            setError('');
            setDialog('create');
          }}
          variant="primary"
          size="sm"
        >
          <Plus size={13} />
          <span>新建</span>
        </Button>
      </div>

      {}
      {filtered.length === 0 ? (
        <div
          className="glass-card"
          style={{
            padding: '40px var(--space-5)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
            暂无 Skill
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
            创建 Skill 或从技能市场添加。
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {filtered.map((s) => (
            <div
              key={s.name}
              className="glass-card"
              style={{
                padding: 'var(--space-2-5) var(--space-3-5)',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                <Sparkles size={15} color="var(--accent-primary)" />
                <div>
                  <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{s.name}</div>
                  <div style={{ fontSize: 'var(--font-size-label)', color: 'var(--text-muted)' }}>{s.description}</div>
                </div>
              </div>

              <button
                onClick={() => onDelete(s.name)}
                style={{ padding: 'var(--space-1)', color: 'var(--accent-rose)' }}
                title="删除 Skill"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
      <Modal isOpen={dialog === 'market'} onClose={() => setDialog(null)} title="技能市场" width={760}>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2-5)',
            maxHeight: 'calc(90vh - 110px)',
            overflowY: 'auto',
            padding: 'var(--space-0-5)',
          }}
        >
          <aside
            role="note"
            style={{
              padding: 'var(--space-2-5) var(--space-3)',
              borderRadius: 'var(--radius-md-plus)',
              border: '1px solid var(--border-warning-soft)',
              background: 'var(--bg-warning-soft)',
              color: 'var(--text-secondary)',
              fontSize: 'var(--font-size-label)',
              lineHeight: 1.55,
            }}
          >
            <strong style={{ color: 'var(--accent-amber)' }}>安全提示：</strong>
            来源标签只说明仓库归属，不代表仓库或其中每个 Skill 已通过安全审计。Skill 指令会影响 Agent
            行为，包内也可能带有脚本和外部资源。添加前请检查源仓库、具体内容、脚本和许可证；不要向不可信 Skill
            提供密钥或敏感数据。
          </aside>
          <SearchField
            wrapperClassName="settings-market-search"
            aria-label="搜索技能市场"
            value={marketSearch}
            onChange={(event) => setMarketSearch(event.target.value)}
            placeholder="搜索名称、用途或来源（支持中文）…"
            rightAdornment={
              <span className="settings-market-search__count">
                {marketSearch
                  ? market.filter((skill) =>
                      `${skill.name} ${skill.description} ${skill.category} ${skill.source}`
                        .toLocaleLowerCase()
                        .includes(marketSearch.trim().toLocaleLowerCase()),
                    ).length
                  : market.length}{' '}
                个技能
              </span>
            }
          />
          {error && (
            <div
              role="alert"
              style={{
                color: 'var(--accent-rose)',
                fontSize: 'var(--font-size-sm)',
                padding: 'var(--space-2) var(--space-2-5)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-danger-soft)',
              }}
            >
              {error}
            </div>
          )}
          {market
            .filter((skill) =>
              `${skill.name} ${skill.description} ${skill.category} ${skill.source}`
                .toLocaleLowerCase()
                .includes(marketSearch.trim().toLocaleLowerCase()),
            )
            .map((skill) => {
              const installed = skills.some((item) => item.name.toLowerCase() === skill.name.toLowerCase());
              return (
                <article
                  key={skill.market_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(0,1fr) auto',
                    alignItems: 'center',
                    gap: 'var(--space-5)',
                    padding: 'var(--space-3-75) var(--space-4)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-lg-plus)',
                    background: 'var(--bg-card)',
                    transition: 'border-color .16s ease, background .16s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', minWidth: 0 }}>
                    <span
                      aria-hidden="true"
                      style={{
                        flex: '0 0 34px',
                        width: 34,
                        height: 34,
                        display: 'grid',
                        placeItems: 'center',
                        borderRadius: 'var(--radius-md-wide)',
                        color: 'var(--accent-skill)',
                        background: 'var(--bg-skill-soft)',
                        border: '1px solid color-mix(in srgb, var(--accent-skill) 22%, var(--border-subtle))',
                      }}
                    >
                      <Sparkles size={16} />
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 'var(--font-size-subheading)',
                          fontWeight: 650,
                          color: 'var(--text-primary)',
                          lineHeight: 1.4,
                          overflowWrap: 'anywhere',
                        }}
                      >
                        {skill.name}
                      </div>
                      <span
                        style={{
                          display: 'inline-flex',
                          marginTop: 'var(--space-1-25)',
                          padding: 'var(--space-0-5) var(--space-1-75)',
                          borderRadius: 'var(--radius-full)',
                          color: 'var(--accent-skill)',
                          background: 'var(--bg-skill-soft)',
                          fontSize: 'var(--font-size-subtle)',
                          lineHeight: 1.5,
                        }}
                      >
                        {skill.category}
                      </span>
                      <div
                        style={{
                          fontSize: 'var(--font-size-label)',
                          lineHeight: 1.55,
                          color: 'var(--text-muted)',
                          marginTop: 'var(--space-1-5)',
                          overflowWrap: 'anywhere',
                        }}
                      >
                        {skill.description}
                      </div>
                      <a
                        href={skill.source}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'inline-block',
                          marginTop: 'var(--space-1-5)',
                          color: 'var(--accent-primary)',
                          fontSize: 'var(--font-size-subtle)',
                        }}
                      >
                        {skill.category} · {skill.commit.slice(0, 8)}
                      </a>
                    </div>
                  </div>
                  <button
                    disabled={busy || installed}
                    onClick={() => void installMarketSkill(skill)}
                    style={{
                      display: 'inline-flex',
                      flex: '0 0 78px',
                      width: 78,
                      minWidth: 78,
                      height: 34,
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 'var(--space-1-25)',
                      whiteSpace: 'nowrap',
                      padding: '0 var(--space-3)',
                      borderRadius: 'var(--radius-md-plus)',
                      background: installed ? 'var(--bg-card-hover)' : 'var(--accent-gradient)',
                      color: installed ? 'var(--text-muted)' : 'var(--text-on-accent)',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 600,
                      boxShadow: installed ? 'none' : 'var(--shadow-sm)',
                      cursor: installed ? 'default' : 'pointer',
                    }}
                  >
                    {installed ? (
                      <>
                        <Check size={13} />
                        已添加
                      </>
                    ) : (
                      '添加'
                    )}
                  </button>
                </article>
              );
            })}
          {market.length > 0 &&
            !market.some((skill) =>
              `${skill.name} ${skill.description} ${skill.category} ${skill.source}`
                .toLocaleLowerCase()
                .includes(marketSearch.trim().toLocaleLowerCase()),
            ) && (
              <div
                style={{
                  padding: 36,
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: 'var(--font-size-sm)',
                  border: '1px dashed var(--border-default)',
                  borderRadius: 'var(--radius-lg)',
                }}
              >
                没有匹配的技能，请尝试其他关键词。
              </div>
            )}
          {!market.length && !error && (
            <div
              aria-live="polite"
              style={{
                padding: 36,
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-sm)',
                border: '1px dashed var(--border-default)',
                borderRadius: 'var(--radius-lg)',
              }}
            >
              {loadingMarket ? '正在获取上游技能目录…' : '技能市场暂无可用项目。'}
            </div>
          )}
        </div>
      </Modal>
      <Modal isOpen={dialog === 'create'} onClose={() => setDialog(null)} title="新建 Skill" width={680}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {error && (
            <div role="alert" style={{ color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)' }}>
              {error}
            </div>
          )}
          <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            名称
            <TextInput
              value={skillName}
              onChange={(e) => setSkillName(e.target.value)}
              placeholder="例如: project-guidelines"
              style={{ display: 'block', marginTop: 'var(--space-1-25)' }}
            />
          </label>
          <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            简介
            <TextInput
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述这个 Skill 的用途"
              style={{ display: 'block', marginTop: 'var(--space-1-25)' }}
            />
          </label>
          <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            SKILL.md 内容
            <TextArea
              className="ui-field--code"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={12}
              spellCheck={false}
              style={{ display: 'block', marginTop: 'var(--space-1-25)' }}
            />
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button onClick={() => setDialog(null)} variant="ghost" size="sm">
              取消
            </Button>
            <Button disabled={busy} onClick={() => void createSkill()} variant="primary" size="sm">
              {busy ? '保存中…' : '创建 Skill'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
