'use strict';
// Offline rerun of historical review fixtures; never invokes a real model CLI.
// Usage: node run-boundary-repros.cjs <codex-peek-source> <prior-review-work> <output-dir>
const fs = require('fs'), path = require('path'), cp = require('child_process'), assert = require('assert/strict'), crypto = require('crypto');
const [sourceArg, priorArg, outputArg] = process.argv.slice(2);
assert(sourceArg && priorArg && outputArg, '3 directory arguments required');
const source = path.resolve(sourceArg), prior = path.resolve(priorArg), output = path.resolve(outputArg);
fs.mkdirSync(output, {recursive:true});
const sourceSha = cp.spawnSync('git', ['-C', source, 'rev-parse', 'HEAD'], {encoding:'utf8', windowsHide:true});
assert.equal(sourceSha.status,0); assert.equal(sourceSha.stdout.trim(),'eb7cec1da0b13d2765eaab770c58d177024f423e');
const sha256 = b => crypto.createHash('sha256').update(b).digest('hex');
const original = fs.readFileSync(path.join(prior,'peek-engine-repro.cjs'),'utf8');
// Only storage/source locations differ from the historical fixture.
const fromBase = "const base = path.join(__dirname, 'peek-engine-sandbox-' + Date.now());";
const fromRepo = "const repo = path.join(__dirname, 'codex-peek');";
assert(original.includes(fromBase) && original.includes(fromRepo));
const sandbox = path.join(output,'engine-sandbox-' + Date.now());
const adapted = original.replace(fromBase,`const base = ${JSON.stringify(sandbox)};`).replace(fromRepo,`const repo = ${JSON.stringify(source)};`);
const adaptedFile = path.join(output,'engine-repro-current.cjs');
fs.writeFileSync(adaptedFile,adapted);
const guardFile = path.join(__dirname,'synthetic-process-guard.cjs');
const env = {...process.env, REVIEW_SOURCE_ROOT:source, REVIEW_OUTPUT_ROOT:output, REVIEW_ENGINE_FILE:adaptedFile, REVIEW_ENGINE_SANDBOX:sandbox, NODE_OPTIONS:'--require '+JSON.stringify(guardFile)};
const startedAt = new Date().toISOString();
const run = cp.spawnSync(process.execPath,[adaptedFile],{cwd:output,env,encoding:'utf8',windowsHide:true,timeout:60000,maxBuffer:1024*1024*8});
fs.writeFileSync(path.join(output,'engine-rerun.stdout.json'),run.stdout||'');
fs.writeFileSync(path.join(output,'engine-rerun.stderr.txt'),run.stderr||'');
assert.equal(run.status,0,run.stderr);
const engine = JSON.parse(run.stdout);
for (const r of engine.results) for (const event of [r.stop,r.before,r.after].filter(Boolean)) { assert.equal(event.exit,0); assert.equal(event.stderr,''); }
const by = id => engine.results.find(x=>x.case===id);
assert.equal(by('explicit-fail-answer').machine.effective,'fail');
assert.equal(by('explicit-fail-answer').stop.stdout,'');
assert.equal(by('non-git-modified-after-proof').after.stdout,'');
assert.equal(by('git-untracked-child-modified-after-proof').after.stdout,'');
assert.equal(by('git-untracked-child-modified-after-proof').directoryMtimeUnchanged,true);
assert.match(by('positive-control-git-tracked-modified-after-proof').after.stdout,/proof-stale/);
const full=by('full-ask-start-worker-provider-ask-wait-stop-fail');
assert.equal(full.jobState,'succeeded'); assert.equal(full.jobExit,0); assert.equal(full.waitExit,0); assert.equal(full.stop.stdout,''); assert.match(full.waitStdout,/Verdict: fail/);
assert.deepEqual(full.judgmentPending,[]);
// citation-check initializes fs/crypto only and reads the explicitly supplied fixture.
const CC=require(path.join(source,'bridge','citation-check.js'));
const citationRoot=path.join(output,'citation-fixture');fs.mkdirSync(citationRoot,{recursive:true});
fs.writeFileSync(path.join(citationRoot,'math.js'),'function add(a,b) { return a+b; }\n');
const cc=CC.citationCheck({findings:[{id:'finding1',file:'math.js',line:1,detail:'`add` encrypts data permanently for every input.'}],roots:[citationRoot],resolvePath:p=>path.join(citationRoot,p),parsedOk:true});
const empty=CC.citationCheck({findings:[],roots:[citationRoot],parsedOk:true});
const citation={falseSemanticClaim:cc.items[0].kind,clearedByEmptyParsedFindings:CC.resolvedByNext({items:[{findingId:'finding1'}]},empty)};
assert.equal(citation.falseSemanticClaim,'ok');assert.equal(citation.clearedByEmptyParsedFindings,'recheck-clean');
const result={startedAt,finishedAt:new Date().toISOString(),upstream:sourceSha.stdout.trim(),node:process.version,engineCases:engine.results.length,engine:engine.results.map(r=>({case:r.case,stop:r.stop||r.after,machineEffective:r.machine&&r.machine.effective,proofStatus:r.proof&&r.proof.status,judgmentPending:r.judgmentPending,jobState:r.jobState,jobExit:r.jobExit,waitExit:r.waitExit,waitContainsFailVerdict:typeof r.waitStdout==='string'?/Verdict: fail/.test(r.waitStdout):undefined,gitStatus:r.gitStatus,directoryMtimeUnchanged:r.directoryMtimeUnchanged})),citation,adaptation:{originalSha256:sha256(original),adaptedSha256:sha256(adapted),changes:['source path is supplied by argument','sandbox created under output directory','inherited preload restricts filesystem, subprocesses, and network modules; no product source changes'],fixtureEnvironment:'Historical fixture redirects bridge/Codex/Claude paths in its child Node process only; no parent environment or installed configuration is changed.'},limits:['Fake provider output; no real model evaluation','C-C lifecycle/core profile/no approval envelope','Freshness fixture uses real proof/receipt writers and hooks; full-fail additionally runs ask-start/worker/ask/ask-wait','Preload is defense in depth for audited code, not an OS security sandbox']};
fs.writeFileSync(path.join(output,'current-verification.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
