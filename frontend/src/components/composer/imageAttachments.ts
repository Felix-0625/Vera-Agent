import { ChatImageAttachment } from '../../types/chat';

export const MAX_CHAT_IMAGE_BYTES = 8 * 1024 * 1024;

export async function readImageFiles(files: FileList | File[]): Promise<ChatImageAttachment[]> {
  const images = Array.from(files).filter((file) => file.type.startsWith('image/') && file.size <= MAX_CHAT_IMAGE_BYTES);
  return Promise.all(images.map((file) => new Promise<ChatImageAttachment>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({
      id: typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${file.name}`,
      name: file.name || 'pasted-image.png',
      mime_type: file.type || 'image/png',
      data_url: String(reader.result),
    });
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  })));
}
