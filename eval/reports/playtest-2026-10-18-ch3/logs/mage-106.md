# mage / seed 106

> [GM] 静寂に包まれたアルテリア王城の王の間。重厚な扉が開かれ、あなたの足音が赤い絨毯に吸い込まれていく。王座に鎮座する国王エドワードは、深いため息をつきながらあなたを見据えた。「若き冒険者よ、我が国を脅かす邪竜イグニスを討ち果たしてくれ。報酬は約束しよう。今はまず、この支度金を受け取ってくれ」国王はそう言うと、手元に100ゴールドと薬草を置いた。
- クエスト更新：紅き邪竜の討伐
- 100ゴールドを獲得しました。
- 薬草 x1を入手しました。

## step 1 / castle 「アルテリア王城」 HP 12/12 G 100

- 国王に邪竜の詳しい話を聞く | 旅の目的と手がかりを確認できます | 判定不要
- 将軍ドラコに助言を求める | 実用的な戦術情報が得られるかもしれません | 筋力または耐久が10以上で1d20判定（DC15） [不可: 筋力10以上または耐久10以上が必要]
- 侍従から旅の支給品を受け取る | 教会から届いた聖水を受け取ります | 判定不要
- 城下町へ出る | 王城の門前に広がる城下町へ | 判定不要

選択: 城下町へ出る
> [プレイヤー] 城下町へ出る
- 現在地がアルテリア城下町になりました。

## step 2 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 魔法店へ向かう
> [プレイヤー] 魔法店へ向かう
> [GM] 薬草と古い紙の匂いが漂う店内で、青いローブの銀髪の魔法使いが顔を上げた。棚の小瓶が、窓からの光を受けて淡く瞬いている。「何かお探しかな」
- 現在地が城下町の魔法店になりました。

## step 3 / magic_shop 「城下町の魔法店」 HP 12/12 G 100

- 店に入る | 青のローブ魔法店 | 判定不要
- 邪竜についての噂を聞く | 魔法使いが知る不穏な噂 | 1d20+wis判定（DC14）
- パーティーへ招く | 同行者として迎える（2ラウンドごとにHPを回復） | 判定不要
- 城下町に戻る | 大通りへ戻る | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 最近変わったことは？ |  | 判定不要

選択: 邪竜についての噂を聞く
> [プレイヤー] 邪竜についての噂を聞く
> [GM] 青いローブの魔法使いは声を潜めた。「邪竜の復活は自然なものではない。誰かが意図して呼び戻した、と私は見ています」
- クエスト更新：凍てつく謎

## step 4 / magic_shop 「城下町の魔法店」 HP 12/12 G 100

- 店に入る | 青のローブ魔法店 | 判定不要
- 邪竜についての噂を聞く | 魔法使いが知る不穏な噂 | 1d20+wis判定（DC14） [不可: 完了済みです。]
- パーティーへ招く | 同行者として迎える（2ラウンドごとにHPを回復） | 判定不要
- 城下町に戻る | 大通りへ戻る | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 最近変わったことは？ |  | 判定不要

選択: 城下町に戻る
> [プレイヤー] 城下町に戻る
- 現在地がアルテリア城下町になりました。

## step 5 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 道具屋へ向かう
> [プレイヤー] 道具屋へ向かう
> [GM] 扉の鈴が鳴ると、棚の陰から金髪の少女サラが顔を出した。肩の上では小さな火コウモリ竜が、ぱちぱちと火の粉を散らしている。「いらっしゃいませ！今日は何をお探しですか？」
- 現在地が城下町の道具屋になりました。

## step 6 / item_shop 「城下町の道具屋」 HP 12/12 G 100

- 店に入る | サラの道具屋 | 判定不要
- ペットの火コウモリ竜を借りる | 懐いてくれるか確かめる（毎ラウンド敵を焼き、HPを回復） | 1d20+wis判定（DC13）
- 城下町に戻る | 大通りへ戻る | 判定不要
- 何か困っていることはある？ |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 城下町に戻る
> [プレイヤー] 城下町に戻る
- 現在地がアルテリア城下町になりました。

## step 7 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 鍛冶屋へ向かう
> [プレイヤー] 鍛冶屋へ向かう
> [GM] 城下町の小さな鍛冶屋に足を踏み入れると、熱気と鉄を打つ音があなたを出迎えた。無骨だが腕の立つ鍛冶師ローベルトが、汗を拭いながらこちらを見ている。「武器の点検か？それとも新しい武具が要るのか？」
- 現在地が城下町の鍛冶屋になりました。

## step 8 / forge 「城下町の鍛冶屋」 HP 12/12 G 100

