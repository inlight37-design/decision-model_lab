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
const isNode = x => x !== null && typeof x === "object" && !Array.isArray(x) && "tag" in x;
// 실제 DOM처럼 노드가 아닌 인자(null·배열)는 글자로 바꿔 넣는다. 걸러 주는 것은 h()뿐이다.
const $ = id => nodes[id] ||= {hidden:false, textContent:"", replaceChildren(...kids) {this.kids=kids.map(k => isNode(k) ? k : String(k));},
  setAttribute(k,v) {this[k]=v;}, focus() {this.focused=true;}};
function h(tag,attrs,...kids) {return {tag,attrs:attrs||{},kids:kids.flat(Infinity).filter(x=>x!==null && x!==false && x!==undefined)};}
const pressAll=()=>{}, updateSourceNote=()=>{}, fmtSize=n=>String(n), fmtTime=n=>String(n);
const badge=text=>h("span",{},text), island=(title,kids)=>h("section",{},title,kids);
const BEHAVIOR_LABEL={ok:"정상"};
const text = node => typeof node==="object" ? (node.kids||[]).map(text).join(" ") : String(node);
const all = node => typeof node==="object" ? [node,...(node.kids||[]).flatMap(all)] : [];
let state, selected, listSig, runSig, liveMode=false, picked=[];
const collapsible=(id,head,kids)=>h("div",{id},head,kids);
''' + source + r'''
const roster=[{pid:"a",label:"CLI A",provider:"p1",transport:"cli"},
 {pid:"b",label:"앱 B",provider:"p2",transport:"manual"}, {pid:"c",label:"같은 회사",provider:"p1",transport:"manual"}];
