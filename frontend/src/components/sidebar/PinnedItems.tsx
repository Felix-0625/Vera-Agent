import React, { useState } from 'react';
import { MoreVertical, Pin } from 'lucide-react';
import { useProjectStore } from '../../stores/projectStore';
import { useChatStore } from '../../stores/chatStore';
import { updateThread, deleteThread } from '../../api/chatApi';
import { Thread } from '../../types/chat';
import { ConversationContextMenu } from './ConversationContextMenu';
import { useLayoutStore } from '../../stores/layoutStore';
import { ProjectRow } from './ProjectRow';
import { InlineThreadRename } from './InlineThreadRename';

export const PinnedItems: React.FC = () => {
  const { projectsHistory, updateProject: saveProject, deleteProject } = useProjectStore();
  const { threads, activeThreadId, selectThread, openDraftConversation, loadThreads } = useChatStore();
  const [menuTarget, setMenuTarget] = useState<{ thread:Thread; pos:{x:number;y:number} } | null>(null);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const { openProjectEdit } = useLayoutStore();
  const pinnedProjects=projectsHistory.filter(project=>project.is_pinned);
  const pinnedProjectIds=new Set(pinnedProjects.map(project=>project.id));
  const pinnedThreads=threads.filter(thread=>thread.is_pinned&&!thread.is_archived&&!(thread.project_id&&pinnedProjectIds.has(thread.project_id)));
  if(!pinnedProjects.length&&!pinnedThreads.length)return null;

  const openMenu=(event:React.MouseEvent,thread:Thread)=>{event.preventDefault();event.stopPropagation();setMenuTarget({thread,pos:{x:event.clientX,y:event.clientY}});};
  const handlePin=async(thread:Thread)=>{await updateThread(thread.thread_id,{is_pinned:!thread.is_pinned});await loadThreads();};
  const handleRename=async(thread:Thread)=>{setEditingThreadId(thread.thread_id);};
  const saveThreadName=async(thread:Thread,title:string|null)=>{if(title){await updateThread(thread.thread_id,{title});await loadThreads();}setEditingThreadId(null);};
  const handleArchive=async(thread:Thread)=>{await updateThread(thread.thread_id,{is_archived:!thread.is_archived});await loadThreads();};
  const handleDelete=async(thread:Thread)=>{if(window.confirm(`确定要删除对话 "${thread.title}" 吗？`)){await deleteThread(thread.thread_id);await loadThreads();}};
  const togglePin=async(project:typeof pinnedProjects[number])=>{await saveProject(project.id,{is_pinned:!project.is_pinned});};

  return <section style={{padding:'0 12px',display:'flex',flexDirection:'column',gap:3}}>
    <div style={{display:'flex',alignItems:'center',padding:'2px 12px',fontSize:11,fontWeight:650,color:'var(--text-muted)'}}>置顶</div>
    {pinnedProjects.map(project=><ProjectRow key={project.id} project={project} threads={threads.filter(thread=>!thread.is_archived&&thread.project_id===project.id)} activeThreadId={activeThreadId} onSelectThread={id=>void selectThread(id)} onNewDraftInProject={id=>openDraftConversation(id)} onContextMenu={openMenu} onPinProject={togglePin} onEditProject={openProjectEdit} onDeleteProject={item=>void deleteProject(item.id)} editingThreadId={editingThreadId} onRenameThread={saveThreadName}/>)}
    {pinnedThreads.map(thread=><div key={thread.thread_id} style={{display:'flex',alignItems:'center',gap:6,minWidth:0,padding:'6px 9px',borderRadius:8,color:'var(--text-secondary)',fontSize:12,cursor:'pointer'}} onClick={()=>{if(editingThreadId!==thread.thread_id)void selectThread(thread.thread_id);}} onContextMenu={event=>openMenu(event,thread)} onMouseEnter={event=>event.currentTarget.style.background='rgba(255,255,255,.05)'} onMouseLeave={event=>event.currentTarget.style.background='transparent'}><Pin size={12} color="#f5b942"/>{editingThreadId===thread.thread_id?<InlineThreadRename title={thread.title||'对话'} onSave={title=>saveThreadName(thread,title)} onCancel={()=>saveThreadName(thread,null)}/>:<span style={{flex:1,minWidth:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{thread.title||'对话'}</span>}<button aria-label="置顶对话操作" title="操作菜单" onClick={event=>openMenu(event,thread)} style={{padding:2,color:'var(--text-muted)',display:'flex'}}><MoreVertical size={13}/></button></div>)}
    {menuTarget&&<ConversationContextMenu thread={menuTarget.thread} position={menuTarget.pos} onClose={()=>setMenuTarget(null)} onPin={handlePin} onRename={handleRename} onArchive={handleArchive} onDelete={handleDelete}/>}
  </section>;
};
