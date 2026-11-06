const fs=require("fs");const g=JSON.parse(fs.readFileSync(process.argv[2]));
const fi={},fo={},adj={};
g.edges.forEach(e=>{fi[e.target]=(fi[e.target]||0)+1;fo[e.source]=(fo[e.source]||0)+1;if(e.type==="imports"||e.type==="calls")(adj[e.source]=adj[e.source]||[]).push(e.target)});
const rank=m=>Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,20);
const order=[],seen=new Set(["file:gui.py"]),q=["file:gui.py"];
while(q.length){const n=q.shift();order.push(n);(adj[n]||[]).forEach(t=>{if(!seen.has(t)){seen.add(t);q.push(t)}})}
fs.writeFileSync(process.argv[3],JSON.stringify({fanIn:rank(fi),fanOut:rank(fo),bfs:order}));
