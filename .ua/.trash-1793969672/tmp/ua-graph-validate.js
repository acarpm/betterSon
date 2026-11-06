const fs=require('fs');
try{
const g=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const scanPath=process.argv[4];
const issues=[],warnings=[];
const NT=['file','function','class','module','concept','config','document','service','table','endpoint','pipeline','schema','resource','domain','flow','step'];
const ET=['imports','exports','contains','inherits','implements','calls','subscribes','publishes','middleware','reads_from','writes_to','transforms','validates','depends_on','tested_by','configures','related','similar_to','deploys','serves','migrates','documents','provisions','routes','defines_schema','triggers','contains_flow','flow_step','cross_domain'];
const DIR=['forward','backward','bidirectional'];
const nodes=g.nodes||[],edges=g.edges||[],layers=g.layers||[],tour=g.tour||[];
const domain=nodes.some(n=>['domain','flow','step'].includes(n.type));
const ids=new Map();
nodes.forEach((n,i)=>{
 if(!ids.has(n.id))ids.set(n.id,[]);ids.get(n.id).push(i);
 const l='Node '+i+' ('+n.id+')';
 if(typeof n.id!=='string'||!n.id)issues.push(l+' missing id');
 if(!NT.includes(n.type))issues.push(l+' invalid type '+n.type);
 if(typeof n.name!=='string'||!n.name)issues.push(l+' missing name');
 if(typeof n.summary!=='string'||!n.summary.trim())issues.push(l+' missing summary');
 else if(n.summary.trim()===n.name||n.summary.trim()===(n.filePath||'').split('/').pop())warnings.push(l+' has generic summary');
 if(!Array.isArray(n.tags)||!n.tags.length)issues.push(l+' missing tags');
 else if(n.tags.some(t=>typeof t!=='string'||t!==t.toLowerCase()||/\s/.test(t)))warnings.push(l+' has non-lowercase/hyphenated tags');
 if(!['simple','moderate','complex'].includes(n.complexity))issues.push(l+' invalid complexity '+n.complexity);
 if(typeof n.id==='string'&&n.type&&!n.id.startsWith(n.type+':'))warnings.push(l+' type/prefix mismatch');
});
for(const [id,ix] of ids)if(ix.length>1)issues.push('Duplicate node id '+id+' at indices '+ix.join(','));
const deg={};
edges.forEach((e,i)=>{
 const l='Edge '+i;
 if(!e.source||!ids.has(e.source))issues.push(l+' source missing/dangling: '+e.source);
 if(!e.target||!ids.has(e.target))issues.push(l+' target missing/dangling: '+e.target);
 if(!ET.includes(e.type))issues.push(l+' invalid type '+e.type);
 if(!DIR.includes(e.direction))issues.push(l+' invalid direction '+e.direction);
 if(typeof e.weight!=='number'||e.weight<0||e.weight>1)issues.push(l+' invalid weight '+e.weight);
 if(e.source===e.target)warnings.push(l+' self-reference '+e.source);
 deg[e.source]=(deg[e.source]||0)+1;deg[e.target]=(deg[e.target]||0)+1;
});
const orph=nodes.filter(n=>!deg[n.id]);
if(orph.length)warnings.push(orph.length+' orphan nodes: '+orph.map(n=>n.id).join(', '));
const emp=(m)=>domain?warnings.push(m):issues.push(m);
if(!nodes.length)issues.push('No nodes');if(!edges.length)issues.push('No edges');
if(!layers.length)emp('No layers');if(!tour.length)emp('No tour steps');
const FL=['file','config','document','service','pipeline','table','schema','resource','endpoint'];
const cnt={};
layers.forEach((L,i)=>{
 if(!Array.isArray(L.nodeIds)||!L.nodeIds.length)issues.push('Layer '+i+' empty nodeIds');
 (L.nodeIds||[]).forEach(id=>{if(!ids.has(id))issues.push('Layer '+i+' dangling '+id);cnt[id]=(cnt[id]||0)+1;});
});
if(!(domain&&!layers.length))nodes.filter(n=>FL.includes(n.type)).forEach(n=>{
 if(!cnt[n.id])issues.push('File-level node '+n.id+' in no layer');
 else if(cnt[n.id]>1)issues.push('File-level node '+n.id+' in '+cnt[n.id]+' layers');
});
tour.forEach((s,i)=>{
 if(s.order!==i+1)warnings.push('Tour step '+i+' order '+s.order+' expected '+(i+1));
 if(!Array.isArray(s.nodeIds)||!s.nodeIds.length)warnings.push('Tour step '+i+' no nodeIds');
 (s.nodeIds||[]).forEach(id=>{if(!ids.has(id))issues.push('Tour step '+i+' dangling '+id);});
});
if(tour.length&&(tour.length<5||tour.length>15))warnings.push('Tour has '+tour.length+' steps (expected 5-15)');
const has=(id,ts)=>edges.some(e=>(e.source===id||e.target===id)&&ts.includes(e.type));
const rules={document:['documents'],service:['deploys','depends_on'],pipeline:['triggers'],table:['migrates','defines_schema'],schema:['defines_schema'],domain:['contains_flow'],flow:['flow_step']};
nodes.forEach(n=>{const r=rules[n.type];if(r&&!has(n.id,r))warnings.push(n.type+' node '+n.id+' has no '+r.join('/')+' edge');});
// cross-validate
if(scanPath){
 const sc=JSON.parse(fs.readFileSync(scanPath,'utf8'));
 const files=(sc.files||[]).map(f=>f.path);
 const fp=new Set(nodes.filter(n=>FL.includes(n.type)).map(n=>n.filePath));
 const allfp=new Set(nodes.map(n=>n.filePath).filter(Boolean));
 files.filter(f=>!fp.has(f)).forEach(f=>warnings.push('Scan file missing from graph: '+f));
 const fs2=new Set(files);
 [...allfp].filter(f=>!fs2.has(f)).forEach(f=>warnings.push('Graph filePath not in scan inventory: '+f));
 warnings.push('Cross-check: scan files='+files.length+', file-level graph filePaths='+fp.size);
}
const nodeTypes={},edgeTypes={};
nodes.forEach(n=>nodeTypes[n.type]=(nodeTypes[n.type]||0)+1);
edges.forEach(e=>edgeTypes[e.type]=(edgeTypes[e.type]||0)+1);
fs.writeFileSync(process.argv[3],JSON.stringify({scriptCompleted:true,issues,warnings,stats:{totalNodes:nodes.length,totalEdges:edges.length,totalLayers:layers.length,tourSteps:tour.length,nodeTypes,edgeTypes}},null,2));
}catch(e){console.error(e);process.exit(1);}
