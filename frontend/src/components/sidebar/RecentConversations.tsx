import React, { useState } from 'react';
import { MoreVertical } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { Thread } from '../../types/chat';
import { ConversationContextMenu } from './ConversationContextMenu';
import { updateThread, deleteThread } from '../../api/chatApi';
import { InlineThreadRename } from './InlineThreadRename';

export const RecentConversations: React.FC = () => {
  const {threads,activeThreadId,selectThread,loadThreads}=useChatStore();
  const [menuTarget,setMenuTarget]=useState<{thread:Thread;pos:{x:number;y:number}}|null>(null);
  const [editingThreadId,setEditingThreadId]=useState<string|null>(null);
  const recent=threads.filter(thread=>!thread.is_archived&&!thread.project_id&&!thread.is_pinned).slice(0,6);
  const openMenu=(event:React.MouseEvent,thread:Thread)=>{event.preventDefault();event.stopPropagation();setMenuTarget({thread,pos:{x:event.clientX,y:event.clientY}});};
  const pin=async(thread:Thread)=>{await updateThread(thread.thread_id,{is_pinned:!thread.is_pinned});await loadThreads();};
  const rename=async(thread:Thread)=>{setEditingThreadId(thread.thread_id);};
  const saveThreadName=async(thread:Thread,title:string|null)=>{if(title){await updateThread(thread.thread_id,{title});await loadThreads();}setEditingThreadId(null);};
  const archive=async(thread:Thread)=>{await updateThread(thread.thread_id,{is_archived:!thread.is_archived});await loadThreads();};
  const remove=async(thread:Thread)=>{if(window.confirm(`确定要删除对话 "${thread.title}" 吗？`)){await deleteThread(thread.thread_id);await loadThreads();}};
  return <section style={{padding:'0 12px 10px',display:'flex',flexDirection:'column',gap:3}}>
    <div style={{padding:'2px 12px',fontSize:11,fontWeight:600,color:'var(--text-muted)'}}>最近会话</div>
    {!recent.length?<div style={{padding:'4px 12px',fontSize:12,color:'var(--text-disabled)'}}>暂无对话</div>:recent.map(thread=><div key={thread.thread_id} onClick={()=>{if(editingThreadId!==thread.thread_id)void selectThread(thread.thread_id);}} onContextMenu={event=>openMenu(event,thread)} style={{display:'flex',alignItems:'center',gap:6,minWidth:0,padding:'5px 8px 5px 12px',borderRadius:'var(--radius-sm)',color:activeThreadId===thread.thread_id?'var(--text-primary)':'var(--text-secondary)',background:activeThreadId===thread.thread_id?'rgba(255,255,255,.07)':'transparent',fontSize:12,cursor:'pointer'}}>{editingThreadId===thread.thread_id?<InlineThreadRename title={thread.title||'对话'} onSave={title=>saveThreadName(thread,title)} onCancel={()=>saveThreadName(thread,null)}/>:<span style={{flex:1,minWidth:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{thread.title||'对话'}</span>}<button onClick={event=>openMenu(event,thread)} title="操作菜单" style={{padding:2,color:'var(--text-muted)',display:'flex',flexShrink:0}}><MoreVertical size={13}/></button></div>)}
    {menuTarget&&<ConversationContextMenu thread={menuTarget.thread} position={menuTarget.pos} onClose={()=>setMenuTarget(null)} onPin={pin} onRename={rename} onArchive={archive} onDelete={remove}/>}
  </section>;
};
