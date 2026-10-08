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
        source += (root / 'app/static/workflow.js').read_text(encoding='utf-8')
        source += (root / 'app/static/paging.js').read_text(encoding='utf-8')
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
const sourceName=(n,taken)=>{taken.add(n.toLowerCase()); return n;};   // index.html의 이름 규칙(여기 파일 이름은 이미 맞다)
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
// 일반 작업의 오케스트레이터는 팀원과 같은 카드여도 된다(분담만 제안, #135) — 서버와 같은 규칙
assert.ok(!boardWarnings({...emptyBoard(),general:["a"],orchestrator:["a"]},roster).join(" ").includes("같은 provider"));
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
assert.deepEqual(chosenModels({supervisor:["a"],isolated:[],orchestrator:[]}),{a:"m1"});   // 슈퍼바이저 칸만 쓰는 카드(PR #134 검토)
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
// 다듬기(카드 #130): 슈퍼바이저 칸은 CLI 한 장, 같은 회사 팀원은 막지 않고 알린다. 다듬기 모드는 그때만 고를 수 있다.
const sroster=[{pid:"a",label:"CLI A",provider:"p1",transport:"cli"},{pid:"z",label:"CLI Z",provider:"p2",transport:"cli"},
 {pid:"b",label:"앱 B",provider:"p3",transport:"manual"}];
const sboard={...emptyBoard(),supervisor:["a"],isolated:["a","z"],input_mode:"refine"};
let sw=boardWarnings(sboard,sroster).join(" ");
assert.ok(sw.includes("주의") && !sw.includes("같은 provider 두 장"), sw);
assert.ok(boardWarnings({...sboard,supervisor:["b"]},sroster).join(" ").includes("CLI 카드만"));
roleOptions={participants:sroster,live:false,behaviors:["ok"]}; state={tasks:[],runs:[],refinements:[]};
roleBoard={...emptyBoard(),isolated:["z"],supervisor:["a"]}; syncInputMode();
assert.equal(nodes.modeRefine.disabled,false);
roleBoard={...emptyBoard(),isolated:["z"],input_mode:"refine"}; syncInputMode();
assert.equal(nodes.modeRefine.disabled,true); assert.equal(roleBoard.input_mode,"original");   // 슈퍼바이저가 빠지면 원문으로
// 다듬기 패널: 진행 상태는 배지, 슈퍼바이저가 묻는 말은 따로 표시한 칸. 형식 실패는 승인할 수 없고 원문을 보인다.
roleBoard={...emptyBoard(),isolated:["z"],supervisor:["a"],input_mode:"refine"};
state.refinements=[{refine_id:"q1",original:"원문 질문",max_turns:3,supervisor:{label:"CLI A"},turns:[
  {turn:1,note:"",state:"accepted",reply:{refined:"다듬은 1",changes:["범위"],ask:"기한은?"}},
  {turn:2,note:"석 달",state:"rejected",status:"format_error",reason:"JSON 아님",raw:{text:"RAW_REPLY"}}]}];
refineCurrent="q1"; renderRefine(true);
assert.ok(nodes.refinePanel.kids.every(isNode));
const panel=nodes.refinePanel.kids.map(text).join(" ");
for (const piece of ["원문 질문","다듬은 1","범위","슈퍼바이저가 나에게 묻는 말","기한은?","형식 검사 실패","RAW_REPLY","내가 쓴 말: 석 달","(3/3차례)","원문으로 돌아가기"])
  assert.ok(panel.includes(piece), piece);