- 店に入る | ローベルト鍛冶店 | 判定不要
- 邪竜を討つ方法を聞く | 鍛冶師の知恵を借りる | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 城下町に戻る | 大通りへ戻る | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 浮かない顔をしているが？ |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 浮かない顔をしているが？
> [プレイヤー] 浮かない顔をしているが？
> [GM] 「……親父の形見のハンマーを、ゴブリンどもに盗まれた」
- クエスト更新：鍛冶師の形見

## step 9 / forge 「城下町の鍛冶屋」 HP 12/12 G 100

- 店に入る | ローベルト鍛冶店 | 判定不要
- 邪竜を討つ方法を聞く | 鍛冶師の知恵を借りる | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 城下町に戻る | 大通りへ戻る | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 浮かない顔をしているが？ |  | 判定不要 [不可: 完了済みです。]
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 邪竜を討つ方法を聞く
> [プレイヤー] 邪竜を討つ方法を聞く
> [GM] 鍛冶師ローベルトは手を止め、低い声で語り始めた。「通常の物理攻撃や炎は、あの邪竜イグニスには一切通用せん。だが、『氷の護符』の力を武器に纏わせれば、自身の攻撃を氷属性に変換できる。それなら奴にも傷を負わせられるはずだ」

## step 10 / forge 「城下町の鍛冶屋」 HP 12/12 G 100

- 店に入る | ローベルト鍛冶店 | 判定不要
- 邪竜を討つ方法を聞く | 鍛冶師の知恵を借りる | 判定不要 [不可: 完了済みです。]
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 城下町に戻る | 大通りへ戻る | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
- 浮かない顔をしているが？ |  | 判定不要 [不可: 完了済みです。]
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 城下町に戻る
> [プレイヤー] 城下町に戻る
- 現在地がアルテリア城下町になりました。

## step 11 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 路地裏へ向かう
> [プレイヤー] 路地裏へ向かう
> [GM] 昼の路地裏はひっそりとして、干された洗濯物が風に揺れているだけだ。奥へ進む理由も見当たらない。
- 現在地が城下町の路地裏・昼になりました。

## step 12 / alley 「城下町の路地裏・昼」 HP 12/12 G 100

- 城下町に戻る | 大通りへ戻る | 判定不要

選択: 城下町に戻る
> [プレイヤー] 城下町に戻る
- 現在地がアルテリア城下町になりました。

## step 13 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 王城へ戻る
> [プレイヤー] 王城へ戻る
- 現在地がアルテリア王城になりました。

## step 14 / castle 「アルテリア王城」 HP 12/12 G 100

- 国王に邪竜の詳しい話を聞く | 旅の目的と手がかりを確認できます | 判定不要
- 将軍ドラコに助言を求める | 実用的な戦術情報が得られるかもしれません | 筋力または耐久が10以上で1d20判定（DC15） [不可: 筋力10以上または耐久10以上が必要]
- 侍従から旅の支給品を受け取る | 教会から届いた聖水を受け取ります | 判定不要
- 城下町へ出る | 王城の門前に広がる城下町へ | 判定不要

選択: 国王に邪竜の詳しい話を聞く
> [プレイヤー] 国王に邪竜の詳しい話を聞く
> [GM] 「イグニスは炎を操る恐ろしい竜だ」と国王は杖を強く握りしめる。「だが、竜の谷の古文書によれば、奴は冷気を帯びた攻撃を極端に嫌うそうだ。氷の魔力を持つ武器か、その性質を突く工夫が必要になるだろう」。その言葉には、かつて多くの騎士たちが挑み、そして散った無念が滲んでいる。

## step 15 / castle 「アルテリア王城」 HP 12/12 G 100

- 国王に邪竜の詳しい話を聞く | 旅の目的と手がかりを確認できます | 判定不要 [不可: 完了済みです。]
- 将軍ドラコに助言を求める | 実用的な戦術情報が得られるかもしれません | 筋力または耐久が10以上で1d20判定（DC15） [不可: 筋力10以上または耐久10以上が必要]
- 侍従から旅の支給品を受け取る | 教会から届いた聖水を受け取ります | 判定不要
- 城下町へ出る | 王城の門前に広がる城下町へ | 判定不要

選択: 侍従から旅の支給品を受け取る
> [プレイヤー] 侍従から旅の支給品を受け取る
> [GM] 侍従が小箱を差し出した。「教会より、邪竜討伐に向かわれる方へ」中には清められた聖水が二本収められている。
- 聖水 x2を入手しました。

## step 16 / castle 「アルテリア王城」 HP 12/12 G 100

- 国王に邪竜の詳しい話を聞く | 旅の目的と手がかりを確認できます | 判定不要 [不可: 完了済みです。]
- 将軍ドラコに助言を求める | 実用的な戦術情報が得られるかもしれません | 筋力または耐久が10以上で1d20判定（DC15） [不可: 筋力10以上または耐久10以上が必要]
- 侍従から旅の支給品を受け取る | 教会から届いた聖水を受け取ります | 判定不要 [不可: 完了済みです。]
- 城下町へ出る | 王城の門前に広がる城下町へ | 判定不要

