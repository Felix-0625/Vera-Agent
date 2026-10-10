import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, BarChart3, ChartNoAxesColumnIncreasing, ChevronLeft, ChevronRight, Coins, RefreshCw, Sparkles } from 'lucide-react';
import { fetchAnalyticsDashboard } from '../../api/toolApi';
import { AnalyticsDashboard } from '../../types/tool';
import { useChatStore } from '../../stores/chatStore';

type Period = 'day' | 'week' | 'month';
const USD_TO_CNY = 7.2;
const MODEL_COLORS = ['#8b7cf6', '#36c7a2', '#59a8ff', '#f5a557', '#e879a9', '#55c6d8'];
const money = (usd: number) => `¥${(usd * USD_TO_CNY).toFixed(2)}`;

const UsageList: React.FC<{ title: string; kind: 'mcp' | 'skill'; rows: Array<{ name: string; count: number }> }> = ({ title, kind, rows }) => {
  const Icon = kind === 'mcp' ? Activity : Sparkles;
  const max = Math.max(1, ...rows.map((row) => row.count));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <section className="metrics-card metrics-usage-card">
      <header className="metrics-card-title"><span className={`metrics-title-icon ${kind}`}><Icon size={15} /></span><h3>{title}</h3><span className="metrics-total">{total.toLocaleString()} 次</span></header>
      {rows.length ? <div className="metrics-usage-list">{rows.map((row, index) => {
        const label = kind === 'mcp' ? ({ web_search: '网页搜索', fetch_web_page: '网页读取' } as Record<string, string>)[row.name] || row.name : row.name;
        return <div className="metrics-usage-row" key={row.name}>
          <div className="metrics-usage-label"><span className="metrics-usage-dot" style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }} /><span title={row.name}>{label}</span><strong>{row.count.toLocaleString()} 次</strong></div>
          <div className="metrics-usage-track"><span style={{ width: `${Math.max(4, row.count / max * 100)}%`, background: MODEL_COLORS[index % MODEL_COLORS.length] }} /></div>
        </div>;
      })}</div> : <div className="metrics-empty-small">暂无调用记录</div>}
    </section>
  );
};