assert.equal(nodes.question.readOnly,true);   // 다듬기를 시작하면 원문을 고정한다
const approve=nodes.refinePanel.kids.flatMap(all).filter(x=>x.tag==="button"&&text(x)==="이 문장으로 승인");
assert.equal(approve.length,1);               // 받은 차례만 승인할 수 있다
approve[0].attrs.onclick(); assert.equal(refineApproved,1); assert.equal(nodes.question.value,"다듬은 1");
resetRefine(); assert.equal(nodes.question.value,"원문 질문"); assert.equal(refineCurrent,null);
const pair=text(refinementPair("내 원문","보낸 문장"));
assert.ok(pair.includes("원래 목표") && pair.includes("내 원문") && pair.includes("실제로 보낸 질문") && pair.includes("보낸 문장"));
state.refinements[0].turns[1].state="unknown"; taskSelected=null; taskPageSig=null; renderTaskPage();
assert.ok(nodes.mainCol.kids.map(text).join(" ").includes("끝났는지 모르는 다듬기 차례"));
// Codex 교차검토(PR #131): 원문 모드의 확인 화면에 null이, 원본 앱 전달문 목록이 배열째 글자로 들어가지 않는다
showInputPreview({mode:"isolated",run_id:"r",confirmation:"c",question:"질문",prompt:"전달문",sources:[],manual_packets:{"b":"옮길 전달문"},
  role_config:{isolated:[],orchestrator:null,supervisor:null},quorum_policy:"independent_only",min_independent:1,
  calls:{draft_cli:1,model_calls:0}},{});
assert.ok(nodes.inputPreview.kids.every(isNode), JSON.stringify(nodes.inputPreview.kids.filter(k=>!isNode(k))));
// 다음 단계 제안(카드 #133): 슈퍼바이저가 있는 공개된 격리 실행에만. 제안 내용은 따로 표시한 칸, 진행 상태는 배지.
const sup={pid:"a",label:"CLI A",transport:"cli",model:"m1"};
const prun=(proposals,extra={})=>({run_id:"r1",task_id:"t1",phase:"revealed",mode:"isolated",
  role_config:{supervisor:sup,orchestrator:null,isolated:[sup],general:[]},proposals,...extra});
assert.equal(proposalIsland(prun([],{role_config:{supervisor:null,isolated:[sup]}})),null);
assert.equal(proposalIsland(prun([],{phase:"drafting"})),null);
assert.equal(proposalIsland(prun([],{mode:"general"})),null);
const again={proposal_id:"p1",state:"accepted",reply:{next:"again",reason:"갈림",question:"다음 질문",open_points:["비용"]},used_by:null};
const stop={proposal_id:"p2",state:"accepted",reply:{next:"stop",reason:"같음",question:null,open_points:[]},used_by:null};
let pisle=proposalIsland(prun([again]));
assert.ok(all(pisle).every(x=>x.kids.every(k=>typeof k!=="object"||isNode(k))));
let ptext=text(pisle);
for (const piece of ["제안: 한 번 더","이유: 갈림","남은 쟁점: 비용","다음 질문","이 질문으로 새 실행 준비","(2/2)"]) assert.ok(ptext.includes(piece), piece);
ptext=text(proposalIsland(prun([again,stop])));
assert.ok(ptext.includes("제안: 여기서 끝") && ptext.includes("판단 완료를 누르세요") && !ptext.includes("(3/2)"));
assert.ok(!text(proposalIsland(prun([{...again,used_by:"r2"}]))).includes("이 질문으로 새 실행 준비"));
ptext=text(proposalIsland(prun([{proposal_id:"p3",state:"unknown"}])));
assert.ok(ptext.includes("종료 미확인") && ptext.includes("종료를 직접 확인했음") && !ptext.includes("제안 받기"));
ptext=text(proposalIsland(prun([{proposal_id:"p4",state:"rejected",status:"format_error",reason:"JSON 아님",raw:{text:"RAW_P"}}])));
assert.ok(ptext.includes("형식 검사 실패") && ptext.includes("RAW_P") && !ptext.includes("새 실행 준비"));
// 보낼 질문이 제안 그대로이고 원문 모드일 때만 제안에 묶는다
proposalLink={id:"p1",question:"다음 질문"}; roleBoard={...emptyBoard(),isolated:["a"],supervisor:["a"],input_mode:"original"};
nodes.question.value="다음 질문"; assert.deepEqual(proposalBody(),{proposal:{id:"p1"}});
nodes.question.value="내가 고친 질문"; assert.deepEqual(proposalBody(),{});
nodes.question.value="다음 질문"; roleBoard.input_mode="refine"; assert.deepEqual(proposalBody(),{});
proposalLink=null; roleBoard.input_mode="original";
// 결과 모으기(카드 #137): 모두 끝난 일반 실행에 오케스트레이터 모델이 있을 때만. 인용마다 원문 일치 배지, 사실 검증 안 함.
const orch={pid:"a",label:"CLI A",transport:"cli",model:"m1"};
const crun=(collations,extra={})=>({run_id:"g1",mode:"general",gate:{collected:true},role_config:{orchestrator:orch,general:[orch]},
  participants:[{pid:"a",label:"CLI A"},{pid:"z",label:"CLI Z"}],collations,...extra});
