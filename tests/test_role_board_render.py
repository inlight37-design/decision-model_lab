"""카드 #99 화면의 실제 JS를 Node로 실행한다. 모델·네트워크 없음."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class RoleBoardRenderTests(unittest.TestCase):
    def test_placement_keyboard_buttons_human_roles_and_safe_task_cards(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "app/static/role-board.js").read_text(encoding="utf-8")
        html = (root / "app/static/index.html").read_text(encoding="utf-8")
        script = r'''
const assert = require("node:assert/strict");
const location = {search: ""};
const nodes = {};
const $ = id => nodes[id] ||= {hidden:false, textContent:"", replaceChildren(...kids) {this.kids=kids;},
  setAttribute(k,v) {this[k]=v;}, focus() {this.focused=true;}};
function h(tag,attrs,...kids) {return {tag,attrs:attrs||{},kids:kids.flat(Infinity).filter(x=>x!==null && x!==false && x!==undefined)};}
const pressAll=()=>{}, updateSourceNote=()=>{}, fmtSize=n=>String(n), fmtTime=n=>String(n);
const badge=text=>h("span",{},text), island=(title,kids)=>h("section",{},title,kids);
const BEHAVIOR_LABEL={ok:"정상"};
const text = node => typeof node==="object" ? (node.kids||[]).map(text).join(" ") : String(node);
const all = node => typeof node==="object" ? [node,...(node.kids||[]).flatMap(all)] : [];
let state, selected, listSig, runSig, liveMode=false;
''' + source + r'''
const roster=[{pid:"a",label:"CLI A",provider:"p1",transport:"cli"},
 {pid:"b",label:"앱 B",provider:"p2",transport:"manual"}, {pid:"c",label:"같은 회사",provider:"p1",transport:"manual"}];
const original=emptyBoard(), placed=placeRole(original,"a","isolated");
assert.deepEqual(original.isolated,[]); assert.deepEqual(placed.isolated,["a"]);
assert.deepEqual(placeRole(placed,"a","isolated").isolated,["a"]);
assert.equal(boardWarnings(placed,roster).length,0);
assert.ok(boardWarnings(placeRole(placed,"c","orchestrator"),roster).join(" ").includes("같은 provider"));
assert.ok(boardWarnings(placeRole(placed,"b","general"),roster).join(" ").includes("C 단계"));
roleOptions={participants:roster,live:false,behaviors:["ok"]}; roleBoard=emptyBoard();
const card=roleCard(roster[0],roleOptions);
const choose=all(card).find(x=>x.attrs.id==="card-a");
assert.equal(choose.tag,"button"); assert.equal(choose.attrs.type,"button");
assert.equal(choose.attrs.draggable,"true");
choose.attrs.onclick(); assert.equal(chosenCard,"a");
renderRoleBoard();
let target=nodes.roleSlots.kids.flatMap(all).find(x=>x.attrs.id==="slot-isolated");
assert.equal(target.tag,"button"); // native Enter/Space click semantics, no mouse-only div
target.attrs.onclick(); assert.deepEqual(roleBoard.isolated,["a"]);
target=nodes.roleSlots.kids.flatMap(all).find(x=>x.attrs.id==="slot-orchestrator");
let transferred;
choose.attrs.ondragstart({dataTransfer:{setData(k,v){transferred=[k,v];}}});
assert.deepEqual(transferred,["text/role-card","a"]);
target.attrs.ondrop({preventDefault(){},dataTransfer:{getData(){return "b";}}});
assert.deepEqual(roleBoard.orchestrator,["b"]);
assert.ok(nodes.roleWarnings.textContent.includes("CLI 합성자"));
const fixed={source:"board",supervisor:null,orchestrator:null,isolated:[roster[0]],general:[],input_mode:"original"};
assert.ok(roleSummary(fixed).includes("오케스트레이터 나"));
const task={task_id:"t",title:"<script>user title</script>",status:"my_turn",role_config:fixed,calls_used:1,
 runs:[{run_id:"r",question:"원문 질문",status:"my_turn",action:"원본 앱 답 붙여넣기",created_at:1,role_config:fixed,calls_used:1}]};
state={tasks:[task],runs:[{draft:"DO_NOT_READ_SEALED_DRAFT"}]};
renderTaskPage();
const home=nodes.mainCol.kids.map(text).join(" ");
assert.ok(home.includes("내 차례") && home.includes("모든 작업") && home.includes("쓴 CLI 호출 1"));
assert.ok(!home.includes("DO_NOT_READ_SEALED_DRAFT"));
taskSelected="t"; taskPageSig=null; renderTaskPage();
assert.ok(nodes.mainCol.kids.map(text).join(" ").includes("실행 타임라인"));
assert.ok(nodes.mainCol.kids.map(text).join(" ").includes("원본 앱 답 붙여넣기"));
assert.ok(!all(taskCard(task)).some(x=>"innerHTML" in x.attrs));
const compared=humanComparison({participants:[{label:"A",draft:"원문 그대로",independence:"unverified"}]});
assert.ok(text(compared).includes("원문 그대로") && text(compared).includes("독립 미확인"));
assert.equal(all(compared).filter(x=>x.tag==="button").length,0);
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        # inline JS도 파싱한다. 실제 동작 함수는 위에서 외부 파일 원문 그대로 실행한다.
        inline = html[html.index('"use strict";'):html.rindex("</script>")]
        parsed = subprocess.run([shutil.which("node"), "--check"], input=inline, capture_output=True,
                                text=True, encoding="utf-8", timeout=15)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn('disabled value="refine"', html)