選択: 城下町へ出る
> [プレイヤー] 城下町へ出る
- 現在地がアルテリア城下町になりました。

## step 17 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 宿屋へ向かう
> [プレイヤー] 宿屋へ向かう
> [GM] 宿屋の扉を開けると、温かい食事の匂いと和やかな喧噪が包み込んできた。カウンターの奥では店主のイアンがグラスを磨いており、隅の席では闇の森を拠点とする女レンジャーのロビンがくつろいでいる。「いらっしゃい、休んでいくかい？」とイアンが声をかけてきた。
- 現在地が城下町の宿屋になりました。

## step 18 / inn 「城下町の宿屋」 HP 12/12 G 100

- 宿で休む（10G） | 温かい食事と寝台で疲れを癒す | 判定不要
- イアンと会話する | 宿屋の店主と話す | 判定不要
  - 強力な氷属性武器の伝説について聞く | 伝説の武器の情報を得る | 1d20判定（DC3）
  - 邪竜を倒すアドバイスを求める | イアンの意見を聞く | 判定不要
  - 竜と人の昔話を聞く |  | 判定不要
- ロビンと会話する | 女レンジャーと話す | 判定不要
  - パーティに勧誘する | ロビンを仲間に誘う（毎ラウンド弓で援護） | 1d20+wis判定（DC12）
  - 噂話を聞く | ロビンから情報を得る | 判定不要
- 城下町に戻る | 大通りへ戻る | 判定不要

選択: 城下町に戻る
> [プレイヤー] 城下町に戻る
- 現在地がアルテリア城下町になりました。

## step 19 / castle_town 「アルテリア城下町」 HP 12/12 G 100

- 鍛冶屋へ向かう | 武器の強化や購入 | 判定不要
- 宿屋へ向かう | 休息や情報収集 | 判定不要
- 魔法店へ向かう | 魔法の品を購入 | 判定不要
- 道具屋へ向かう | アイテムを購入 | 判定不要
- 路地裏へ向かう | 怪しい場所を探索 | 判定不要
- 王城へ戻る |  | 判定不要
- 城門を出て闇の森へ向かう | 第2章へ進みます | 判定不要

選択: 城門を出て闇の森へ向かう
> [プレイヤー] 城門を出て闇の森へ向かう
> [GM] 城門を抜けると石畳は次第に細い獣道へ変わり、湿った土と苔の匂いが濃くなっていく。やがて木々が陽光を遮り、闇の森の入口で青いスライムが進路を塞いだ。
- 現在地が闇の森・入口になりました。

## step 20 / dark_forest_loc 「闇の森・入口」 HP 12/12 G 100

- スライムと戦う | 戦闘を開始します | 危険（戦闘）

選択: スライムと戦う
> [プレイヤー] スライムと戦う
> [GM] 湿った土を踏みしめて森へ入ると、青いスライムが道を塞いだ。戦う準備を整える。
>
> 敵が退路を塞ぎ、戦闘が始まる。

## step 21 / dark_forest_loc 「闇の森・入口」 HP 12/12 G 100


戦闘: skill / fireball → slime:1
- 火球はスライムに当たらなかった。
- 体当たりがテストに1ダメージ。

## step 22 / dark_forest_loc 「闇の森・入口」 HP 11/12 G 100


戦闘: skill / fireball → slime:1
- 火球がスライムに20ダメージ。
- すべての敵を倒した。
- 5ゴールドを獲得しました。
- 薬草 x2を入手しました。
- 治療の巻物 x1を入手しました。
- 現在地が迷い子の十字路になりました。

## step 23 / lost_goblin_crossroads 「迷い子の十字路」 HP 11/12 G 105

- 箱を取り戻す手伝いを引き受ける |  | 判定不要
- 迷子のゴブリンを無視する | 背を向けた隙に何か起きるかもしれない | 未知の感知判定
- 先へ進む |  | 不明
- 森の入口へ戻る |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]
> [GM] スライムを倒して森を進むと、十字路で一匹のゴブリンが助けを求めていた。別の一族に箱を盗まれ、取り戻してほしいという。
- 戦闘に勝利しました。 HP 11/12、MP 12/20、SP 6/6。

## step 24 / lost_goblin_crossroads 「迷い子の十字路」 HP 11/12 G 105

- 箱を取り戻す手伝いを引き受ける |  | 判定不要
- 迷子のゴブリンを無視する | 背を向けた隙に何か起きるかもしれない | 未知の感知判定
- 先へ進む |  | 不明
- 森の入口へ戻る |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 迷子のゴブリンを無視する
> [プレイヤー] 迷子のゴブリンを無視する
> [GM] 泉へ向かって歩き出した後、財布が軽くなっていることに気づいた。迷子を装ったゴブリンに金を盗まれたのだ。
- 30ゴールドを消費しました。