assert.equal(collationIsland(crun([],{role_config:{orchestrator:null}})),null);
assert.equal(collationIsland(crun([],{gate:{collected:false}})),null);
assert.equal(collationIsland(crun([],{mode:"isolated"})),null);
const gathered={collation_id:"c1",state:"accepted",labels:{T1:"a",T2:"z"},reply:{claims:[
  {statement:"둘 다 도입 찬성",support:"quoted",quotes:[{member:"T1",text:"찬성한다",source_check:"exact_match"},
    {member:"T2",text:"지어낸 말",source_check:"not_found"}]},
  {statement:"비용은 작다",support:"unsupported_addition",quotes:[]}],overlaps:["겹침 X"],gaps:["빈 곳 Y"],next:["다음 Z"],
  checks:{quotes:2,exact_matches:1,unsupported_additions:1}}};
const cisle=collationIsland(crun([gathered]));
assert.ok(all(cisle).every(x=>x.kids.every(k=>typeof k!=="object"||isNode(k))));
let ctext=text(cisle);
for (const piece of ["둘 다 도입 찬성","원문 일치","T1 CLI A","찬성한다","원문에 없음","T2 CLI Z","원문에 없는 추가 주장",
  "겹침 X","빈 곳 Y","다음 Z","사실 검증 안 함","(2/2)"]) assert.ok(ctext.includes(piece), piece);
// 글자 그대로 맞아도 너무 짧은 인용은 근거가 아니다 — 배지와 요약 줄에 그렇게 쓴다
ctext=text(collationIsland(crun([{...gathered,reply:{...gathered.reply,claims:[{statement:"짧은 근거",support:"unsupported_addition",
  quotes:[{member:"T1",text:"A",source_check:"exact_match",substantive:false}]}],checks:{quotes:1,exact_matches:1,short_matches:1,unsupported_additions:1}}}])));
assert.ok(ctext.includes("원문 일치 · 너무 짧아 근거 아님") && ctext.includes("원문 일치 1개(그중 너무 짧아 근거 아님 1개)"), ctext);
ctext=text(collationIsland(crun([gathered,gathered])));
assert.ok(!ctext.includes("(3/2)") && !ctext.includes("호출 1회"));
ctext=text(collationIsland(crun([{collation_id:"c2",state:"unknown",labels:{}}])));
assert.ok(ctext.includes("종료 미확인") && ctext.includes("종료를 직접 확인했음") && !ctext.includes("호출 1회"));
ctext=text(collationIsland(crun([{collation_id:"c3",state:"rejected",status:"format_error",reason:"JSON 아님",raw:{text:"RAW_C"},labels:{}}])));
assert.ok(ctext.includes("형식 검사 실패") && ctext.includes("RAW_C"));
assert.ok(!text(generalResults(crun([]))).includes("오케스트레이터는 나"));
// 교차검토(카드 #140): 공개된 격리 실행에서 받은 답이 둘 이상이고 CLI 팀원이 있을 때만 버튼. 판독 실패는 지적 없음이 아니다.
const vparts=[{pid:"a",label:"CLI A",transport:"cli",draft:"A 답"},{pid:"z",label:"CLI Z",transport:"cli",draft:"Z 답"},
  {pid:"m",label:"앱 M",transport:"manual",draft:"M 답"}];
