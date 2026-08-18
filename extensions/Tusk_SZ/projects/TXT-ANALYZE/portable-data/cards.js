import { VENGEANCE_CARDS, VENGEANCE_DECK, VENGEANCE_IDS } from "./vengeance.js";
import { NEUTRON_CARDS, NEUTRON_DECK, NEUTRON_IDS } from "./neutron.js";

const card = (definition) => {
  const legacy = definition.classes ?? definition.cardClass ?? definition.className ?? definition.class
    ?? definition.affiliation ?? definition.tribe ?? definition.species ?? definition["所属"] ?? definition["種族"] ?? [];
  const classes = [...new Set((Array.isArray(legacy) ? legacy : String(legacy).split(/[\/／]/))
    .map((value) => String(value).trim()).filter(Boolean))];
  return Object.freeze({ ...definition, classes });
};

export const CARD_LIBRARY = Object.freeze({
  ...VENGEANCE_CARDS,
  ...NEUTRON_CARDS,
  "R-JUNKY": card({
    id: "R-JUNKY", name: "ジャンキー", category: "Ob", color: "赤", cost: 1, atk: 1, str: 1,
    text: "[QA] ターン終了時、このObが攻撃していたら破壊する。"
  }),
  "R-JUNK-PARTS": card({
    id: "R-JUNK-PARTS", name: "ジャンクパーツ", category: "Code", color: "赤", cost: 1,
    text: "マウントしたObを+1/+1する。"
  }),
  "R-KANEKO": card({
    id: "R-KANEKO", name: "サプライヤー・カネコ", category: "Ob", color: "赤", cost: 2, atk: 1, str: 1,
    text: "[ログイン] 「ジャンクパーツ」1枚にアクセスし、それをドラッグする。"
  }),
  "R-SAM": card({
    id: "R-SAM", name: "ジャンカー・サム", category: "Ob", color: "赤", cost: 2, atk: 2, str: 2,
    text: "[ログイン] このObがマウントしているなら手札のレッドパンクス1枚を捨て、カードを2枚引く。"
  }),
  "R-THIEF": card({
    id: "R-THIEF", name: "こそ泥", category: "Ob", color: "赤", cost: 2, atk: 2, str: 1,
    text: "[バックアップ]"
  }),
  "R-ATSUTO": card({
    id: "R-ATSUTO", name: "切込隊長 アツト", category: "Ob", color: "赤", cost: 2, atk: 3, str: 1,
    text: "[QA] これは可能であればObを攻撃する。"
  }),
  "R-LUCKY-SHOT": card({
    id: "R-LUCKY-SHOT", name: "グレンのラッキー☆ショット", category: "Sp", color: "赤", cost: 2,
    text: "相手のOb1体に3ダメージ。その後、自分エリアのカード1枚を破壊して相手ユーザーに2ダメージ。"
  }),
  "R-REPA-BEGIN": card({
    id: "R-REPA-BEGIN", name: "簡易合体レッパ・ビギニング", category: "Ob", color: "赤", cost: 5, atk: 3, str: 5,
    text: "[レイヤード:レッドパンクス1体以上+ジャンク1枚以上] [QA] 攻撃時、レイヤー1枚を破棄してゴミ箱からコスト計2以下を配置する。"
  }),
  "R-SOUNDMAN": card({
    id: "R-SOUNDMAN", name: "サウンドマン", category: "Ob", color: "赤", cost: 2, atk: 1, str: 1,
    text: "[ログイン] 仮想Ob『パンクス』1体を配置する。"
  }),
  "R-REPA-G": card({
    id: "R-REPA-G", name: "変形合体レッパオー・G", category: "Ob", color: "赤", cost: 7, atk: 5, str: 5,
    text: "[レイヤード] [QA] [ログイン] 相手フォートレスにXダメージ。XはこのObのレイヤー数。"
  }),
  "TOKEN-PUNKS": card({
    id: "TOKEN-PUNKS", name: "パンクス", category: "Ob", color: "赤", cost: 1, atk: 1, str: 2,
    text: "仮想Ob。効果なし。", token: true
  }),
  "Y-SHIELD-KNIGHT": card({
    id: "Y-SHIELD-KNIGHT", name: "大盾の騎士", category: "Ob", color: "黄", cost: 1, atk: 1, str: 1,
    text: "[セキュリティ] [ログイン] [OC+4] カードを2枚引く。+2/+2する。"
  }),
  "Y-HANAMORI": card({
    id: "Y-HANAMORI", name: "「華守り」", category: "Ob", color: "黄", cost: 3, atk: 1, str: 3,
    text: "[セキュリティ] [ログアウト] 「華守り」1体を手札からドラッグする。"
  }),
  "Y-GEORGE": card({
    id: "Y-GEORGE", name: "不屈の守り手 ジョージ", category: "Ob", color: "黄", cost: 2, atk: 2, str: 1,
    text: "[セキュリティ] [バックアップ]"
  }),
  "Y-LEO": card({
    id: "Y-LEO", name: "兵長 不殺のレオ", category: "Ob", color: "黄", cost: 3, atk: 3, str: 6,
    text: "[セキュリティ] このObがObとの戦闘で与えるダメージは0になる。"
  }),
  "Y-HIYOKE": card({
    id: "Y-HIYOKE", name: "「火除け」", category: "Ob", color: "黄", cost: 3, atk: 1, str: 5,
    text: "[レスポンス:3] [セキュリティ]"
  }),
  "Y-YASASISA": card({
    id: "Y-YASASISA", name: "「夜叉しさ」", category: "Ob", color: "黄", cost: 3, atk: 1, str: 1,
    text: "[セキュリティ] [ログイン] 自分のライフが相手より少ないなら、メモリ上限を+1する。"
  }),
  "Y-SHIELD-BASH": card({
    id: "Y-SHIELD-BASH", name: "シールドバッシュ", category: "Sp", color: "黄", cost: 2,
    text: "相手Ob1体にXダメージ。Xは自分エリアにある[セキュリティ]の数+1。"
  }),
  "Y-PRAYER": card({
    id: "Y-PRAYER", name: "祈る力", category: "Sp", color: "黄", cost: 2,
    text: "自分ライフを2回復し、カードを1枚引く。"
  }),
  "Y-ARCTURUS": card({
    id: "Y-ARCTURUS", name: "騎士団長 不敗のアークツルス", category: "Ob", color: "黄", cost: 7, atk: 4, str: 6,
    text: "[ログイン] 次のターン、相手のObすべては攻撃しなければならない。自分の[セキュリティ]が攻撃された時、相手ユーザーに2ダメージ。"
  }),
  "Y-HAHANAMORI": card({
    id: "Y-HAHANAMORI", name: "「破華守り」", category: "Ob", color: "黄", cost: 7, atk: 4, str: 8,
    text: "[コンタクト] 攻撃宣言時、自分の他のObを破壊してスタンバイできる。戦闘相手は次の開始時にスタンバイしない。"
  }),
  "T-CACHE-BACK": card({
    id: "T-CACHE-BACK", sourceId: "AISD-016", name: "キャッシュ・バック", category: "Script", color: null, cost: 1,
    text: "[if:自分Obが破壊された時] カードを2枚引く。"
  }),
  "T-CHAIN-EXPLOSION": card({
    id: "T-CHAIN-EXPLOSION", sourceId: "AISD-015", name: "連鎖爆発", category: "Script", color: "赤", cost: 3,
    text: "[レジデント] いずれかのユーザーが効果ダメージを受けた時、自分のメモリを1回復する。"
  }),
  "T-BACKDOOR": card({
    id: "T-BACKDOOR", sourceId: "AISD-007", name: "バックドア設置", category: "Script", color: "青", cost: 2,
    text: "[レジデント] 1ターンに1度、相手のカード実行時、相手エリアに『バグトークン』を1体生成し配置する。"
  }),
  "T-GATLING": card({
    id: "T-GATLING", sourceId: "AISD-011", name: "重装テロリスト “Gatling”", category: "Ob", color: "赤", cost: 4, atk: 3, str: 4,
    text: "[QA][レイヤード:お互いのエリアの『バグトークン』2体以上] 攻撃宣言時、レイヤーを1枚破棄して起動する。相手ユーザーに3ダメージ。"
  }),
  "T-BUG-TOKEN": card({
    id: "T-BUG-TOKEN", name: "バグトークン", category: "Ob", color: null, cost: 0, atk: 0, str: 1,
    text: "テスト用仮想Ob。", token: true
  }),
  "T-PLUGIN-TACKLE": card({
    id: "T-PLUGIN-TACKLE", sourceId: "STD-224", name: "亜空間タックル", category: "Plugin", color: null, cost: null,
    text: "これのインストール時、任意の数字を指定する。相手が実行し配置したカードに記載されたメモリが指定した数字だった場合、これとそのカードの両方を破壊する。"
  })
});