## step 25 / lost_goblin_crossroads 「迷い子の十字路」 HP 11/12 G 75

- 箱を取り戻す手伝いを引き受ける |  | 判定不要
- 先へ進む |  | 不明
- 森の入口へ戻る |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 森の入口へ戻る
> [プレイヤー] 森の入口へ戻る
- 現在地が闇の森・入口になりました。

## step 26 / dark_forest_loc 「闇の森・入口」 HP 11/12 G 75

- 分かっている道を通って十字路へ進む | 敵を倒す必要はありません | 危険（戦闘）

選択: 分かっている道を通って十字路へ進む
> [プレイヤー] 分かっている道を通って十字路へ進む
- 現在地が迷い子の十字路になりました。

## step 27 / lost_goblin_crossroads 「迷い子の十字路」 HP 11/12 G 75

- 箱を取り戻す手伝いを引き受ける |  | 判定不要
- 先へ進む |  | 不明
- 森の入口へ戻る |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: 箱を取り戻す手伝いを引き受ける
> [プレイヤー] 箱を取り戻す手伝いを引き受ける
> [GM] 「分かった、取り返してやる」と告げると、ゴブリンの顔がぱっと明るくなった。「砦の鉄門で合言葉を聞かれたら、こう答えるんだ」背伸びして耳打ちすると、木々の向こうにそびえる砦を指さした。
- クエスト更新：迷子のゴブリンの箱

## step 28 / lost_goblin_crossroads 「迷い子の十字路」 HP 11/12 G 75

- 先へ進む |  | 不明
- ゴブリン砦へ向かう |  | 不明
- 森の入口へ戻る |  | 判定不要
- ？？？ |  |  [不可: まだ知らない何かが必要なようだ。]

選択: ゴブリン砦へ向かう
> [プレイヤー] ゴブリン砦へ向かう
- 現在地がゴブリン砦・一階前半になりました。

## step 29 / goblin_fort 「ゴブリン砦・一階前半」 HP 11/12 G 75

- 見張りのゴブリンと戦う | 戦闘を開始します | 危険（戦闘）
- 見張りを迂回する | 一階最初の戦闘を避ける | 1d20+dex判定（DC13）
- 砦を出て十字路へ戻る |  | 危険（戦闘）

選択: 見張りのゴブリンと戦う
> [プレイヤー] 見張りのゴブリンと戦う
> [GM] 砦の入口を塞ぐ見張りへ武器を向ける。ゴブリンは侵入者に気づいて警笛へ手を伸ばすが、間に合わないと悟ると短剣を抜き、狭い通路で身構えた。

## step 30 / goblin_fort 「ゴブリン砦・一階前半」 HP 11/12 G 75


戦闘: skill / ice_arrow → goblin:1
- 氷の矢がゴブリンに12ダメージ。
- すべての敵を倒した。
- 5ゴールドを獲得しました。
- 治療の巻物 x1を入手しました。
- 現在地がゴブリン砦・一階後半になりました。

## step 31 / goblin_fort_first_second 「ゴブリン砦・一階後半」 HP 11/12 G 80

> [GM] 最後の一撃が決まり、敵は地に伏した。荒い息を整えると、戦場に静けさが戻る。傷と消耗は残っているが、道を阻む脅威は退けられた。
- 戦闘に勝利しました。 HP 11/12、MP 10/20、SP 6/6。

## step 32 / goblin_fort_first_second 「ゴブリン砦・一階後半」 HP 11/12 G 80

- ゴブリンたちと戦う | 戦闘を開始します | 危険（戦闘）
- 見張りの二匹を迂回する | 一階後半の戦闘を避ける | 1d20+dex判定（DC16）

選択: ゴブリンたちと戦う
> [プレイヤー] ゴブリンたちと戦う
> [GM] 一階奥の角を曲がると、ゴブリンが槍を構え、弓ゴブリンが木箱の上へ飛び乗った。矢じりがこちらを向き、逃げ道を封じてくる。
>
> 敵が退路を塞ぎ、戦闘が始まる。

## step 33 / goblin_fort_first_second 「ゴブリン砦・一階後半」 HP 11/12 G 80


戦闘: skill / ice_arrow → goblin:1
- 氷の矢がゴブリンに12ダメージ。
- 粗末な矢がテストに4ダメージ。

## step 34 / goblin_fort_first_second 「ゴブリン砦・一階後半」 HP 7/12 G 80


戦闘: skill / ice_arrow → goblin_archer:2
- 氷の矢が弓ゴブリンに15ダメージ。
- すべての敵を倒した。
- 10ゴールドを獲得しました。
- 治療の巻物 x1を入手しました。
- 治療の巻物 x2を入手しました。
- 生命の果実 x1を入手しました。
- 現在地がゴブリン砦・二階分岐になりました。