const vrun=(round,extra={})=>({run_id:"v1",mode:"isolated",phase:"revealed",participants:vparts,cross_review:round,...extra});
assert.equal(crossReviewIsland(vrun(null,{phase:"drafting"})),null);
assert.equal(crossReviewIsland(vrun(null,{mode:"general"})),null);
assert.equal(crossReviewIsland(vrun(null,{participants:[vparts[0],{...vparts[1],draft:undefined}]})),null);
let vtext=text(crossReviewIsland(vrun(null)));
assert.ok(vtext.includes("호출 2회(검토자 2명)") && vtext.includes("독립 정족수에 세지 않습니다"), vtext);
const vreview=(state,extra={})=>({review_id:"r-"+state,state,status:null,reviewer:{pid:"a"},labels:{D1:"z",D2:"m"},
  targets:{D1:{pid:"z",fresh:true},D2:{pid:"m",fresh:true}},reply:null,...extra});
const vround={question:"비용을 따져라",coverage:{pairs:4,reviewed:2,missing:[{reviewer:"z",target:"a",reason:"earlier_reviewer_not_accepted"}]},
  reviews:[vreview("accepted",{reply:{findings:[{target:"D1",target_pid:"z",quote:"Z 답",kind:"counterexample",detail:"반례 설명",
    source_check:"exact_match",disposition:"qualified"},{target:"D2",target_pid:"m",quote:"없는 말",kind:"other",detail:"d",
    source_check:"not_found",disposition:"unresolved"}]}}),
    vreview("rejected",{reviewer:{pid:"z"},status:"format_error",reason:"JSON 아님",raw:{text:"RAW_V"}}),
    vreview("skipped",{reviewer:{pid:"z"},status:"cap_reached"}),vreview("unknown",{reviewer:{pid:"z"}}),
    vreview("accepted",{reviewer:{pid:"z"},reply:{findings:[]},targets:{D1:{pid:"a",fresh:false}},labels:{D1:"a"}})]};
const visle=crossReviewIsland(vrun(vround));
assert.ok(all(visle).every(x=>x.kids.every(k=>typeof k!=="object"||isNode(k))));
vtext=text(visle);
for (const piece of ["검토 질문: 비용을 따져라","검토한 관계 2/4","검토하지 않음: CLI Z → CLI A · 앞 검토자가 받지 못함","D1 = CLI Z",
  "D1 CLI Z · 반례","원문 일치","대상 원문에 없음","반례 설명","판독 실패","'지적 없음'이 아닙니다","RAW_V","호출 상한에 닿음",
  "종료를 직접 확인했음","지적 없음 — 검토자가 형식에 맞게","대상 답이 바뀌었습니다: D1"]) assert.ok(vtext.includes(piece), piece);
assert.ok(!vtext.includes("교차검토 받기"));   // 한 라운드
// 일반 팀원 교차검토(GR-1): 모음으로 닫힌 뒤에만, 바로 시작하지 않고 입력 확인부터. 대상의 맡은 일을 함께 보인다.
const gparts=[{pid:"a",label:"CLI A",transport:"cli",draft:"A 결과"},{pid:"z",label:"CLI Z",transport:"cli",draft:"Z 결과"}];
const grun=(round,extra={})=>({run_id:"g1",mode:"general",phase:"collected",gate:{collected:true},participants:gparts,cross_review:round,...extra});
assert.equal(crossReviewIsland(grun(null,{gate:{collected:false}})),null);
let gtext=text(crossReviewIsland(grun(null)));
assert.ok(gtext.includes("교차검토 입력 확인 · 호출 2회 예정") && gtext.includes("자료 본문은 보내지 않습니다") &&
  !gtext.includes("교차검토 받기"), gtext);
