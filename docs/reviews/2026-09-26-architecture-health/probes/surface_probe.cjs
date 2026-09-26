// Executes unchanged function bodies from product files against synthetic responses.
// No DOM, browser, network, account query, model, or persistent app state.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = process.argv[2];
const html = fs.readFileSync(path.join(root, 'app/static/index.html'), 'utf8');
const board = fs.readFileSync(path.join(root, 'app/static/role-board.js'), 'utf8');
const refresh = html.slice(html.indexOf('async function refresh()'), html.indexOf('async function loadOptions()'));
const confirmRun = board.slice(board.indexOf('async function confirmRun()'), board.indexOf('function closeNewRun()'));
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;}); return {promise,resolve,reject}; };
const base = () => ({state:{version:'old',runs:[]}, connection:'', settledSeen:null, render(){}, renderQuota(){}, renderHeader(){}, autoQuota(){}});
(async () => {
  const queue = [deferred(),deferred(),deferred(),deferred()], context=base();
  let calls=0; context.api=()=>queue[calls++].promise;
  vm.createContext(context); vm.runInContext(refresh,context);
  const old=context.refresh(), recent=context.refresh();
  queue[2].resolve({version:'new',runs:[]}); queue[3].resolve({}); await recent;
  const before=context.state.version;
  queue[0].resolve({version:'old',runs:[]}); queue[1].resolve({}); await old;
  const after=context.state.version;
  const context2=base();
  context2.api=url => url==='/api/state' ? Promise.resolve({version:'new',runs:[]}) : Promise.reject(new Error('quota endpoint unavailable'));
  vm.createContext(context2); vm.runInContext(refresh,context2); await context2.refresh();
  const nodes={}, context3=base();
  Object.assign(context3,{previewRequest:{run_id:'new-run'}, picked:[], renderPicked(){}, closed:false,navigated:false,
    $:id=>nodes[id]||=( {disabled:false,textContent:''}),
    closeNewRun(){context3.closed=true;context3.previewRequest=null;},
    navigateTask(){context3.navigated=true;},toast(){},
    api:url=>url==='/api/runs' ? Promise.resolve({run_id:'new-run'}) : url==='/api/state' ? Promise.reject(new Error('temporary state failure')) : Promise.resolve({})});
  vm.createContext(context3); vm.runInContext(refresh+'\n'+confirmRun,context3); await context3.confirmRun();
  assert.equal(before,'new'); assert.equal(after,'old');
  assert.equal(context2.state.version,'old'); assert.match(context2.connection,/quota/);
  assert.equal(context3.closed,true); assert.equal(context3.previewRequest,null); assert.equal(context3.navigated,false);
  assert.match(nodes.formErr.textContent,/task_id/);
  console.log(JSON.stringify({refresh_out_of_order:{requests:calls,state_before_old_response:before,state_after_old_response:after},
    optional_quota_failure:{state:context2.state.version,connection:context2.connection},
    created_then_refresh_failure:{server_creation_succeeded:true,dialog_closed:context3.closed,preview_receipt_retained:context3.previewRequest!==null,navigated:context3.navigated,error_in_closed_dialog:nodes.formErr.textContent}},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