## step 35 / goblin_fort_second_choice 「ゴブリン砦・二階分岐」 HP 7/12 G 90

> [GM] 最後の一撃が決まり、敵は地に伏した。荒い息を整えると、戦場に静けさが戻る。傷と消耗は残っているが、道を阻む脅威は退けられた。
- 戦闘に勝利しました。 HP 7/12、MP 6/20、SP 6/6。

## step 36 / goblin_fort_second_choice 「ゴブリン砦・二階分岐」 HP 7/12 G 90

- 右の通路を探索する |  | 不明
- 左の通路を探索する |  | 不明

選択: 左の通路を探索する
> [プレイヤー] 左の通路を探索する
> [GM] 左の扉を押し開けた瞬間、鉄鎖が床を激しく擦った。暗がりで一対の目が光り、繋がれていた猛犬が鎖を引きちぎって襲いかかる。
- 現在地がゴブリン砦・二階左になりました。

## step 37 / goblin_fort_second_left 「ゴブリン砦・二階左」 HP 7/12 G 90


戦闘: skill / ice_arrow → war_hound:1
- 氷の矢が猛犬に15ダメージ。
- 噛みつきはテストに当たらなかった。

## step 38 / goblin_fort_second_left 「ゴブリン砦・二階左」 HP 7/12 G 90


戦闘: skill / ice_arrow → war_hound:1
- 氷の矢が猛犬に15ダメージ。
- すべての敵を倒した。
- 20ゴールドを獲得しました。
- 現在地がゴブリン砦・回復法陣になりました。

## step 39 / goblin_fort_healing_circle 「ゴブリン砦・回復法陣」 HP 7/12 G 110

> [GM] 最後の一撃が決まり、敵は地に伏した。荒い息を整えると、戦場に静けさが戻る。傷と消耗は残っているが、道を阻む脅威は退けられた。
- 戦闘に勝利しました。 HP 7/12、MP 2/20、SP 6/6。

## step 40 / goblin_fort_healing_circle 「ゴブリン砦・回復法陣」 HP 7/12 G 110

- 回復法陣を使う | 全状態を回復する | 不明

選択: 回復法陣を使う
> [プレイヤー] 回復法陣を使う
> [GM] 法陣の中央に立つと、淡い光が足元から立ちのぼり、傷口がみるみる塞がっていった。息が整ったところで、奥の階段を上る。
- HP・MP・SPが全回復しました。
- 現在地がゴブリン砦・三階鉄門になりました。

## step 41 / goblin_fort_third_gate 「ゴブリン砦・三階鉄門」 HP 12/12 G 110

- 暗号を答える | 入手した暗号で鉄門を開ける | 不明
- 暗号を適当に作る | 知力で門番を騙す | 1d20+int判定（DC18）
- 暗号を知らないと正直に言う | 背後から警備兵が現れる | 危険（戦闘）

選択: 暗号を知らないと正直に言う
> [プレイヤー] 暗号を知らないと正直に言う
> [GM] 暗号を知らないと答えた瞬間、小窓が勢いよく閉じた。直後に背後の隠し扉が開き、一匹の大ゴブリンが棍棒を構えて退路を塞ぐ。
>
> 敵が退路を塞ぎ、戦闘が始まる。
- 現在地がゴブリン砦・三階警備戦になりました。

## step 42 / goblin_fort_third_guards 「ゴブリン砦・三階警備戦」 HP 12/12 G 110


戦闘: skill / ice_arrow → hobgoblin:1
- 氷の矢が大ゴブリンに17ダメージ。
- すべての敵を倒した。
- 5ゴールドを獲得しました。
- 薬草 x1を入手しました。
- 現在地がゴブリン砦・四階財宝庫になりました。

## step 43 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 12/12 G 115

> [GM] 一匹の警備兵を倒すと、戦闘の衝撃で鉄門の錠が外れた。扉の先は財宝庫だ。金貨の山からゴブリン王が立ち上がり、一匹の弓兵が高台へ散って次の戦いを挑んでくる。
- 戦闘に勝利しました。 HP 12/12、MP 18/20、SP 6/6。

## step 44 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 12/12 G 115


戦闘: item / holy_water → goblin_king:1
- 聖水がゴブリン王に36光属性ダメージ。
- 王の戦斧がテストに23ダメージ。
- プレイヤーは戦闘不能になった。
- ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。

## step 45 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 0/12 G 115

> [GM] ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。
- 戦闘に敗北しました。 HP 0/12、MP 18/20、SP 6/6。

## step 46 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 0/12 G 115


終了: {"reason": "ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。", "ending": "goblin_fort_fourth_defeat", "combat_defeat": true, "created_at": "2026-10-18T06:12:22.123036+00:00", "epilogue": []}
> [GM] 運命の糸がほどけ、あなたは再びゴブリン砦の入口に立っていた。
- ゴブリン砦の入口からやり直しました。