const ground={question:"분담 충돌",coverage:{pairs:2,reviewed:1,missing:[]},missing_members:[{pid:"x",task:"일 X"}],
  reviews:[vreview("accepted",{labels:{D1:"z"},targets:{D1:{pid:"z",fresh:true}},snapshot:{targets:{D1:{task:"B 보기"}}},
    reply:{findings:[]}})]};
gtext=text(crossReviewIsland(grun(ground)));
for (const piece of ["교차검토 · 일반 팀원, 독립 아님","D1 = CLI Z (맡은 일: B 보기)","결과가 없어 검토하지 않은 팀원: x — 일 X"])
  assert.ok(gtext.includes(piece), piece);
const pressed=all(visle).filter(x=>x.tag==="button"&&x.attrs["aria-pressed"]==="true").map(text);
assert.deepEqual(pressed,["받아들임","보류"]);
// 토큰 사용량(카드 #141): provider별로 나누고 더하지 않는다. 관측 안 됨·원본 앱·봉인 중·정가 추정(청구액 아님)을 글로 적는다.
assert.equal(usageIsland({usage:null}),null);
const uvalue={by_provider:{"claude-code":{calls:2,observed:1,unobserved:1,tokens:{input_tokens:1200,cache_read_input_tokens:800},
  list_price_estimate_usd:0.0125},codex:{calls:1,observed:1,unobserved:0,tokens:{input_tokens:300,cached_input_tokens:200},
  list_price_estimate_usd:null}},unobserved:{manual:1,no_usage_reported:1},sealed_runs:1};
const utext=text(usageIsland({usage:uvalue}));
for (const piece of ["Claude — 호출 2(관측 1, 관측 안 됨 1)","입력 1,200","캐시로 읽음 800","정가 추정 $0.0125(청구액 아님)",
  "Codex — 호출 1(관측 1)","캐시로 읽음 200","원본 앱 답 1건 — 사용량 관측 안 됨","봉인 중인 실행 1개는 공개 뒤에 더합니다"]) assert.ok(utext.includes(piece), piece);
assert.ok(!utext.includes("1,500") && !utext.includes("1500"));   // 회사끼리 더한 숫자가 없다
assert.ok(all(usageIsland({usage:uvalue})).every(x=>x.kids.every(k=>typeof k!=="object"||isNode(k))));
// 분담 제안(카드 #135): 오케스트레이터 칸에 CLI 카드가 있을 때만 버튼. 제안이 오면 팀원별 칸을 채우고,
// 같은 목표·팀원·자료로 보낼 때만 제안을 붙인다.
roleOptions={participants:sroster,live:false,behaviors:["ok"]};
picked=[{name:"a.md",size:3},{name:"b.md",size:3}]; assignDraft={}; resetSplit();
roleBoard={...emptyBoard(),general:["a","z"],orchestrator:["a"]}; nodes.question.value="목표"; state.splits=[];
renderAssignments();
let stext=nodes.assignments.kids.map(text).join(" ");
assert.ok(stext.includes("분담 제안 받기") && stext.includes("(1/2)"), stext);
const acceptedSplit={split_id:"s1",state:"accepted",goal:"목표",members:{M1:"a",M2:"z"},
  sources:[{name:"a.md"},{name:"b.md"}],orchestrator:{label:"CLI A"},
  reply:{assignments:{a:{task:"A 보기",sources:["a.md"]},z:{task:"B 보기",sources:["b.md"]}},reason:"자료마다 한 명"}};
