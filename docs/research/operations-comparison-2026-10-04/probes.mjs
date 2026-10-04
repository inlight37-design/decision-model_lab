// Research-only probes. No provider SDK, model, server, or repository writes.
// node --experimental-transform-types probes.mjs /path/to/research-sources
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { registerHooks } from 'node:module';
import { readFileSync } from 'node:fs';
// Bun's text imports appear in the constants dependency. Preserve their text;
// they are data, never evaluated as instructions or JavaScript.
registerHooks({load(url,context,nextLoad) {
  if (url.endsWith('.md')) return {format:'module',shortCircuit:true,source:`export default ${JSON.stringify(readFileSync(new URL(url),'utf8'))}`};
  return nextLoad(url,context);
}});
const root = resolve(process.argv[2]);
const pins = {backlog: '69e7b15362337d6712783d9a685f6e4bb693fa9d', 'lite-harness': 'dd99cfdfc68dbb6b3f7f986d54efd42572373a6c'};
for (const [repo, sha] of Object.entries(pins)) {
  assert.equal(execFileSync('git', ['-C', resolve(root, repo), 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim(), sha);
  assert.equal(execFileSync('git', ['-C', resolve(root, repo), 'status', '--porcelain', '--untracked-files=no'], {encoding:'utf8'}).trim(), '');
}
const mod = (repo, path) => import(pathToFileURL(resolve(root, repo, path)).href);
const {createReadinessGraph, getTaskReadiness} = await mod('backlog', 'src/utils/readiness.ts');
const {createTaskRecordIndex} = await mod('backlog', 'src/utils/task-record-index.ts');
const {buildDependencyGraph, findCycleThroughRoot} = await mod('backlog', 'src/utils/dependency-graph.ts');
const {canonicalTaskId} = await mod('backlog', 'src/utils/task-id.ts');
const {isTerminalStatus} = await mod('backlog', 'src/utils/terminal-status.ts');
const {resultFrame, contentToText, parseLaunchArgs} = await mod('lite-harness', 'src/sdk/server/protocol.mjs');
const {Session} = await mod('lite-harness', 'src/sdk/server/session.mjs');
const {createEventTransformer} = await mod('lite-harness', 'src/sdk/server/providers/codex/transformation.mjs');
const results = [];
async function probe(id, note, fn) { await fn(); results.push({id, note, result:'pass'}); }
const task = (id, deps=[], status='To Do', filePath=`/${id}.md`) => ({id,title:id,status,dependencies:deps,filePath});
await probe('B01', 'Missing dependency is unresolved and blocks readiness', () => {
  const a=task('TASK-1',['TASK-9']); const r=getTaskReadiness(a,createReadinessGraph({tasks:[a]}));
  assert.equal(r.isReady,false); assert.deepEqual(r.missingDependencies,['TASK-9']);
});
await probe('B02', 'Different files with canonical duplicate IDs remain ambiguous', () => {
  const i=createTaskRecordIndex({tasks:[task('TASK-01'), task('TASK-1')]});
  assert.equal(i.lookup('TASK-1'),'ambiguous');
});
await probe('B03', 'Same-file duplicate preserves completed-corpus evidence despite old status', () => {
  const b=task('TASK-2'); const a=task('TASK-1',['TASK-2']);
  const g=createReadinessGraph({tasks:[a,b],completedTasks:[b]});
  assert.equal(getTaskReadiness(a,g).isReady,true);
  assert.deepEqual(getTaskReadiness(b,g),{isReady:false,isBlocked:false,blockingDependencies:[],missingDependencies:[]});
});
await probe('B04', 'Mutual dependency produces an explicit root cycle', () => {
  const a=task('TASK-1',['TASK-2']), b=task('TASK-2',['TASK-1']);
  const g=buildDependencyGraph(a,{tasks:[a,b]});
  assert.ok(findCycleThroughRoot(g));
});
await probe('B05', 'Canonical identity retains integers above Number safe precision', () => {
  assert.notEqual(canonicalTaskId('TASK-9007199254740992'),canonicalTaskId('TASK-9007199254740993'));
});
await probe('B06', 'Configured last status is terminal, not a hardcoded Done label', () => {
  assert.equal(isTerminalStatus(' finished ',['Todo','Done','Finished']),true);
  assert.equal(isTerminalStatus('Done',['Todo','Done','Finished']),false);
});
await probe('L01', 'Result builder defaults to success, empty usage and zero cost', () => {
  const r=resultFrame({sessionId:'fixture'});
  assert.equal(r.subtype,'success'); assert.equal(r.total_cost_usd,0); assert.deepEqual(r.usage,{});
});
await probe('L02', 'Unknown launch flag is silently ignored; non-text content is absent from prompt text', () => {
  assert.equal(parseLaunchArgs(['--not-supported','yes']).agent,'claude');
  assert.equal(contentToText([{type:'image',source:{data:'fixture'}},{type:'text',text:'hello'}]),'hello');
});
await probe('L03', 'Fake runtime with no frames still gets an empty success result from Session', async () => {
  const provider={createRuntime:()=>({model:'fake',async *runTurn(){}})};
  const s=new Session({provider,model:'fake',permissionMode:'default',cwd:root,env:{},stderr:{write(){}}});
  const frames=[]; for await (const f of s.runTurn({prompt:'fixture',content:[]})) frames.push(f);
  assert.equal(frames.at(-1).subtype,'success'); assert.equal(frames.at(-1).result,'');
});
await probe('L04', 'Fake runtime exception gets an error result', async () => {
  const provider={createRuntime:()=>({model:'fake',async *runTurn(){throw new Error('fixture-failure');}})};
  const s=new Session({provider,model:'fake',env:{},stderr:{write(){}}});
  const frames=[]; for await (const f of s.runTurn({prompt:'fixture'})) frames.push(f);
  assert.equal(frames.at(-1).is_error,true);
});
await probe('L05', 'Codex text transformer ignores failed-turn and usage events', () => {
  const f=createEventTransformer(), ctx={sessionId:'fixture',model:'fake'};
  assert.deepEqual(f({type:'turn.failed',error:{message:'fixture'}},ctx),[]);
  assert.deepEqual(f({type:'turn.completed',usage:{input_tokens:10,output_tokens:2}},ctx),[]);
});
await probe('L06', 'Accumulated text yields only new suffix, completion yields complete text', () => {
  const f=createEventTransformer(), ctx={sessionId:'fixture',model:'fake'};
  const ev=(type,text)=>({type,item:{type:'agent_message',id:'a',text}});
  assert.equal(f(ev('item.updated','가'),ctx)[0].event.delta.text,'가');
  assert.equal(f(ev('item.updated','가나'),ctx)[0].event.delta.text,'나');
  assert.equal(f(ev('item.completed','가나'),ctx)[0].message.content[0].text,'가나');
});
console.log(JSON.stringify({observed_at:'2026-10-04',runtime:process.version,pins,limits:'Pure upstream functions and fake runtime only; no provider SDK invocation, no end-to-end agent run.',results},null,2));