## step 47 / goblin_fort 「ゴブリン砦・一階前半」 HP 11/12 G 75

- 見張りのゴブリンと戦う | 戦闘を開始します | 危険（戦闘）
- 見張りを迂回する | 一階最初の戦闘を避ける | 1d20+dex判定（DC13）
- 砦を出て十字路へ戻る |  | 危険（戦闘）

選択: 見張りを迂回する
> [プレイヤー] 見張りを迂回する
> [GM] 物陰と木箱を利用し、見張りに気づかれず一階奥へ進んだ。
- 現在地がゴブリン砦・一階後半になりました。

## step 48 / goblin_fort_first_second 「ゴブリン砦・一階後半」 HP 11/12 G 75

- ゴブリンたちと戦う | 戦闘を開始します | 危険（戦闘）
- 見張りの二匹を迂回する | 一階後半の戦闘を避ける | 1d20+dex判定（DC16）

選択: 見張りの二匹を迂回する
> [プレイヤー] 見張りの二匹を迂回する
> [GM] 巡回の隙を読み、積み上げられた樽の陰を抜けて二匹の背後を通過した。二階へ続く階段まで誰にも気づかれていない。すれ違いざまに生命の果実をくすねた。
- 生命の果実 x1を入手しました。
- 現在地がゴブリン砦・二階分岐になりました。

## step 49 / goblin_fort_second_choice 「ゴブリン砦・二階分岐」 HP 11/12 G 75

- 右の通路を探索する |  | 不明
- 左の通路を探索する |  | 不明

選択: 右の通路を探索する
> [プレイヤー] 右の通路を探索する
- 現在地がゴブリン砦・二階右になりました。

## step 50 / goblin_fort_second_right 「ゴブリン砦・二階右」 HP 11/12 G 75

- 大ゴブリンと戦う | 戦闘を開始します | 危険（戦闘）
- 大ゴブリンを尾行して迂回する | 私室を探る | 1d20+dex判定（DC17）

選択: 大ゴブリンと戦う
> [プレイヤー] 大ゴブリンと戦う
> [GM] 大ゴブリンの前へ踏み出すと、相手は口ずさんでいた暗号を止め、壁に立てかけた棍棒を掴んだ。廊下を塞ぐ巨体が床板を鳴らし、正面から突進してくる。
>
> 敵が退路を塞ぎ、戦闘が始まる。

## step 51 / goblin_fort_second_right 「ゴブリン砦・二階右」 HP 11/12 G 75


戦闘: skill / ice_arrow → hobgoblin:1
- 氷の矢が大ゴブリンに17ダメージ。
- すべての敵を倒した。
- 5ゴールドを獲得しました。
- 薬草 x1を入手しました。
- 現在地がゴブリン砦・三階鉄門になりました。

## step 52 / goblin_fort_third_gate 「ゴブリン砦・三階鉄門」 HP 11/12 G 80

> [GM] 最後の一撃が決まり、敵は地に伏した。荒い息を整えると、戦場に静けさが戻る。傷と消耗は残っているが、道を阻む脅威は退けられた。
- 戦闘に勝利しました。 HP 11/12、MP 10/20、SP 6/6。

## step 53 / goblin_fort_third_gate 「ゴブリン砦・三階鉄門」 HP 11/12 G 80

- 暗号を答える | 入手した暗号で鉄門を開ける | 不明
- 暗号を適当に作る | 知力で門番を騙す | 1d20+int判定（DC18）
- 暗号を知らないと正直に言う | 背後から警備兵が現れる | 危険（戦闘）

選択: 暗号を答える
> [プレイヤー] 暗号を答える
> [GM] 覚えた暗号を告げると鉄門が開く。だが財宝庫へ足を踏み入れた途端、玉座代わりの金貨の山からゴブリン王が立ち上がり、傍らの弓兵が退路へ照準を合わせた。
>
> 敵が退路を塞ぎ、戦闘が始まる。
- 現在地がゴブリン砦・四階財宝庫になりました。

## step 54 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 11/12 G 80


戦闘: item / holy_water → goblin_king:1
- 聖水がゴブリン王に36光属性ダメージ。
- 王の戦斧がテストに9ダメージ。
- 粗末な矢がテストに4ダメージ。
- プレイヤーは戦闘不能になった。
- ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。

## step 55 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 0/12 G 80

> [GM] ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。
- 戦闘に敗北しました。 HP 0/12、MP 10/20、SP 6/6。

## step 56 / goblin_fort_fourth 「ゴブリン砦・四階財宝庫」 HP 0/12 G 80


終了: {"reason": "ゴブリン砦・四階財宝庫で力尽きた。冒険はここで終わりを迎える。", "ending": "goblin_fort_fourth_defeat", "combat_defeat": true, "created_at": "2026-10-18T06:12:23.381185+00:00", "epilogue": []}

