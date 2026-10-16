import React from 'react';
import logoUrl from '../../assets/logo.png';

interface VeraLogoProps {
  size?: number;
  className?: string;
}

/**
 * 品牌 Logo 组件 (严格使用根目录挪动的 图标.png)
 */
export const VeraLogo: React.FC<VeraLogoProps> = ({ size = 24, className = '' }) => {
  return (
    <img
      src={logoUrl}
      alt="VeraAgent Logo"
      width={size}
      height={size}
      className={className}
      style={{
        display: 'inline-block',
        verticalAlign: 'middle',
        flexShrink: 0,
        objectFit: 'contain',
        borderRadius: 'var(--radius-xs)',
      }}
    />
  );
};
