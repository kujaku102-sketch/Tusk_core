import { endTurn, installCard, playCard, restSecurity } from "../game/engine.js";

const BASIC_STEPS = [
  {
    speaker: "ナビゲーター",
    text: "赤デッキを渡す。まずDoors ZXを起動してみる。『開始』を押して。",
    expect: { type: "advance" }
  },
  {
    speaker: "ナビゲーター",
    text: "赤カードを使うには赤シンボルが要る。手札の『こそ泥』を選び、レジストリへインストール。",
    expect: { type: "install", cardId: "R-THIEF" }
  },
  {
    speaker: "ナビゲーター",
    text: "メモリ1で『ジャンキー』をフロントへ実行。[QA]だから今すぐ殴れる。",
    expect: { type: "play", cardId: "R-JUNKY" }
  },
  {
    speaker: "ナビゲーター",
    text: "ジャンキーで相手のDoors ZXを攻撃。相手フロントに壁はいない。",
    expect: { type: "attack", cardId: "R-JUNKY", targetType: "fortress" }
  },
  {
    speaker: "ナビゲーター",
    text: "ターン終了。攻撃したジャンキーは終了時効果で自壊する。黄側の準備は自動で進める。",
    expect: { type: "end-turn" },
    after: "yellow-demo"
  },
  {
    speaker: "ナビゲーター",
    text: "黄側は『華守り』をスリープして[セキュリティ]を構えた。『サプライヤー・カネコ』をフロントへ実行して、アクセスしたジャンクパーツの配置先も選んで。Codeは単体で場に残る。",
    expect: { type: "play", cardId: "R-KANEKO", zone: "front" }
  },
  {
    speaker: "ナビゲーター",
    text: "QAも[コンタクト]もないカネコは、実行したターンには攻撃できない。ターンを終了して黄側を自動でパスさせる。",
    expect: { type: "end-turn" },
    after: "yellow-pass"
  },
  {
    speaker: "ナビゲーター",
    text: "次の自ターンになった。カネコで相手Doors ZXへ攻撃してみろ。対象はスリープ中のセキュリティへ変更される。",
    expect: { type: "attack", cardId: "R-KANEKO" }
  },
  {
    speaker: "ナビゲーター",
    text: "最後。『グレンのラッキー☆ショット』を華守りへ実行。3ダメージ後のダイアログで任意追加効果を選べる。使うなら自分エリアのカードも選択。",
    expect: { type: "play", cardId: "R-LUCKY-SHOT", targetCardId: "Y-HANAMORI" }
  },
  {
    speaker: "ナビゲーター",
    text: "ここまで。実行先選択、QA、セキュリティ、マウント、任意追加効果まで動いた。以降は自由操作。カードを選べば左の詳細欄からリログもできる。",
    expect: null
  }
];

const VENGEANCE_STEPS = [
  {
    speaker: "劇団ナビゲーター",
    text: "ヴェンジェンスはObの移動とレイヤードを使う。まず『開始』を押して盤面を確認。",
    expect: { type: "advance" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "紫カードの実行に紫シンボルが要る。手札の『淫魔像』をレジストリへインストール。",
    expect: { type: "install", cardId: "STD-191" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "『マーダードールズ=トライプビア』を選び、フロントへレイヤード。場の『ドールズ』2体を素材として選択する。",
    expect: { type: "layered", cardId: "STD-195", zone: "front" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "トライプビアを選び、バックへリログ。レイヤー1枚を破棄することで移動コストが1になり、移動後はスタンバイする。",
    expect: { type: "relog", cardId: "STD-195", zone: "back" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "次は『マーダードールズ=アクロィア』をフロントへ実行。",
    expect: { type: "play", cardId: "STD-194", zone: "front" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "『マーダードールズ=タナフォリア』をフロントへ実行。リログではなく、次にこのカードの効果でアクロィアを動かす。",
    expect: { type: "play", cardId: "STD-192", zone: "front" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "タナフォリアを選んで『効果起動』。[アップデート:2]を選び、対象にアクロィア、移動先にバックを指定。アクロィアの移動時効果と1ドローまで処理される。",
    expect: { type: "activate-effect", cardId: "STD-192", zone: "back" }
  },
  {
    speaker: "劇団ナビゲーター",
    text: "終了。ヴェンジェンスの基本は、生成したドールズを素材・移動元の穴埋め・攻撃役へ使い回すこと。以降は自由操作。",
    expect: null
  }
];

const tutorialSteps = (tutorialId) => tutorialId === "vengeance" ? VENGEANCE_STEPS : BASIC_STEPS;

export function createTutorialFlow(tutorialId = "basics") {
  return { tutorialId, index: 0, complete: false, error: "" };
}

export function currentTutorialStep(flow) {
  const steps = tutorialSteps(flow?.tutorialId);
  return steps[Math.min(flow.index, steps.length - 1)];
}

function matches(expect, action) {
  if (!expect) return true;
  return Object.entries(expect).every(([key, value]) => action[key] === value);
}

export function acceptTutorialAction(state, flow, action) {
  const steps = tutorialSteps(flow?.tutorialId);
  const step = currentTutorialStep(flow);
  if (!matches(step.expect, action)) {
    flow.error = "今はその操作じゃない。セリフのカードと行動を確認して。";
    return false;
  }
  flow.error = "";
  flow.index += 1;
  if (step.after === "yellow-demo") runYellowTutorialTurn(state);
  if (step.after === "yellow-pass" && state.active === "ai") {
    endTurn(state);
    const security = state.players.ai.front.find((card) => card.id === "Y-HANAMORI" && !card.sleep);
    if (security) restSecurity(state, "ai", security.uid);
    if (state.securityRestWindow === "ai") endTurn(state);
  }
  if (flow.index >= steps.length - 1) flow.complete = true;
  return true;
}

function runYellowTutorialTurn(state) {
  const ai = state.players.ai;
  const install = ai.hand.find((card) => card.id === "Y-SHIELD-KNIGHT");
  if (install) installCard(state, "ai", install.uid, { force: true });
  const hanamori = ai.hand.find((card) => card.id === "Y-HANAMORI");
  if (hanamori) {
    playCard(state, "ai", hanamori.uid, { force: true });
    endTurn(state);
    const fieldHanamori = ai.front.find((card) => card.id === "Y-HANAMORI");
    if (fieldHanamori) restSecurity(state, "ai", fieldHanamori.uid);
  } else endTurn(state);
  if (state.securityRestWindow === "ai") endTurn(state);
}

export function tutorialAdvanceAction() {
  return { type: "advance" };
}
