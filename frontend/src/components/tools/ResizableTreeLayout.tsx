import React, { useRef, useState } from 'react';

export const ResizableTreeLayout: React.FC<{
  primary: React.ReactNode;
  secondary: React.ReactNode;
  collapsed: boolean;
  onToggle: () => void;
}> = ({ primary, secondary, collapsed, onToggle }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [treeWidth, setTreeWidth] = useState(250);
  const dragging = useRef(false);

  const resizeAt = (clientX: number) => {
    const bounds = containerRef.current?.getBoundingClientRect();
    if (!bounds) return;
    const next = Math.max(0, Math.min(bounds.width * 0.5, bounds.right - clientX));
    if (next < 28) {
      if (!collapsed) onToggle();
      return;
    }
    if (collapsed) onToggle();
    setTreeWidth(next);
  };

  return <div ref={containerRef} style={{ height: '100%', width: '100%', minWidth: 0, minHeight: 0, display: 'flex', overflow: 'hidden' }}>
    <div style={{ flex: 1, minWidth: 0, minHeight: 0, overflow: 'hidden' }}>{primary}</div>
    <div
      role="separator"
      aria-label="调整文件目录宽度"
      aria-orientation="vertical"
      onPointerDown={(event) => { dragging.current = true; event.currentTarget.setPointerCapture(event.pointerId); resizeAt(event.clientX); }}
      onPointerMove={(event) => { if (dragging.current) resizeAt(event.clientX); }}
      onPointerUp={() => { dragging.current = false; }}
      onDoubleClick={() => { if (!collapsed) onToggle(); else onToggle(); }}
      style={{ width: 5, flex: '0 0 5px', cursor: 'col-resize', background: 'var(--border-subtle)', touchAction: 'none' }}
      title="拖动调整目录宽度，双击收起/展开"
    />
    {collapsed ? <div style={{ display: 'none' }} /> : <aside style={{ width: treeWidth, flex: '0 0 auto', minWidth: 0, maxWidth: '50%', minHeight: 0, overflow: 'hidden' }}>{secondary}</aside>}
  </div>;
};