const original=emptyBoard(), placed=placeRole(original,"a","isolated");
assert.deepEqual(original.isolated,[]); assert.deepEqual(placed.isolated,["a"]);
assert.deepEqual(placeRole(placed,"a","isolated").isolated,["a"]);
assert.equal(boardWarnings(placed,roster).length,0);
assert.ok(boardWarnings(placeRole(placed,"c","orchestrator"),roster).join(" ").includes("같은 provider"));
assert.ok(boardWarnings(placeRole(placed,"b","general"),roster).join(" ").includes("CLI 카드만"));
assert.ok(boardWarnings(placeRole(placed,"a","general"),roster).join(" ").includes("함께 쓰지 않습니다"));
assert.equal(boardWarnings(placeRole(emptyBoard(),"a","general"),roster).length,0);
assert.ok(boardWarnings(emptyBoard(),roster).join(" ").includes("한 명 이상"));
roleOptions={participants:roster,live:false,behaviors:["ok"]}; roleBoard=emptyBoard();
// 모델 고르기(카드 #119): 허용 목록만 보이고, 막힌 모델은 고를 수 없게 두고 이유를 붙인다. 기본은 명단의 모델.
const listed={a:[{model:"m1",funding:"included",basis:"관측",usable:true},{model:"m2",funding:"credits",basis:"문서",usable:false}]};
const pickModel=all(roleCard({...roster[0],model:"m1"},{...roleOptions,model_choices:listed})).find(x=>x.attrs.id==="m-a");
assert.deepEqual(pickModel.kids.map(o=>[o.attrs.value,o.attrs.disabled,o.attrs.selected]),[["m1",false,true],["m2",true,false]]);
assert.ok(text(pickModel).includes("추가 크레딧"));
assert.ok(!all(roleCard(roster[1],{...roleOptions,model_choices:listed})).some(x=>x.tag==="select"));   // 원본 앱은 고를 모델이 없다
nodes["m-a"]={value:"m1"};
assert.deepEqual(chosenModels({isolated:["a"],orchestrator:[]}),{a:"m1"});
assert.ok(roleSummary({isolated:[{label:"CLI A",transport:"cli",model:"m1"}]}).includes("CLI A(m1)"));
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
// 경로와 작업 목록에는 노드만 들어간다 — 홈에서 "홈 nullnull", 목록에서 "[object HTMLButtonElement]"가 보였다.
const onlyNodes = id => nodes[id].kids.every(isNode);
for (const [tasks, pickTask, pickRun, tabs, list] of [[[task], null, null, 1, 2], [[task], "t", "r", 3, 2], [[], null, null, 1, 2]]) {
  state={tasks,runs:[]}; taskSelected=pickTask; selected=pickRun; listSig=null; renderTaskNavigation();
  assert.ok(onlyNodes("runTabs") && onlyNodes("runListIsland"), JSON.stringify([nodes.runTabs.kids, nodes.runListIsland.kids]));
  assert.equal(nodes.runTabs.kids.length, tabs); assert.equal(nodes.runListIsland.kids.length, list);
}
const compared=humanComparison({participants:[{label:"A",draft:"원문 그대로",independence:"unverified"}]});
assert.ok(text(compared).includes("원문 그대로") && text(compared).includes("독립 미확인"));
assert.equal(all(compared).filter(x=>x.tag==="button").length,0);
// 일반 팀원(카드 #125): 팀원마다 맡길 일·받을 자료를 고르고, 자료는 처음에 모두 받는 것으로 시작한다.
const fileA={name:"a.md",size:3}, fileB={name:"b.md",size:3};
picked=[fileA,fileB]; assignDraft={}; roleBoard={...emptyBoard(),general:["a"]}; renderRoleBoard();
assert.equal(nodes.assignments.hidden,false); assert.equal(nodes.advanced.hidden,true);
assert.equal(nodes.sourcesLabelText.textContent,"자료 · 팀원마다 고름");
assert.ok(nodes.assignments.kids.every(isNode));
const field=nodes.assignments.kids.flatMap(all);
assert.ok(field.some(x=>x.attrs.id==="task-a") && field.some(x=>x.attrs.id==="src-a-1"));
assert.equal(field.find(x=>x.attrs.id==="src-a-0").checked,true);
field.find(x=>x.attrs.id==="task-a").attrs.oninput({target:{value:"A만 읽기"}});
field.find(x=>x.attrs.id==="src-a-1").attrs.onchange({target:{checked:false}});
let built=buildAssignments(["a"],picked,[{name:"a.md"},{name:"b.md"}],assignDraft);
assert.deepEqual(built.assignments,{a:{task:"A만 읽기",sources:["a.md"]}});
assert.deepEqual(built.unused,["b.md"]); assert.deepEqual(built.missing,[]);
assert.deepEqual(buildAssignments(["a","x"],[],[],assignDraft).missing,["x"]);
roleBoard=emptyBoard(); renderRoleBoard();
assert.equal(nodes.assignments.hidden,true); assert.equal(nodes.advanced.hidden,false);
// 확인 화면은 팀원마다 보낼 입력 전문과 자료 목록을 그대로 보인다.
const gspec={pid:"a",label:"CLI A",transport:"cli",model:"m1"};
const gpreview={mode:"general",question:"전체 목표",calls:{draft_cli:1,model_calls:0},role_config:{general:[gspec],isolated:[]},
 assignments:{a:{task:"A만 읽기",prompt:"PROMPT_FULL_TEXT",input_sha256:"f".repeat(64),input_bytes:9,
  sources:[{name:"a.md",bytes:3,sha256:"e".repeat(64),kind:"original",range:"whole"}]}}};
const shownNodes=generalPreview(gpreview);
assert.ok(shownNodes.every(isNode));   // replaceChildren에 펼쳐 넣는다 — 배열이 섞이면 글자로 들어간다
const shown=shownNodes.map(text).join(" ");
assert.ok(nodes.assignments.kids===undefined || nodes.assignments.kids.every(isNode));
for (const piece of ["전체 목표","A만 읽기","PROMPT_FULL_TEXT","a.md","원문 파일 전체","CLI A(m1)","봉인·독립·정족수 판정은 하지 않습니다"])
  assert.ok(shown.includes(piece), piece);
// 결과 모음: 받은 답은 바로 보이고, 독립·정족수 라벨이 없다. 실패는 이유와 함께 빈자리로 보인다.
const results=text(generalResults({gate:{collected:false},participants:[
  {pid:"a",label:"CLI A",state:"accepted",draft:"받은 답 원문",independence:"not_applicable",assignment:{task:"A만 읽기"}},
  {pid:"b",label:"CLI B",state:"rejected",status:"cli_error",detail:null,independence:"not_applicable",assignment:{task:"B"}},
  {pid:"c",label:"CLI C",state:"running",independence:"not_applicable"}]}));
assert.ok(results.includes("받은 답 원문") && results.includes("A만 읽기") && results.includes("결과 없음 · cli_error"));
assert.ok(results.includes("작업 중입니다"));
assert.ok(!results.includes("독립") && !results.includes("정족수"));
assert.ok(roleSummary({supervisor:null,orchestrator:null,isolated:[],general:[gspec]}).includes("일반 CLI A(m1)"));
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