// 제안을 받는 동안 같은 이름의 다른 파일로 바꿨으면 칸에 채우지도 실행에 붙이지도 않는다(Codex 교차검토, PR #136)
splitCurrent="s1"; splitInputs=splitSnapshot(); state.splits=[acceptedSplit];
const kept=picked; picked=[{name:"a.md",size:9},picked[1]]; assignDraft={a:{task:"내가 쓴 일",off:new Set()}};
renderAssignments();
assert.equal(assignDraft.a.task,"내가 쓴 일"); assert.equal(splitApplied,null);
assert.ok(nodes.assignments.kids.map(text).join(" ").includes("이 제안을 쓰지 않습니다"));
assert.deepEqual(splitBody(),{});
picked=kept; assignDraft={};
renderAssignments();
assert.ok(nodes.assignments.kids.every(isNode));
assert.equal(assignDraft.a.task,"A 보기"); assert.deepEqual([...assignDraft.a.off].map(f=>f.name),["b.md"]);
stext=nodes.assignments.kids.map(text).join(" ");
assert.ok(stext.includes("제안대로 채움") && stext.includes("나눈 이유: 자료마다 한 명"));
assert.deepEqual(splitBody(),{split:{id:"s1"}});
nodes.question.value="다른 목표"; assert.deepEqual(splitBody(),{});   // 목표를 바꾸면 내가 나눈 분담
nodes.question.value="목표"; picked=[picked[0]]; assert.deepEqual(splitBody(),{});   // 자료를 바꿔도
state.splits=[{...state.splits[0],state:"unknown"}]; picked=[{name:"a.md",size:3},{name:"b.md",size:3}]; renderAssignments();
stext=nodes.assignments.kids.map(text).join(" ");
assert.ok(stext.includes("종료 미확인") && stext.includes("종료를 직접 확인했음"));
roleBoard={...roleBoard,orchestrator:[]}; renderAssignments();
assert.ok(!nodes.assignments.kids.map(text).join(" ").includes("분담 제안 받기"));   // 오케스트레이터가 나면 버튼 없음
assert.ok(generalPreview({...gpreview,split:{as_proposed:false}}).map(text).join(" ").includes("내가 고쳤습니다"));
resetSplit(); state.splits=[]; picked=[]; roleBoard=emptyBoard(); assignDraft={};
const remembered = memoryPreview({memory:{enabled:true, task_id:"t", selection_scope:{eligible_runs:30, considered_runs:24,
  older_runs_not_considered:6, unselected_runs:21}, entries:[{run_id:"r",created_at:1,excerpt:"승인되지 않았다",
  excerpt_policy:"section-balanced-v2", truncated:true,source_sha256:"hash",selection:{overlap_terms:["승인"],
  matched_fields:["human_judgment","reviews"],recent_fallback:false},omissions:{reviews:{omitted_bytes:300}}}]}});
assert.ok(text(remembered).includes("판단 메모·검토 지적"));
assert.ok(text(remembered).includes("오래된 실행 6개"));
assert.ok(text(remembered).includes("검토 지적 300 bytes"));
assert.ok(text(remembered).includes("승인되지 않았다"));
assert.ok(!text(remembered).includes("전체 기록"));
const expandedRecall = memoryPreview({memory:{enabled:true, selection_scope:{scanned_runs:80, considered_runs:1,
  below_score_floor_runs:2, query_terms_omitted:3, unselected_runs:0}, entries:[{run_id:"a",created_at:1,excerpt:"본문 근거",
  selection:{overlap_terms:["etag"],matched_fields:["answers"],recent_fallback:false}}]}});
assert.ok(text(expandedRecall).includes("공개 이력 80개를 검색"));
assert.ok(text(expandedRecall).includes("공개 답"));
assert.ok(text(expandedRecall).includes("약한 표현 일치 2개"));
assert.ok(text(expandedRecall).includes("표현 3개를 제외"));
assert.ok(text(memoryPreview({memory:{enabled:true,entries:[{run_id:"old",created_at:1,excerpt:"옛 발췌"}]}}))
  .includes("선택 이유가 저장되기 전"));
