'use strict';
// Defense in depth for these inspected fixtures, not a general-purpose sandbox.
const fs=require('fs'), path=require('path'), cp=require('child_process'), Module=require('module');
const source=path.resolve(process.env.REVIEW_SOURCE_ROOT), output=path.resolve(process.env.REVIEW_OUTPUT_ROOT), sandbox=path.resolve(process.env.REVIEW_ENGINE_SANDBOX);
const inRoot=(p,r)=>{const q=path.resolve(String(p)).toLowerCase(),k=r.toLowerCase();return q===k||q.startsWith(k+path.sep);};
const read=p=>{if(typeof p==='number')return;if(!(inRoot(p,source)||inRoot(p,output)))throw Error('fixture read outside approved roots: '+p);};
const write=p=>{if(typeof p==='number')return;if(!inRoot(p,output))throw Error('fixture write outside output: '+p);};
for(const name of ['readFileSync','readdirSync','statSync','lstatSync','accessSync','existsSync']){const f=fs[name];fs[name]=function(p,...a){read(p);return f.call(this,p,...a);};}
const real=fs.realpathSync;fs.realpathSync=function(p,...a){read(p);return real.call(this,p,...a);};fs.realpathSync.native=function(p,...a){read(p);return real.native.call(this,p,...a);};
for(const name of ['writeFileSync','appendFileSync','mkdirSync','unlinkSync','rmSync','rmdirSync','utimesSync','chmodSync']){const f=fs[name];fs[name]=function(p,...a){write(p);return f.call(this,p,...a);};}
const rename=fs.renameSync;fs.renameSync=function(a,b){write(a);write(b);return rename.call(this,a,b);};
const copy=fs.copyFileSync;fs.copyFileSync=function(a,b,...rest){read(a);write(b);return copy.call(this,a,b,...rest);};
const open=fs.openSync;fs.openSync=function(p,flag,...a){if(flag==='r')read(p);else write(p);return open.call(this,p,flag,...a);};
function approve(file,args,opts){
  if(opts && opts.shell)throw Error('fixture shell forbidden');
  if(path.resolve(file).toLowerCase()===process.execPath.toLowerCase()){
    if(!args||!args[0]||!(inRoot(args[0],source)||inRoot(args[0],output)))throw Error('unapproved Node entry point');
    return;
  }
  if(file==='git'){
    const ci=args.indexOf('-C');if(ci<0||!inRoot(args[ci+1],sandbox))throw Error('Git operation outside synthetic workspace');
    return;
  }
  throw Error('unapproved process: '+file);
}
for(const name of ['spawn','spawnSync']){const f=cp[name];cp[name]=function(file,args,opts){approve(file,args,opts);return f.call(this,file,args,opts);};}
for(const name of ['exec','execSync','execFile','execFileSync','fork'])cp[name]=function(){throw Error('fixture process API forbidden: '+name);};
const load=Module._load;Module._load=function(id,...rest){if(/^(?:node:)?(?:http|https|http2|net|tls|dgram|dns)$/.test(id))throw Error('fixture network forbidden');return load.call(this,id,...rest);};
