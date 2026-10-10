import React from 'react';
import { Image as ImageIcon, X } from 'lucide-react';
import { ChatImageAttachment } from '../../types/chat';

interface ImageAttachmentStripProps {
  images: ChatImageAttachment[];
  onRemove: (id: string) => void;
}

export const ImageAttachmentStrip: React.FC<ImageAttachmentStripProps> = ({ images, onRemove }) => {
  if (!images.length) return null;
  return (
    <div aria-label="待发送图片" style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '10px 14px 2px' }}>
      {images.map((image) => (
        <div key={image.id} style={{ width: 88, height: 68, flex: '0 0 auto', position: 'relative', borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(148,163,184,.22)', background: 'rgba(255,255,255,.04)' }}>
          <img src={image.data_url} alt={image.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          <button onClick={() => onRemove(image.id)} aria-label={`移除图片 ${image.name}`} title="移除图片" style={{ position: 'absolute', top: 4, right: 4, width: 19, height: 19, display: 'grid', placeItems: 'center', borderRadius: 999, color: '#fff', background: 'rgba(10,12,17,.8)' }}><X size={12} /></button>
        </div>
      ))}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-muted)', fontSize: 11 }}><ImageIcon size={13} />{images.length}/4</div>
    </div>
  );
};
