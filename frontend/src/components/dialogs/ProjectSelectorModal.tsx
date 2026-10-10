import React, { useEffect, useState } from 'react';
import { Folder, FolderPlus, FolderOpen, Check, Plus, Trash2, ChevronDown, X } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { useChatStore } from '../../stores/chatStore';
import { selectProjectFolder } from '../../api/projectApi';
import { Modal } from '../common/Modal';

const projectBlue = '#4b91ff';
const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).at(-1) || path;

export const ProjectSelectorModal: React.FC = () => {
  const { projectSelectorOpen, projectSelectorView, editingProject, setProjectSelectorOpen } = useLayoutStore();
  const { currentProject, projectsHistory, bindProject, deleteProject, updateProject } = useProjectStore();
  const { setDraftProjectId, loadThreads } = useChatStore();
  const [name, setName] = useState('');
  const [folders, setFolders] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [folderPickerBusy, setFolderPickerBusy] = useState(false);
  const isEdit = projectSelectorView === 'edit';
  const isCreate = projectSelectorView === 'create';

  useEffect(() => {
    if (!projectSelectorOpen) return;
    setError('');
    if (projectSelectorView === 'edit' && editingProject) {
      setName(editingProject.name || '');
      setFolders(editingProject.folders?.length ? editingProject.folders : [editingProject.path]);
    } else {
      setName('');
      setFolders([]);
    }
  }, [projectSelectorOpen, projectSelectorView, editingProject]);

  const browseFolder = async () => {
    if (busy || folderPickerBusy) return;
    setFolderPickerBusy(true);
    setError('');
    try {
      const result = await selectProjectFolder();
      if (result.path) setFolders(current => current.includes(result.path!) ? current : [...current, result.path!]);
      else setError('已取消文件夹选择。');
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法打开系统文件夹选择器，请检查本地服务是否运行。');
    } finally { setFolderPickerBusy(false); }
  };

  const saveProject = async () => {
    if (!name.trim()) { setError('请输入项目名称。'); return; }
    if (!folders.length) { setError('请至少选择一个源文件夹。'); return; }
    setBusy(true); setError('');
    try {
      if (isEdit && editingProject) {
        await updateProject(editingProject.id, { name: name.trim(), folders });
        const active = useProjectStore.getState().currentProject;
        if (active?.id === editingProject.id) setDraftProjectId(editingProject.id);
      } else {
        await bindProject(folders[0], { name: name.trim(), folders });
        const created = useProjectStore.getState().currentProject;
        setDraftProjectId(created?.id || null);
        await loadThreads();
      }
      setProjectSelectorOpen(false);
    } catch {
      setError('项目保存失败，请确认所选文件夹仍然存在。');
    } finally { setBusy(false); }
  };

  const selectExisting = async (id: string, path: string, projectName: string, projectFolders?: string[]) => {
    setBusy(true); setError('');
    try {
      await bindProject(path, { projectId:id, name:projectName, folders:projectFolders });
      setDraftProjectId(id);
      await loadThreads();
      setProjectSelectorOpen(false);
    } catch { setError('打开项目失败，请检查项目目录是否仍然可用。'); }
    finally { setBusy(false); }
  };

  const handleRemoveProject = async () => {
    if (!editingProject) return;
    setBusy(true);
    try { await deleteProject(editingProject.id); setDraftProjectId(null); setProjectSelectorOpen(false); }
    catch { setError('移除项目失败，请稍后重试。'); }
    finally { setBusy(false); }
  };

  const title = isEdit ? '编辑项目' : isCreate ? '创建项目' : '选择项目';
  return <Modal isOpen={projectSelectorOpen} onClose={() => setProjectSelectorOpen(false)} title={title} width={isEdit ? 638 : isCreate ? 650 : 520} titleStyle={isEdit || isCreate ? { fontSize:24, fontWeight:700, letterSpacing:'-.02em' } : undefined} headerStyle={isCreate ? { padding:'20px 24px 8px', borderBottom:0 } : undefined} contentStyle={isCreate ? { padding:'12px 24px 20px' } : undefined}>
    {isEdit || isCreate ? <div style={{ display:'flex', flexDirection:'column', gap:16, minHeight:isCreate ? 309 : 324 }}>
      {error && <div role="alert" style={{ padding:'8px 10px', borderRadius:8, background:'rgba(244,63,94,.09)', color:'var(--accent-rose)', fontSize:12 }}>{error}</div>}
      <label style={{ position:'relative', display:'block' }}>
        <Folder size={17} color={projectBlue} style={{ position:'absolute', left:17, top:16, zIndex:1 }} />
        {isCreate && <span aria-hidden="true" style={{ position:'absolute', left:49, top:1, bottom:1, width:1, background:'rgba(148,163,184,.22)' }} />}
        <input aria-label="项目名称" value={name} onChange={event=>setName(event.target.value)} placeholder="项目名称" style={{ width:'100%', height:50, padding:`0 14px 0 ${isCreate ? 61 : 46}px`, borderRadius:12, border:'1px solid #4389ff', background:'#20242c', color:'var(--text-primary)', fontSize:14, outline:'none' }} />
      </label>
      <div>
        <div style={{ marginBottom:9, color:'var(--text-primary)', fontSize:12.5, fontWeight:600 }}>源文件夹</div>
        <div style={folders.length ? { border:'1px solid var(--border-default)', borderRadius:14, overflow:'hidden', background:'rgba(255,255,255,.018)' } : { minHeight:130, border:'1px solid var(--border-default)', borderRadius:14, background:'rgba(255,255,255,.018)', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:12 }}>
          {folders.map((path,index)=><div key={`${path}-${index}`} style={{ minHeight:54, padding:'9px 14px', display:'flex', alignItems:'center', gap:11, borderBottom:'1px solid rgba(148,163,184,.12)' }}>
            <FolderOpen size={17} color={projectBlue} style={{ flex:'0 0 auto' }}/>
            <div style={{ flex:1,minWidth:0 }}><div style={{fontSize:12.5,color:'var(--text-primary)',fontWeight:550}}>{folderName(path)}</div><div title={path} style={{fontSize:10.5,color:'var(--text-muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{path}</div></div>
            <button onClick={()=>setFolders(current=>current.filter((_,i)=>i!==index))} title="移除此文件夹" aria-label={`移除文件夹 ${folderName(path)}`} style={{padding:5,color:'var(--text-muted)',cursor:'pointer'}}><X size={14}/></button>
          </div>)}
          {folders.length ? <button disabled={busy||folderPickerBusy} onClick={()=>void browseFolder()} style={{ width:'100%', minHeight:54, padding:'0 16px', display:'flex', alignItems:'center', gap:10, color:'var(--text-primary)', fontSize:12.5, fontWeight:600, textAlign:'left', opacity:folderPickerBusy ? .65 : 1 }}><FolderPlus size={17} color={projectBlue}/><span>{folderPickerBusy?'正在打开文件夹选择器…':'添加文件夹'}</span></button> : <>
            <button disabled={busy||folderPickerBusy} onClick={()=>void browseFolder()} style={{ display:'flex', alignItems:'center', gap:8, color:'var(--text-secondary)', fontSize:12.5, fontWeight:600 }}><span>{folderPickerBusy?'正在打开文件夹选择器…':'在此电脑上添加文件夹'}</span><ChevronDown size={14} color="var(--text-muted)"/></button>
            <button disabled={busy||folderPickerBusy} onClick={()=>void browseFolder()} style={{ minWidth:82, height:32, padding:'0 12px', borderRadius:18, background:'rgba(255,255,255,.09)', color:'var(--text-primary)', fontSize:12, fontWeight:600, display:'flex', alignItems:'center', justifyContent:'center', gap:7, opacity:folderPickerBusy ? .65 : 1 }}><FolderPlus size={15}/><span>{folderPickerBusy?'打开中…':'添加'}</span></button>
          </>}
        </div>
      </div>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:12, marginTop:'auto', marginBottom:isCreate ? 5 : 0 }}>
        {isEdit ? <button disabled={busy} onClick={()=>void handleRemoveProject()} style={{ padding:'9px 14px', borderRadius:9, background:'rgba(239,68,68,.12)', color:'#fb7185', fontSize:12, fontWeight:600 }}>移除本地项目</button> : <span/>}
        <div style={{ display:'flex', alignItems:'center', gap:isCreate ? 20 : 10 }}>
          <button disabled={busy} onClick={()=>setProjectSelectorOpen(false)} style={isCreate ? { width:52, height:39, padding:0, color:'var(--text-secondary)', fontSize:12 } : { padding:'9px 14px', color:'var(--text-secondary)', fontSize:12 }}>取消</button>
          <button disabled={busy} onClick={()=>void saveProject()} style={{ width:isCreate ? 112 : 'auto', minWidth:isCreate ? 112 : 92, height:isCreate ? 39 : undefined, padding:isCreate ? '0 16px' : '9px 16px', borderRadius:10, background:'#e8e9eb', color:'#17191d', fontSize:12, fontWeight:700, opacity:busy?0.65:1 }}>{busy?'保存中…':isEdit?'保存':'创建项目'}</button>
        </div>
      </div>
    </div> : <div style={{ display:'flex', flexDirection:'column', gap:9 }}>
      <div style={{ fontSize:12, color:'var(--text-muted)', marginBottom:2 }}>选择一个已绑定的本地项目，或创建项目。</div>
      {error && <div role="alert" style={{ padding:'8px 10px', borderRadius:8, background:'rgba(244,63,94,.09)', color:'var(--accent-rose)', fontSize:12 }}>{error}</div>}
      {projectsHistory.map(project=>{
        const selected=currentProject?.path===project.path||currentProject?.repo_root===project.path;
        return <div key={project.id} onClick={()=>void selectExisting(project.id,project.path,project.name,project.folders)} className="glass-card" style={{padding:'11px 13px',display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,cursor:'pointer',border:selected?'1px solid rgba(75,145,255,.62)':'1px solid var(--border-subtle)',background:selected?'rgba(75,145,255,.075)':'rgba(255,255,255,.02)'}}>
          <div style={{display:'flex',alignItems:'center',gap:11,minWidth:0}}><span style={{width:34,height:34,flex:'0 0 34px',display:'grid',placeItems:'center',borderRadius:10,background:'rgba(75,145,255,.12)',border:'1px solid rgba(75,145,255,.18)'}}><FolderOpen size={16} color={projectBlue}/></span><div style={{minWidth:0}}><div style={{fontSize:12.5,fontWeight:600,color:'var(--text-primary)'}}>{project.name}</div><div style={{fontSize:10.5,color:'var(--text-muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',marginTop:3}}>{project.path}{project.folders&&project.folders.length>1?` · ${project.folders.length} 个文件夹`:''}</div></div></div>
          <div style={{display:'flex',alignItems:'center',gap:8,flex:'0 0 auto'}}>{selected&&<Check size={15} color={projectBlue}/>}<button onClick={event=>{event.stopPropagation();void deleteProject(project.id);}} style={{padding:5,color:'var(--text-muted)',borderRadius:7}} title="删除项目记录" aria-label={`删除 ${project.name} 项目记录`}><Trash2 size={13}/></button></div>
        </div>;
      })}
      {!projectsHistory.length&&<div style={{padding:25,textAlign:'center',color:'var(--text-muted)',fontSize:12,border:'1px dashed var(--border-default)',borderRadius:12}}>还没有绑定项目</div>}
      <button onClick={()=>useLayoutStore.getState().openProjectCreate()} style={{marginTop:4,minHeight:52,padding:'0 14px',borderRadius:11,border:'1px dashed rgba(75,145,255,.36)',background:'rgba(75,145,255,.045)',color:'#a9caff',fontSize:12.5,fontWeight:600,display:'flex',alignItems:'center',gap:9}}><Plus size={15} color={projectBlue}/><span>新建项目并选择文件夹</span></button>
    </div>}
  </Modal>;
};
