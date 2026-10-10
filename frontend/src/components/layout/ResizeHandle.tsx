import React, { useState } from 'react';

interface ResizeHandleProps {
  onResize: (deltaX: number) => void;
  direction?: 'left' | 'right';
}

export const ResizeHandle: React.FC<ResizeHandleProps> = ({ onResize, direction = 'left' }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    const startX = e.clientX;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = direction === 'left' ? moveEvent.clientX - startX : startX - moveEvent.clientX;
      onResize(deltaX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div
      onMouseDown={handleMouseDown}
      style={{
        width: 5,
        cursor: 'col-resize',
        backgroundColor: isDragging ? 'var(--accent-primary)' : 'transparent',
        transition: 'background-color 0.15s ease',
        zIndex: 20,
        position: 'relative',
        flexShrink: 0,
      }}
      onMouseEnter={(e) => {
        if (!isDragging) e.currentTarget.style.backgroundColor = 'rgba(124, 58, 237, 0.4)';
      }}
      onMouseLeave={(e) => {
        if (!isDragging) e.currentTarget.style.backgroundColor = 'transparent';
      }}
    />
  );
};