export const LAB_CARD_IDS = Object.freeze([
  ...Object.keys(CARD_LIBRARY),
]);

export { VENGEANCE_DECK, VENGEANCE_IDS, NEUTRON_DECK, NEUTRON_IDS };

export const RED_DECK = Object.freeze([
  ["R-JUNKY", 3], ["R-JUNK-PARTS", 3], ["R-KANEKO", 2], ["R-SAM", 2],
  ["R-THIEF", 2], ["R-ATSUTO", 2], ["R-LUCKY-SHOT", 2], ["R-REPA-BEGIN", 2],
  ["R-SOUNDMAN", 1], ["R-REPA-G", 1]
]);

export const YELLOW_DECK = Object.freeze([
  ["Y-SHIELD-KNIGHT", 3], ["Y-HANAMORI", 3], ["Y-GEORGE", 2], ["Y-LEO", 2],
  ["Y-HIYOKE", 2], ["Y-YASASISA", 2], ["Y-SHIELD-BASH", 2], ["Y-PRAYER", 2],
  ["Y-ARCTURUS", 1], ["Y-HAHANAMORI", 1]
]);

export const USERS = Object.freeze({
  player: Object.freeze({
    id: "DOORS-ZX-PLAYER", name: "Doors ZX", color: "赤", maxStr: 20, memory: 5,
    frontLimit: 5, backLimit: 5, incidents: [15, 11, 7, 3],
    ability: "ターボ・ブースト！：ゲーム中1度、次の自ターン開始までメモリ上限+2。"
  }),
  ai: Object.freeze({
    id: "DOORS-ZX-AI", name: "Doors ZX", color: "黄", maxStr: 20, memory: 5,
    frontLimit: 5, backLimit: 5, incidents: [15, 11, 7, 3],
    ability: "ターボ・ブースト！：ゲーム中1度、次の自ターン開始までメモリ上限+2。"
  })
});

export function expandDeck(recipe, owner) {
  let serial = 0;
  return recipe.flatMap(([cardId, count]) => Array.from({ length: count }, () => ({
    ...CARD_LIBRARY[cardId],
    uid: `${owner}-${cardId}-${++serial}`,
    owner,
    sleep: false,
    damage: 0,
    attackedThisTurn: false,
    summoningSick: true,
    mounted: [],
    tempAtk: 0,
    tempStr: 0,
    skipStandby: false
  })));
}

export function createToken(owner, serial) {
  return {
    ...CARD_LIBRARY["TOKEN-PUNKS"], uid: `${owner}-TOKEN-PUNKS-${serial}`, owner,
    sleep: false, damage: 0, attackedThisTurn: false, summoningSick: true,
    mounted: [], tempAtk: 0, tempStr: 0, skipStandby: false
  };
}

export function createCardInstance(cardId, owner, serial = 1) {
  return {
    ...CARD_LIBRARY[cardId], uid: `${owner}-${cardId}-lab-${serial}`, owner,
    sleep: false, damage: 0, attackedThisTurn: false, summoningSick: true,
    mounted: [], tempAtk: 0, tempStr: 0, skipStandby: false,
    faceDown: false, residentActive: false, layerRole: null
  };
}
