'use strict';
// Run the unmodified #102 fixture first. A source checkout lacks packaged out/;
// retain that setup limitation, then rerun all ten unchanged probe assertions
// with the syntax-only sweep restricted to bridge/ (no pretend packaged pass).
// Usage: node run-pr102-probes.cjs <probes.cjs> <source-root> <output-dir>
const fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert/strict'),crypto=require('crypto');
const [probeArg,sourceArg,outputArg]=process.argv.slice(2);assert(probeArg&&sourceArg&&outputArg);
const probe=path.resolve(probeArg),source=path.resolve(sourceArg),output=path.resolve(outputArg);fs.mkdirSync(output,{recursive:true});
const run=file=>cp.spawnSync(process.execPath,[file,source],{encoding:'utf8',windowsHide:true,timeout:10000});
const original=run(probe);fs.writeFileSync(path.join(output,'pr102-original-source-checkout.stderr.txt'),original.stderr||'');
const input=fs.readFileSync(probe,'utf8');
assert(input.includes("['bridge','out']"));
const adapted=input.replace("['bridge','out']","['bridge']").replace('Not the upstream suite, no models, no installs, no CLI or hook registration. VM used only on audited snippets, not a general security sandbox.','Source-checkout adaptation: ten probe assertions unchanged; syntax-only sweep covers bridge/ only, not packaged out/. Not the upstream suite; no models, installs, CLI or hook registration. VM used only on audited snippets, not a security sandbox.');
const adaptedFile=path.join(output,'pr102-source-only-probes.cjs');fs.writeFileSync(adaptedFile,adapted);
const current=run(adaptedFile);assert.equal(current.status,0,current.stderr);const result=JSON.parse(current.stdout);assert.equal(result.results.length,10);assert(result.results.every(x=>x.result==='pass'));
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const wrapper={observedAt:new Date().toISOString(),originalOnSourceCheckout:{exit:original.status,error:'ENOENT: source checkout has no out/ directory; original fixture requires unpacked extension. Six blob pins and all ten assertions preceded this error, but no successful whole-run claim.'},adaptation:{originalSha256:sha(input),adaptedSha256:sha(adapted),changes:['syntax sweep array changed from bridge/out to bridge only','limits string changed to disclose narrower syntax sweep'],probeAssertionsChanged:false},...result};
fs.writeFileSync(path.join(output,'pr102-current-verification.json'),JSON.stringify(wrapper,null,2)+'\n');console.log(JSON.stringify(wrapper,null,2));