export const MetricsTab: React.FC = () => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || undefined : draftProjectId || undefined;
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState<Period>('day');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [hovered, setHovered] = useState<number | null>(null);
  const chartScrollRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    if (!projectId) { setData(null); return; }
    setLoading(true);
    setError('');
    try { setData(await fetchAnalyticsDashboard(projectId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : '数据加载失败'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void loadData(); }, [projectId]);

  const months = data?.retained_months || [];
  useEffect(() => {
    if (months.length && (!selectedMonth || !months.includes(selectedMonth))) setSelectedMonth(months[months.length - 1]);
  }, [months, selectedMonth]);
  const activeMonth = data?.monthly_models.find((item) => item.month === selectedMonth);
  const chart = useMemo(() => {
    if (period === 'month') return (activeMonth?.models || []).filter((item) => item.tokens > 0 || item.cost_usd > 0).map((item) => ({ name: item.name, tokens: item.tokens, cost_usd: item.cost_usd }));
    if (period === 'day') return (data?.daily_trends || []).filter((item) => item.month === selectedMonth).map((item) => ({ name: item.date, tokens: item.tokens, cost_usd: item.cost_usd }));
    return (data?.weekly_trends || []).filter((item) => item.month === selectedMonth).map((item) => ({ name: item.label, tokens: item.tokens, cost_usd: item.cost_usd }));
  }, [activeMonth, data, period, selectedMonth]);
  const maxTokens = Math.max(1, ...chart.map((item) => item.tokens));
  const chartWidth = period === 'day' ? Math.max(460, chart.length * 38) : Math.max(460, chart.length * (period === 'week' ? 92 : 84));
  const points = chart.map((item, index) => ({
    x: chart.length < 2 ? chartWidth / 2 : 24 + index * ((chartWidth - 48) / (chart.length - 1)),
    y: 156 - (item.tokens / maxTokens) * 126,
  }));
  const linePath = points.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ');
  const totalCalls = (data?.mcp_usage || []).reduce((sum, row) => sum + row.count, 0) + (data?.skill_usage || []).reduce((sum, row) => sum + row.count, 0);

  return (
    <div className="metrics-page">
      <div className="metrics-header">
        <div className="metrics-heading"><span><BarChart3 size={16} /></span><strong>数据看板</strong></div>
        <button className="metrics-refresh" onClick={() => void loadData()} title="刷新数据" aria-label="刷新数据" disabled={loading}><RefreshCw size={14} className={loading ? 'pulse-glow' : ''} /></button>
      </div>
      {!projectId ? <div className="metrics-empty"><Coins size={25} /><span>选择一个项目查看项目用量</span></div> : error ? <div className="metrics-empty metrics-error">{error}</div> : <>
        <div className="metrics-summary">
          <div className="metrics-summary-card"><span>近 3 个月 Token</span><strong>{(data?.summary.total_tokens || 0).toLocaleString()}</strong></div>
          <div className="metrics-summary-card"><span>近 3 个月费用 · ¥估算</span><strong title="按 1 USD = 7.2 CNY 换算">{money(data?.summary.total_cost_usd || 0)}</strong></div>
          <div className="metrics-summary-card"><span>今日费用 · ¥估算</span><strong title="按 1 USD = 7.2 CNY 换算">{money(data?.summary.today_cost_usd || 0)}</strong></div>
          <div className="metrics-summary-card"><span>MCP / Skill 调用</span><strong>{totalCalls.toLocaleString()}</strong><small>次</small></div>
        </div>

        <section className="metrics-card metrics-chart-card">
          <header className="metrics-card-title metrics-chart-title">
            <div><span className="metrics-title-icon chart"><ChartNoAxesColumnIncreasing size={15} /></span><h3>Token 消耗</h3></div>
            <div className="metrics-periods">{(['day', 'week', 'month'] as Period[]).map((value) => <button key={value} className={period === value ? 'active' : ''} onClick={() => { setPeriod(value); setHovered(null); }}>{value === 'day' ? '每日' : value === 'week' ? '每周' : '按月'}</button>)}</div>
          </header>
          <div className="metrics-month-select">
            <select aria-label="选择统计月份" value={selectedMonth} onChange={(event) => { setSelectedMonth(event.target.value); setHovered(null); }}>{months.map((month) => <option key={month} value={month}>{month}</option>)}</select>
            {period !== 'month' && <div className="metrics-chart-scroll-actions"><button type="button" onClick={() => chartScrollRef.current?.scrollBy({ left: -280, behavior: 'smooth' })} aria-label="向左查看图表"><ChevronLeft size={13} /></button><button type="button" onClick={() => chartScrollRef.current?.scrollBy({ left: 280, behavior: 'smooth' })} aria-label="向右查看图表"><ChevronRight size={13} /></button></div>}
          </div>
          {!chart.length ? <div className="metrics-chart-empty">暂无 Token 用量记录</div> : period === 'month' ? <div className="metrics-model-chart" ref={chartScrollRef}>
            <div className="metrics-model-bars" style={{ width: chartWidth, minWidth: '100%' }}>{chart.map((item, index) => <div className="metrics-model-column" key={item.name} onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)}>
              {hovered === index && <div className="metrics-tooltip metrics-model-tooltip"><b>{item.name}</b><span>{item.tokens.toLocaleString()} Tokens</span><span>{money(item.cost_usd)}</span></div>}
              <div className="metrics-model-bar" style={{ height: `${Math.max(5, item.tokens / maxTokens * 100)}%`, background: MODEL_COLORS[index % MODEL_COLORS.length] }} />
              <span className="metrics-model-name" title={item.name}>{item.name}</span>
            </div>)}</div>
            <div className="metrics-month-details">{chart.map((item, index) => <div className="metrics-month-detail" key={item.name}><span className="metrics-usage-dot" style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }} /><span className="metrics-month-model" title={item.name}>{item.name}</span><span>{item.tokens.toLocaleString()} Token</span><strong>{money(item.cost_usd)}</strong></div>)}</div>
            <div className="metrics-chart-caption"><span>Token 与人民币费用</span><span>{selectedMonth}</span></div>
          </div> : <div className="metrics-line-chart">
            <div className="metrics-chart-axis"><span>{maxTokens.toLocaleString()}</span><span>{Math.round(maxTokens / 2).toLocaleString()}</span><span>0</span></div>
            <div className="metrics-chart-scroll" ref={chartScrollRef}><svg viewBox={`0 0 ${chartWidth} 178`} style={{ width: chartWidth }} role="img" aria-label={period === 'day' ? '每日 Token 折线图' : '每周 Token 柱形图'}>
              {[30, 93, 156].map((y) => <line key={y} x1="20" y1={y} x2={chartWidth - 20} y2={y} className="metrics-grid-line" />)}
              {period === 'day' ? <><path d={linePath} className="metrics-line" />{points.map((point, index) => <g key={index} onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)} className="metrics-point-hit"><circle cx={point.x} cy={point.y} r="10" fill="transparent" />{hovered === index && <><circle cx={point.x} cy={point.y} r="6" className="metrics-point-active" /><foreignObject x={Math.min(chartWidth - 136, Math.max(4, point.x - 64))} y={Math.max(2, point.y - 66)} width="132" height="58"><div className="metrics-tooltip"><b>{chart[index].name}</b><span>{chart[index].tokens.toLocaleString()} Tokens</span><span>{money(chart[index].cost_usd)}</span></div></foreignObject></>}<circle cx={point.x} cy={point.y} r="3.3" className="metrics-point" /></g>)}</> : chart.map((item, index) => <g key={item.name} onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)} className="metrics-point-hit"><rect x={points[index].x - 10} y={points[index].y} width="20" height={156 - points[index].y} rx="3" className={`metrics-week-bar ${hovered === index ? 'hovered' : ''}`} />{hovered === index && <foreignObject x={Math.min(chartWidth - 136, Math.max(4, points[index].x - 64))} y={Math.max(2, points[index].y - 66)} width="132" height="58"><div className="metrics-tooltip"><b>{item.name}</b><span>{item.tokens.toLocaleString()} Tokens</span><span>{money(item.cost_usd)}</span></div></foreignObject>}</g>)}
            </svg><div className="metrics-x-labels" style={{ width: chartWidth, minWidth: '100%' }}>{chart.filter((_, index) => period === 'day' ? index === 0 || index % 5 === 4 || index === chart.length - 1 : true).map((item) => <span key={item.name}>{period === 'day' ? item.name.slice(-2) : item.name}</span>)}</div></div>
            <div className="metrics-chart-caption"><span>{period === 'day' ? '日期' : '周次'}　·　悬停查看 Token 与费用</span><span>Token 数量</span></div>
          </div>}
        </section>

        <div className="metrics-usage-grid"><UsageList title="MCP 工具调用" kind="mcp" rows={data?.mcp_usage || []} /><UsageList title="Skill 使用" kind="skill" rows={data?.skill_usage || []} /></div>
      </>}
    </div>
  );
};
