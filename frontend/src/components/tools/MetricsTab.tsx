import { Activity, BarChart3, ChartNoAxesColumnIncreasing, Coins, RefreshCw, Sparkles } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchAnalyticsDashboard } from '../../api/toolApi';
import { useChatStore } from '../../stores/chatStore';
import { AnalyticsDashboard } from '../../types/tool';
import { SelectField } from '../common/Field';

type Period = 'day' | 'week' | 'month';
const USD_TO_CNY = 7.2;
const MODEL_COLORS = [
  'var(--accent-primary)',
  'var(--accent-emerald)',
  'var(--accent-cyan)',
  'var(--accent-amber)',
  'var(--accent-rose)',
  'var(--text-muted)',
];
const money = (usd: number) => `¥${(usd * USD_TO_CNY).toFixed(2)}`;

const UsageList: React.FC<{ title: string; kind: 'mcp' | 'skill'; rows: Array<{ name: string; count: number }> }> = ({
  title,
  kind,
  rows,
}) => {
  const Icon = kind === 'mcp' ? Activity : Sparkles;
  const max = Math.max(1, ...rows.map((row) => row.count));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <section className="metrics-card metrics-usage-card">
      <header className="metrics-card-title">
        <span className={`metrics-title-icon ${kind}`}>
          <Icon size={15} />
        </span>
        <h3>{title}</h3>
        <span className="metrics-total">{total.toLocaleString()} 次</span>
      </header>
      {rows.length ? (
        <div className="metrics-usage-list">
          {rows.map((row, index) => {
            const label =
              kind === 'mcp'
                ? ({ web_search: '网页搜索', fetch_web_page: '网页读取' } as Record<string, string>)[row.name] ||
                  row.name
                : row.name;
            return (
              <div className="metrics-usage-row" key={row.name}>
                <div className="metrics-usage-label">
                  <span
                    className="metrics-usage-dot"
                    style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }}
                  />
                  <span title={row.name}>{kind === 'mcp' ? `mcp/${label}` : `skill/${label}`}</span>
                  <strong>— {row.count.toLocaleString()} 次</strong>
                </div>
                <div className="metrics-usage-track">
                  <span
                    style={{
                      width: `${Math.max(4, (row.count / max) * 100)}%`,
                      background: MODEL_COLORS[index % MODEL_COLORS.length],
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="metrics-empty-small">暂无调用记录</div>
      )}
    </section>
  );
};

export const MetricsTab: React.FC<{ projectId?: string | null }> = ({ projectId: projectIdOverride }) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId =
    projectIdOverride !== undefined
      ? projectIdOverride || undefined
      : activeThreadId
        ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || undefined
        : draftProjectId || undefined;
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState<Period>('day');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [hovered, setHovered] = useState<number | null>(null);
  const chartFrameRef = useRef<HTMLDivElement>(null);
  const [chartFrameWidth, setChartFrameWidth] = useState(620);

  const loadData = useCallback(async () => {
    if (!projectId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      setData(await fetchAnalyticsDashboard(projectId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '数据加载失败');
    } finally {
      setLoading(false);
    }
  }, [projectId]);
  // This effect starts the project-scoped request; loadData owns the request lifecycle and loading state.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Start the asynchronous project request on a scope change.
    void loadData();
  }, [loadData]);
  useEffect(() => {
    const element = chartFrameRef.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setChartFrameWidth(Math.max(180, element.clientWidth - 35)));
    observer.observe(element);
    setChartFrameWidth(Math.max(180, element.clientWidth - 35));
    return () => observer.disconnect();
  }, [data, period, selectedMonth]);

  const months = data?.retained_months || [];
  const activeMonthKey = months.includes(selectedMonth) ? selectedMonth : months.at(-1) || '';
  const activeMonth = data?.monthly_models.find((item) => item.month === activeMonthKey);
  const chart = useMemo(() => {
    if (period === 'month')
      return (activeMonth?.models || [])
        .filter((item) => item.tokens > 0 || item.cost_usd > 0)
        .map((item) => ({ name: item.name, tokens: item.tokens, cost_usd: item.cost_usd }));
    if (period === 'day')
      return (data?.daily_trends || [])
        .filter((item) => item.month === activeMonthKey)
        .map((item) => ({ name: item.date, tokens: item.tokens, cost_usd: item.cost_usd }));
    return (data?.weekly_trends || [])
      .filter((item) => item.month === activeMonthKey)
      .map((item) => ({ name: item.label, tokens: item.tokens, cost_usd: item.cost_usd }));
  }, [activeMonth, activeMonthKey, data, period]);
  const maxTokens = Math.max(1, ...chart.map((item) => item.tokens));
  const rawStep = maxTokens / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const normalizedStep = rawStep / magnitude;
  const tickStep = (normalizedStep <= 1 ? 1 : normalizedStep <= 2 ? 2 : normalizedStep <= 5 ? 5 : 10) * magnitude;
  const axisMax = Math.max(tickStep, Math.ceil(maxTokens / tickStep) * tickStep);
  const ticks = Array.from({ length: 5 }, (_, index) => axisMax - tickStep * index);
  const chartWidth = period === 'month' ? Math.max(460, chart.length * 84) : chartFrameWidth;
  const points = chart.map((item, index) => ({
    x: chart.length < 2 ? chartWidth / 2 : 12 + index * ((chartWidth - 24) / (chart.length - 1)),
    y: 156 - (item.tokens / axisMax) * 126,
  }));
  const linePath = points
    .map((point, index) => {
      if (index === 0) return `M ${point.x} ${point.y}`;
      const previous = points[index - 1];
      const dx = (point.x - previous.x) / 3;
      return `C ${previous.x + dx} ${previous.y}, ${point.x - dx} ${point.y}, ${point.x} ${point.y}`;
    })
    .join(' ');
  const areaPath = points.length ? `${linePath} L ${points.at(-1)!.x} 156 L ${points[0].x} 156 Z` : '';
  const mcpCalls = (data?.mcp_usage || []).reduce((sum, row) => sum + row.count, 0);
  const skillCalls = (data?.skill_usage || []).reduce((sum, row) => sum + row.count, 0);

  return (
    <div className="metrics-page">
      <div className="metrics-header">
        <div className="metrics-heading">
          <span>
            <BarChart3 size={16} />
          </span>
          <strong>数据看板</strong>
        </div>
        <button
          className="metrics-refresh"
          onClick={() => void loadData()}
          title="刷新数据"
          aria-label="刷新数据"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'pulse-glow' : ''} />
        </button>
      </div>
      {!projectId ? (
        <div className="metrics-empty">
          <Coins size={25} />
          <span>选择一个项目查看项目用量</span>
        </div>
      ) : error ? (
        <div className="metrics-empty metrics-error">{error}</div>
      ) : (
        <>
          <div className="metrics-summary">
            <div className="metrics-summary-card">
              <span>项目 Token 消耗量</span>
              <strong>{(data?.summary.total_tokens || 0).toLocaleString()}</strong>
            </div>
            <div className="metrics-summary-card">
              <span>项目预估费用</span>
              <strong title="按各模型记录费用汇总并换算人民币">{money(data?.summary.total_cost_usd || 0)}</strong>
            </div>
            <div className="metrics-summary-card">
              <span>MCP 调用次数</span>
              <strong>{mcpCalls.toLocaleString()}</strong>
            </div>
            <div className="metrics-summary-card">
              <span>Skill 调用次数</span>
              <strong>{skillCalls.toLocaleString()}</strong>
            </div>
          </div>

          <section className="metrics-card metrics-chart-card">
            <header className="metrics-card-title metrics-chart-title">
              <div>
                <span className="metrics-title-icon chart">
                  <ChartNoAxesColumnIncreasing size={15} />
                </span>
                <h3>Token 消耗</h3>
              </div>
              <div className="metrics-periods">
                {(['day', 'week', 'month'] as Period[]).map((value) => (
                  <button
                    key={value}
                    className={period === value ? 'active' : ''}
                    onClick={() => {
                      setPeriod(value);
                      setHovered(null);
                    }}
                  >
                    {value === 'day' ? '每日' : value === 'week' ? '每周' : '按月'}
                  </button>
                ))}
              </div>
            </header>
            <div className="metrics-month-select">
              <SelectField
                aria-label="选择统计月份"
                value={activeMonthKey}
                onChange={(event) => {
                  setSelectedMonth(event.target.value);
                  setHovered(null);
                }}
              >
                {months.map((month) => (
                  <option key={month} value={month}>
                    {month}
                  </option>
                ))}
              </SelectField>
            </div>
            {!chart.length ? (
              <div className="metrics-chart-empty">暂无 Token 用量记录</div>
            ) : period === 'month' ? (
              <div className="metrics-model-chart" ref={chartFrameRef}>
                <div className="metrics-model-bars" style={{ width: chartWidth, minWidth: '100%' }}>
                  {chart.map((item, index) => (
                    <div
                      className="metrics-model-column"
                      key={item.name}
                      onMouseEnter={() => setHovered(index)}
                      onMouseLeave={() => setHovered(null)}
                    >
                      {hovered === index && (
                        <div className="metrics-tooltip metrics-model-tooltip">
                          <b>{item.name}</b>
                          <span>{item.tokens.toLocaleString()} Tokens</span>
                          <span>{money(item.cost_usd)}</span>
                        </div>
                      )}
                      <div
                        className="metrics-model-bar"
                        style={{
                          height: `${Math.max(5, (item.tokens / maxTokens) * 100)}%`,
                          background: MODEL_COLORS[index % MODEL_COLORS.length],
                        }}
                      />
                      <span className="metrics-model-name" title={item.name}>
                        {item.name}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="metrics-month-details">
                  {chart.map((item, index) => (
                    <div className="metrics-month-detail" key={item.name}>
                      <span
                        className="metrics-usage-dot"
                        style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }}
                      />
                      <span className="metrics-month-model" title={item.name}>
                        {item.name}
                      </span>
                      <span>{item.tokens.toLocaleString()} Token</span>
                      <strong>{money(item.cost_usd)}</strong>
                    </div>
                  ))}
                </div>
                <div className="metrics-chart-caption">
                  <span>Token 与人民币费用</span>
                  <span>{activeMonthKey}</span>
                </div>
              </div>
            ) : (
              <div className="metrics-line-chart" ref={chartFrameRef}>
                <div className="metrics-chart-scroll">
                  <div className="metrics-chart-axis">
                    {ticks.map((tick) => (
                      <span key={tick}>{tick.toLocaleString()}</span>
                    ))}
                  </div>
                  <svg
                    viewBox={`0 0 ${chartWidth} 178`}
                    style={{ width: chartWidth }}
                    role="img"
                    aria-label={period === 'day' ? '每日 Token 折线图' : '每周 Token 柱形图'}
                  >
                    <defs>
                      <linearGradient id="metrics-area-gradient" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent-primary)" />
                        <stop offset="100%" stopColor="var(--accent-primary)" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    {[30, 61.5, 93, 124.5, 156].map((y) => (
                      <line key={y} x1="20" y1={y} x2={chartWidth - 20} y2={y} className="metrics-grid-line" />
                    ))}
                    {period === 'day' ? (
                      <>
                        <path d={areaPath} className="metrics-area" />
                        <path d={linePath} className="metrics-line" />
                        {points.map((point, index) => (
                          <g
                            key={index}
                            onMouseEnter={() => setHovered(index)}
                            onMouseLeave={() => setHovered(null)}
                            className="metrics-point-hit"
                          >
                            <circle cx={point.x} cy={point.y} r="10" fill="transparent" />
                            {hovered === index && (
                              <>
                                <circle cx={point.x} cy={point.y} r="6" className="metrics-point-active" />
                                <foreignObject
                                  x={Math.min(chartWidth - 136, Math.max(4, point.x - 64))}
                                  y={Math.max(2, point.y - 66)}
                                  width="132"
                                  height="58"
                                >
                                  <div className="metrics-tooltip">
                                    <b>{chart[index].name}</b>
                                    <span>{chart[index].tokens.toLocaleString()} Tokens</span>
                                    <span>{money(chart[index].cost_usd)}</span>
                                  </div>
                                </foreignObject>
                              </>
                            )}
                            <circle cx={point.x} cy={point.y} r="3.3" className="metrics-point" />
                          </g>
                        ))}
                      </>
                    ) : (
                      chart.map((item, index) => (
                        <g
                          key={item.name}
                          onMouseEnter={() => setHovered(index)}
                          onMouseLeave={() => setHovered(null)}
                          className="metrics-point-hit"
                        >
                          <rect
                            x={points[index].x - Math.min(12, chartWidth / chart.length / 3)}
                            y={points[index].y}
                            width={Math.min(24, (chartWidth / chart.length) * 0.62)}
                            height={156 - points[index].y}
                            rx="3"
                            className={`metrics-week-bar ${hovered === index ? 'hovered' : ''}`}
                          />
                          {hovered === index && (
                            <foreignObject
                              x={Math.min(chartWidth - 136, Math.max(4, points[index].x - 64))}
                              y={Math.max(2, points[index].y - 66)}
                              width="132"
                              height="58"
                            >
                              <div className="metrics-tooltip">
                                <b>{item.name}</b>
                                <span>{item.tokens.toLocaleString()} Tokens</span>
                                <span>{money(item.cost_usd)}</span>
                              </div>
                            </foreignObject>
                          )}
                        </g>
                      ))
                    )}
                  </svg>
                </div>
                <div className="metrics-x-labels" style={{ width: chartWidth, minWidth: '100%' }}>
                  {(() => {
                    const tickCount = Math.min(period === 'day' ? 6 : 5, chart.length);
                    const tickIndices = new Set(
                      Array.from({ length: tickCount }, (_, index) =>
                        tickCount <= 1 ? 0 : Math.round((index * (chart.length - 1)) / (tickCount - 1)),
                      ),
                    );
                    return chart.map((item, index) =>
                      tickIndices.has(index) ? (
                        <span
                          key={item.name}
                          style={{ left: `${chart.length <= 1 ? 50 : (index / (chart.length - 1)) * 100}%` }}
                        >
                          {period === 'day' ? `${item.name.slice(-2)}日` : item.name.replace('第', '')}
                        </span>
                      ) : null,
                    );
                  })()}
                </div>
                <div className="metrics-chart-caption">
                  <span>{period === 'day' ? '日期' : '周次'}　·　悬停查看 Token 与费用</span>
                  <span>Token 数量</span>
                </div>
              </div>
            )}
          </section>

          <div className="metrics-usage-grid">
            <UsageList title="MCP 工具调用" kind="mcp" rows={data?.mcp_usage || []} />
            <UsageList title="Skill 使用" kind="skill" rows={data?.skill_usage || []} />
          </div>
        </>
      )}
    </div>
  );
};
