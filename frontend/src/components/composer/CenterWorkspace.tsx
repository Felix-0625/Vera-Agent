import React, { Suspense, useRef, useState } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WelcomeBanner } from './WelcomeBanner';
import { MessageStream } from './MessageStream';
import { ApprovalBanner } from './ApprovalBanner';
import { ProjectCapsule } from './ProjectCapsule';
import { SignatureInputCard } from './SignatureInputCard';
import { readImageFiles } from './imageAttachments';
import { useLayoutStore } from '../../stores/layoutStore';

const TerminalTab = React.lazy(() => import('../tools/TerminalTab').then((module) => ({ default: module.TerminalTab })));


export const CenterWorkspace: React.FC = () => {
  const messages = useChatStore((state) => state.messages);
  const addDraftImages = useChatStore((state) => state.addDraftImages);
  const { bottomDrawerOpen, bottomDrawerHeight, setBottomDrawerHeight, toggleBottomDrawer } = useLayoutStore();
  const [isDraggingImage, setIsDraggingImage] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const resizeStart = useRef<{ y: number; height: number } | null>(null);
  const startResize = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const mainHeight = mainRef.current?.clientHeight || window.innerHeight;
    const maxHeight = Math.floor(mainHeight * 0.4);
    resizeStart.current = { y: event.clientY, height: Math.min(bottomDrawerHeight, maxHeight) };
    const move = (moveEvent: PointerEvent) => {
      if (!resizeStart.current || !mainRef.current) return;
      const max = Math.floor(mainRef.current.clientHeight * 0.4);
      const height = Math.max(130, Math.min(max, resizeStart.current.height + resizeStart.current.y - moveEvent.clientY));
      setBottomDrawerHeight(height);
    };
    const end = () => {
      resizeStart.current = null;
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end, { once: true });
  };

  const terminalDrawer = (
    <div className="center-terminal-drawer" style={{ height: bottomDrawerHeight, flexBasis: bottomDrawerHeight, maxHeight: '40%' }}>
      <div className="center-terminal-resize" onPointerDown={startResize} title="拖动调整终端高度" aria-label="调整终端高度" />
      <div style={{ height: 'calc(100% - 6px)', minHeight: 0 }}>
        <Suspense fallback={<div role="status" aria-live="polite" style={{ padding: 'var(--space-3)', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>正在加载终端…</div>}>
          <TerminalTab onClose={toggleBottomDrawer} />
        </Suspense>
      </div>
    </div>
  );

  const handleDragOver = (event: React.DragEvent<HTMLElement>) => {
    if (!Array.from(event.dataTransfer.types).includes('Files')) return;
    event.preventDefault();
    setIsDraggingImage(true);
  };

  const handleDrop = async (event: React.DragEvent<HTMLElement>) => {
    if (!Array.from(event.dataTransfer.types).includes('Files')) return;
    event.preventDefault();
    setIsDraggingImage(false);
    addDraftImages(await readImageFiles(event.dataTransfer.files));
  };

  return (
    <main
      ref={mainRef}
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-workspace)',
        position: 'relative',
        minWidth: 320,
        overflow: 'hidden',
      }}
      onDragEnter={handleDragOver}
      onDragOver={handleDragOver}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDraggingImage(false); }}
      onDrop={handleDrop}
    >
      {isDraggingImage && <div style={{ position: 'absolute', inset: 10, zIndex: 80, borderRadius: 'var(--radius-xl)', border: '1px dashed var(--accent-cyan)', background: 'var(--bg-info-soft)', display: 'grid', placeItems: 'center', color: 'var(--text-primary)', fontSize: 'var(--font-size-md)', pointerEvents: 'none' }}>松开鼠标添加图片</div>}
      {}
      <WorkspaceHeader />

      {messages.length === 0 ? (

        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 var(--space-6) 60px',
            overflowY: 'auto',
          }}
        >
          <WelcomeBanner />
          <div style={{ width: '100%', maxWidth: 762, marginTop: 28 }}>
            <ProjectCapsule />
            <SignatureInputCard />
          </div>
          <ApprovalBanner />
        </div>
      ) : (

        <>
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                width: '100%',
                maxWidth: 860,
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <MessageStream />
              <ApprovalBanner />
            </div>
          </div>

          <div
            style={{
              padding: '0 var(--space-5) var(--space-5)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <div style={{ width: '100%', maxWidth: 762 }}>
              <ProjectCapsule />
              <SignatureInputCard />
            </div>
          </div>

          {bottomDrawerOpen && terminalDrawer}
        </>
      )}

      {messages.length === 0 && bottomDrawerOpen && (
        terminalDrawer
      )}
    </main>
  );
};