## 検証結果

```json
{
  "character": "mage",
  "seed": 106,
  "steps": 56,
  "retry_count": 1,
  "ending": "goblin_fort_fourth_defeat",
  "final_location": "goblin_fort_fourth",
  "first_death": {
    "step": 46,
    "location": "goblin_fort_fourth",
    "ending": "goblin_fort_fourth_defeat",
    "combat_defeat": true,
    "completed": false,
    "attempt": 0,
    "area": "goblin_fort",
    "entry_hp": 11
  },
  "deaths": [
    {
      "step": 46,
      "location": "goblin_fort_fourth",
      "ending": "goblin_fort_fourth_defeat",
      "combat_defeat": true,
      "completed": false,
      "attempt": 0,
      "area": "goblin_fort",
      "entry_hp": 11
    },
    {
      "step": 56,
      "location": "goblin_fort_fourth",
      "ending": "goblin_fort_fourth_defeat",
      "combat_defeat": true,
      "completed": false,
      "attempt": 1,
      "area": "goblin_fort",
      "entry_hp": 11
    }
  ],
  "farthest_location": "goblin_fort_fourth",
  "visited_locations": [
    "castle",
    "castle_town",
    "magic_shop",
    "item_shop",
    "forge",
    "alley",
    "inn",
    "dark_forest_loc",
    "lost_goblin_crossroads",
    "goblin_fort",
    "goblin_fort_first_second",
    "goblin_fort_second_choice",
    "goblin_fort_second_left",
    "goblin_fort_healing_circle",
    "goblin_fort_third_gate",
    "goblin_fort_third_guards",
    "goblin_fort_fourth",
    "goblin_fort_second_right"
  ],
  "retry_visited_locations": [
    "goblin_fort",
    "goblin_fort_first_second",
    "goblin_fort_second_choice",
    "goblin_fort_second_right",
    "goblin_fort_third_gate",
    "goblin_fort_fourth"
  ],
  "failures": [],
  "completed": false,
  "preferred_chapter3_route": "battlefield",
  "chapter3_routes": [],
  "route_entries": [],
  "companion_history": [
    {
      "step": 1,
      "attempt": 0,
      "location": "castle",
      "companion": null
    },
    {
      "step": 47,
      "attempt": 1,
      "location": "goblin_fort",
      "companion": null
    }
  ],
  "final_companion": null,
  "clue_flags": [
    "heard_human_caused_dragon_return"
  ],
  "final_clue_flags": [
    "heard_human_caused_dragon_return"
  ],
  "scenario_choices": [
    {
      "step": 1,
      "attempt": 0,
      "location": "castle",
      "action_id": "go_castle_town",
      "text": "城下町へ出る",
      "pure_movement": true
    },
    {
      "step": 2,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_magic_shop",
      "text": "魔法店へ向かう",
      "pure_movement": true
    },
    {
      "step": 3,
      "attempt": 0,
      "location": "magic_shop",
      "action_id": "ask_blue_mage_rumor",
      "text": "邪竜についての噂を聞く",
      "pure_movement": false
    },
    {
      "step": 4,
      "attempt": 0,
      "location": "magic_shop",
      "action_id": "return_castle_from_magic_shop",
      "text": "城下町に戻る",
      "pure_movement": false
    },
    {
      "step": 5,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_item_shop",
      "text": "道具屋へ向かう",
      "pure_movement": true
    },
    {
      "step": 6,
      "attempt": 0,
      "location": "item_shop",
      "action_id": "return_castle_from_item_shop",
      "text": "城下町に戻る",
      "pure_movement": false
    },
    {
      "step": 7,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_forge",
      "text": "鍛冶屋へ向かう",
      "pure_movement": true
    },
    {
      "step": 8,
      "attempt": 0,
      "location": "forge",
      "action_id": "ask_robert_hammer",
      "text": "浮かない顔をしているが？",
      "pure_movement": false
    },
    {
      "step": 9,
      "attempt": 0,
      "location": "forge",
      "action_id": "ask_blacksmith_weakness",
      "text": "邪竜を討つ方法を聞く",
      "pure_movement": false
    },
    {
      "step": 10,
      "attempt": 0,
      "location": "forge",
      "action_id": "return_castle_from_forge",
      "text": "城下町に戻る",
      "pure_movement": false
    },
    {
      "step": 11,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_alley",
      "text": "路地裏へ向かう",
      "pure_movement": true
    },
    {
      "step": 12,
      "attempt": 0,
      "location": "alley",
      "action_id": "return_castle_from_alley",
      "text": "城下町に戻る",
      "pure_movement": false
    },
    {
      "step": 13,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "return_castle_from_town",
      "text": "王城へ戻る",
      "pure_movement": true
    },
    {
      "step": 14,
      "attempt": 0,
      "location": "castle",
      "action_id": "ask_king_info",
      "text": "国王に邪竜の詳しい話を聞く",
      "pure_movement": false
    },
    {
      "step": 15,
      "attempt": 0,
      "location": "castle",
      "action_id": "check_supplies",
      "text": "侍従から旅の支給品を受け取る",
      "pure_movement": false
    },
    {
      "step": 16,
      "attempt": 0,
      "location": "castle",
      "action_id": "go_castle_town",
      "text": "城下町へ出る",
      "pure_movement": true
    },
    {
      "step": 17,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_inn",
      "text": "宿屋へ向かう",
      "pure_movement": true
    },
    {
      "step": 18,
      "attempt": 0,
      "location": "inn",
      "action_id": "return_castle_from_inn",
      "text": "城下町に戻る",
      "pure_movement": false
    },
    {
      "step": 19,
      "attempt": 0,
      "location": "castle_town",
      "action_id": "go_dark_forest",
      "text": "城門を出て闇の森へ向かう",
      "pure_movement": true
    },
    {
      "step": 20,
      "attempt": 0,
      "location": "dark_forest_loc",
      "action_id": "attack_slime",
      "text": "スライムと戦う",
      "pure_movement": false
    },
    {
      "step": 24,
      "attempt": 0,
      "location": "lost_goblin_crossroads",
      "action_id": "ignore_lost_goblin",
      "text": "迷子のゴブリンを無視する",
      "pure_movement": false
    },
    {
      "step": 25,
      "attempt": 0,
      "location": "lost_goblin_crossroads",
      "action_id": "crossroads_back",
      "text": "森の入口へ戻る",
      "pure_movement": true
    },
    {
      "step": 26,
      "attempt": 0,
      "location": "dark_forest_loc",
      "action_id": "pass_cleared_forest",
      "text": "分かっている道を通って十字路へ進む",
      "pure_movement": true
    },
    {
      "step": 27,
      "attempt": 0,
      "location": "lost_goblin_crossroads",
      "action_id": "help_lost_goblin",
      "text": "箱を取り戻す手伝いを引き受ける",
      "pure_movement": false
    },
    {
      "step": 28,
      "attempt": 0,
      "location": "lost_goblin_crossroads",
      "action_id": "enter_goblin_fort",
      "text": "ゴブリン砦へ向かう",
      "pure_movement": true
    },
    {
      "step": 29,
      "attempt": 0,
      "location": "goblin_fort",
      "action_id": "fight_fort_first_guard",
      "text": "見張りのゴブリンと戦う",
      "pure_movement": false
    },
    {
      "step": 32,
      "attempt": 0,
      "location": "goblin_fort_first_second",
      "action_id": "fight_fort_second_guards",
      "text": "ゴブリンたちと戦う",
      "pure_movement": false
    },
    {
      "step": 36,
      "attempt": 0,
      "location": "goblin_fort_second_choice",
      "action_id": "explore_fort_left",
      "text": "左の通路を探索する",
      "pure_movement": false
    },
    {
      "step": 40,
      "attempt": 0,
      "location": "goblin_fort_healing_circle",
      "action_id": "use_fort_healing_circle",
      "text": "回復法陣を使う",
      "pure_movement": false
    },
    {
      "step": 41,
      "attempt": 0,
      "location": "goblin_fort_third_gate",
      "action_id": "admit_no_password",
      "text": "暗号を知らないと正直に言う",
      "pure_movement": false
    },
    {
      "step": 47,
      "attempt": 1,
      "location": "goblin_fort",
      "action_id": "fort_first_bypass",
      "text": "見張りを迂回する",
      "pure_movement": false
    },
    {
      "step": 48,
      "attempt": 1,
      "location": "goblin_fort_first_second",
      "action_id": "fort_second_bypass",
      "text": "見張りの二匹を迂回する",
      "pure_movement": false
    },
    {
      "step": 49,
      "attempt": 1,
      "location": "goblin_fort_second_choice",
      "action_id": "explore_fort_right",
      "text": "右の通路を探索する",
      "pure_movement": true
    },
    {
      "step": 50,
      "attempt": 1,
      "location": "goblin_fort_second_right",
      "action_id": "fight_hobgoblin",
      "text": "大ゴブリンと戦う",
      "pure_movement": false
    },
    {
      "step": 53,
      "attempt": 1,
      "location": "goblin_fort_third_gate",
      "action_id": "give_correct_password",
      "text": "暗号を答える",
      "pure_movement": false
    }
  ],
  "invariants": {
    "exceptions": 0,
    "noncombat_dead_ends": 0,
    "fallback_narrations": 0
  },
  "battlefield_completed": false,
  "gorge_completed": false,
  "repeat_death_candidate": true
}
```