// 두 번 눌러도 요청은 하나이고, 응답 전에 원문으로 돌아가면(창을 새로 연 것과 같다) 늦은 응답을 붙이지 않는다
let pending=[], apiCalls=0, apiHook=null;
function api(path, body) { if (apiHook) return apiHook(path, body); apiCalls++; return new Promise(resolve => pending.push(() => resolve({refine_id:"late"}))); }
async function refresh() { return true; }
(async () => {
  roleBoard={...emptyBoard(),isolated:["z"],supervisor:["a"],input_mode:"refine"}; state.refinements=[];
  resetRefine(); nodes.question.value="원문 A";
  const first=refineTurn(), second=refineTurn();
  assert.equal(apiCalls,1);
  resetRefine();
  pending.forEach(f => f()); await first; await second;
  assert.equal(refineCurrent,null); assert.equal(refineBusy,false);
  // 일반 교차검토 입력 확인(GR-1): 미리보기를 보인 뒤 같은 round_id·확인 값으로만 시작한다. 다른 창을 연 뒤 늦게 온
  // 미리보기는 붙이지 않는다.
  let frames=[], generation=0, sent=[];
  const keep=k => k.flat(Infinity).filter(x => x!==null && x!==false && x!==undefined);
  globalThis.catalogFrame=(title, body) => { generation++; frames.push(body);
    body.replaceChildren=(...k) => { body.kids=keep(k); }; body.append=(...k) => { body.kids.push(...keep(k)); }; };
  globalThis.catalogRequest={begin() { const mine=generation; return {current: () => mine===generation}; }};
  globalThis.closeCatalog=() => { generation++; };
  const manifest={round_id:"g"+"1".repeat(32),confirmation:"c".repeat(64),calls:2,input_bytes:120,question:"분담 충돌",
    missing:[],members:[{pid:"a",label:"CLI A",task:"A 보기",sources:[{name:"a.md"}],answer_sha256:"f".repeat(64)}],
    reviewers:[{pid:"a",label:"CLI A",input_bytes:60,prompt:"PROMPT_A"}]};
  apiHook=async (path, body) => { sent.push([path, body]); return path.endsWith("/preview") ? manifest : {review_ids:["v"]}; };
  await previewGeneralReview(grun(null), "분담 충돌");
  const shown=frames[0];
  const ptext=text(shown);
  for (const piece of ["PROMPT_A","CLI A에게 보낼 입력 · 60바이트","A 보기","이 입력으로 교차검토 받기 · 호출 2회","자료 본문과 자동 기억은 보내지 않고"])
    assert.ok(ptext.includes(piece), piece);
  const go=all(shown).find(x => x.tag==="button");
  await go.attrs.onclick();
  assert.deepEqual(sent.at(-1), ["/api/runs/g1/cross-review",{question:"분담 충돌",round_id:manifest.round_id,confirmation:manifest.confirmation}]);
  let release;
  apiHook=() => new Promise(resolve => { release=() => resolve(manifest); });
  const late=previewGeneralReview(grun(null), "분담 충돌");
  catalogFrame("다른 창", {});
  release(); await late;
  assert.ok(!text(frames[1]).includes("PROMPT_A"));
  apiHook=null;
})().catch(e => { console.error(e); process.exit(1); });
'''
        # 스크립트가 Windows 명령줄 길이 한도(약 32K자)를 넘으므로 표준 입력으로 준다.
        result = subprocess.run([shutil.which("node"), "-"], input=script, capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        # inline JS도 파싱한다. 실제 동작 함수는 위에서 외부 파일 원문 그대로 실행한다.
        inline = html[html.index('"use strict";'):html.rindex("</script>")]
        parsed = subprocess.run([shutil.which("node"), "--check"], input=inline, capture_output=True,
                                text=True, encoding="utf-8", timeout=15)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn('disabled value="refine"', html)
