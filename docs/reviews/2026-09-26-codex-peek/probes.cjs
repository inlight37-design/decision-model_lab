'use strict';
// 고정 배포물의 소스를 읽는 오프라인 검토. 설치/CLI/네트워크를 호출하지 않는다.
const fs = require('fs'), path = require('path'), vm = require('vm'), crypto = require('crypto'), assert = require('assert/strict');
const root = path.resolve(process.argv[2] || '');
if (!process.argv[2]) throw new Error('usage: node probes.cjs <unpacked-extension-root>');
const pins = {
 'bridge/codex-guard.js':'0365afaa7a31154bf6c1b338b20998f75cd32e16',
 'bridge/rules-flow.js':'49fd145e85def9b7f6eb07acd901b0217b13f5b5',
 'bridge/map-provenance.js':'13cc5a8ff420a7c6a2ac3fe9855125a17df1483a',
 'bridge/map-retrieval.js':'8e22c521f006b04e78efc9594ce7f7a18ad10d61',
 'bridge/contract-lib.js':'a08a1972d2ca3d94d31437c492eb7658912d3cb6',
 'bridge/codex-bridge.js':'481801fa92fda2b7422b49d83656187c9184adc2'
};
function read(p) { const b=fs.readFileSync(path.join(root,p)); const sha=crypto.createHash('sha1').update(Buffer.from(`blob ${b.length}\0`)).update(b).digest('hex'); assert.equal(sha,pins[p],`source changed: ${p}`); return b.toString('utf8'); }
const hashes={};for(const p of Object.keys(pins)){read(p);hashes[p]=pins[p];}
const results=[];
function test(id,fn){const detail=fn();results.push({id,result:'pass',...detail});}
// 이 VM은 일반 보안 격리기가 아니다. 읽고 확인한 순수 함수만 실행하며 실행기 모듈을 넘기지 않는다.
function pure(source) { const box={module:{exports:{}},require(n){ if(n==='path')return path; throw new Error('unapproved module: '+n); }};vm.runInNewContext(source,box,{timeout:1500});return box.module.exports; }
const flow=pure(read('bridge/rules-flow.js')), retrieval=pure(read('bridge/map-retrieval.js'));
const pr=read('bridge/map-provenance.js');
const reduce=pure(pr.slice(pr.indexOf('function reduceAutoCandidates('),pr.indexOf('// 등재(수확 공용 꼬리)'))+'\nmodule.exports={reduceAutoCandidates,reduceAutoEntries};');
const cl=read('bridge/contract-lib.js');
function hook(input){let data,end,code=null;const done={};const box={require(n){assert.equal(n,'./contract-lib.js');return {BRIDGE:'/synthetic/codex-bridge.js',loadLang:()=> 'en'};},process:{stdin:{setEncoding(){},on(ev,cb){if(ev==='data')data=cb;if(ev==='end')end=cb;}},stderr:{write(){}},exit(n){code=n;throw done;}}};vm.runInNewContext(read('bridge/codex-guard.js'),box,{timeout:1500});data(typeof input==='string'?input:JSON.stringify(input));try{end();}catch(e){if(e!==done)throw e;}return code;}
test('P01-direct-guard-control',()=>{const exit=hook({tool_input:{command:'codex exec synthetic-input'}});assert.equal(exit,2);return{exit};});
test('P02-marker-is-not-confinement',()=>{const exit=hook({tool_input:{command:'echo codex-bridge; codex exec synthetic-input'}});assert.equal(exit,0);return{exit,interpretation:'lexical guard bypass reproduced; command was data only, never executed'};});
test('P03-malformed-hook-input',()=>{const exit=hook('{');assert.equal(exit,0);return{exit,interpretation:'fail-open parsing observed'};});
const rows=[{wsKey:'w',repoKey:'r',askId:'ask-real',selectedIds:['r1'],ts:'1'}, {wsKey:'w',repoKey:'r',askId:'ask-preview',purpose:'preview',selectedIds:['x','y'],ts:'2'}, {wsKey:'w',repoKey:'r',purpose:'curate',selectedIds:['z'],ts:'3'}, {wsKey:'w',repoKey:'other',askId:'ask-wrong-repo',selectedIds:['z'],ts:'4'}];
test('P04-actual-receipt-not-preview',()=>{const r=flow.lastSelectionOf(rows,'w','r');assert.equal(r.askId,'ask-real');assert.equal(r.selectedCount,1);return{receipt:r};});
test('P05-receipt-missing-scope',()=>{assert.equal(flow.lastSelectionOf(rows,'w',''),null);return{selection:null};});
const entries=[{kind:'entry',subjectKey:'s',gen:2,origin:{eventRef:'e2'},ts:'1'}, {kind:'entry',subjectKey:'s',gen:10,origin:{eventRef:'e10'},ts:'2'}];
test('P06-generation-order',()=>{assert.equal(reduce.reduceAutoEntries(entries)[0].gen,10);assert.equal(reduce.reduceAutoEntries([...entries].reverse())[0].gen,10);return{selectedGeneration:10};});
const tb={kind:'tombstone',subjectKey:'s',scope:'subject',tombstoneId:'t1'};
test('P07-revoke-and-reinstate',()=>{assert.equal(reduce.reduceAutoEntries([...entries,tb]).length,0);assert.equal(reduce.reduceAutoEntries([...entries,tb,{kind:'tombstone-retract',targetTombstoneId:'t1'}])[0].gen,10);return{suppressed:0,restoredGeneration:10};});
test('P08-no-irrelevant-padding',()=>{const r=retrieval.selectCandidates({cap:8,nodes:[{id:'n',paths:['a.js']} ]});assert.equal(r.fallback,true);assert.equal(r.selected.length,0);return{selected:0,fallback:true};});
const p={v:2,implementerSession:'s',workspace:'/repo',ts:'2026-09-26T00:00:00.000Z',codexSession:'v',exit:0,status:'success',answerChars:1,jobId:'ask-abcd-1234567890',turnId:'t',implementerRevision:1,headState:'git',headOid:'a'.repeat(40)};
// strictProofV2 uses one grammar helper; copy only this audited helper, no contract module initialization.
const jidStart=cl.indexOf('function askJobIdOk(');const jidEnd=cl.indexOf('\n',jidStart);
const proof2=pure(cl.slice(jidStart,jidEnd)+'\n'+cl.slice(cl.indexOf('function exactKeys('),cl.indexOf('const RECEIPT_V1_KEYS'))+'\nmodule.exports={strictProofV2};');
test('P09-proof-schema-control',()=>{const r=proof2.strictProofV2(p);assert.equal(r.ok,true,JSON.stringify(r));return r;});
test('P10-proof-missing-and-extra-keys',()=>{const p1={...p};delete p1.turnId;assert.equal(proof2.strictProofV2(p1).ok,false);assert.equal(proof2.strictProofV2({...p,unexpected:true}).ok,false);return{missingRejected:true,extraRejected:true};});
let parsed=0;for(const dir of ['bridge','out'])for(const name of fs.readdirSync(path.join(root,dir)))if(name.endsWith('.js')){new vm.Script(require('module').wrap(fs.readFileSync(path.join(root,dir,name),'utf8').replace(/^#![^\n]*\n/,'\n')),{filename:dir+'/'+name});parsed++;}
console.log(JSON.stringify({upstream:'eb7cec1da0b13d2765eaab770c58d177024f423e',node:process.version,sourceGitBlobs:hashes,syntaxOnlyFiles:parsed,results,limits:'Not the upstream suite, no models, no installs, no CLI or hook registration. VM used only on audited snippets, not a general security sandbox.'},null,2));
