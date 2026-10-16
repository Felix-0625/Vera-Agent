import React from 'react';
import { Image as ImageIcon, X } from 'lucide-react';
import { ChatImageAttachment } from '../../types/chat';
import { IconButton } from '../common/IconButton';

interface ImageAttachmentStripProps {
  images: ChatImageAttachment[];
  onRemove: (id: string) => void;
}

export const ImageAttachmentStrip: React.FC<ImageAttachmentStripProps> = ({ images, onRemove }) => {
  if (!images.length) return null;
  return (
    <div aria-label="待发送图片" style={{ display: 'flex', gap: 'var(--space-2)', overflowX: 'auto', padding: 'var(--space-2-5) var(--space-3-5) var(--space-0-5)' }}>
      {images.map((image) => (
        <div key={image.id} style={{ width: 88, height: 68, flex: '0 0 auto', position: 'relative', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-default)', background: 'var(--bg-card)' }}>
          <img src={image.data_url} alt={image.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          <IconButton className="image-attachment-remove" label={`移除图片 ${image.name}`} size="sm" onClick={() => onRemove(image.id)}><X size={13} /></IconButton>
        </div>
      ))}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-25)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}><ImageIcon size={13} />{images.length}/4</div>
    </div>
  );
};
