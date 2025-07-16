# **Codex向け指示書：フリガナ自動チェックツールの精度向上と入力ミス検知機能の実装**

## **1\. 最終目標**

このプロジェクトの最終目標は、**漢字氏名**と**フリガナ**のペアを入力として受け取り、そのフリガナが正しいかの検証に加え、**入力ミスである可能性を検知・警告する高精度なツール**を開発することです。

具体的には、入力されたフリガナ以外に、より可能性の高い読み方が存在する場合、その候補と「確からしさ」をスコアとして提示する機能を実現します。

**実行例:**

python app.py "河合 良人" "カワイ ヨシト"

**期待される出力例:**

{  
  "status": "warning",  
  "message": "入力された 'カワイ ヨシト' よりも可能性の高い候補があります。",  
  "input\_kanji": "河合 良人",  
  "input\_furigana": "カワイ ヨシト",  
  "candidates": \[  
    {  
      "furigana": "カワイ ヨシヒト",  
      "score": 0.95  
    },  
    {  
      "furigana": "カワイ ヨシト",  
      "score": 0.75  
    },  
    {  
      "furigana": "カワアイ ヨシヒト",  
      "score": 0.25  
    }  
  \]  
}

## **2\. 現状の課題分析**

現在のスクリプト (app.py, core/scorer.py) には、主に2つの課題があります。

### **課題1: 多様な読み方候補を生成できていない**

* **問題のファイルと箇所:** app.py の main 関数内  
* **原因:** llm.ask() を異なる温度設定で複数回呼び出していますが、後続の候補生成処理 (scorer.get\_candidates) には、**最初のLLMからの応答（最も確実だが多様性に欠ける結果）しか渡していません。** これにより、温度を上げて得られた多様な読み方候補が捨てられてしまい、「河合 良人」に対する「カワイ ヨシヒト」のような有力な候補がリストアップされない問題が発生しています。

### **課題2: 候補の評価ロジックが不十分**

* **問題のファイルと箇所:** core/scorer.py の get\_candidates 関数  
* **原因:** 現在の関数は、LLMからのJSON出力をパースしてリスト化するだけの単純な処理に留まっています。複数の情報源（異なる温度設定のLLM出力など）を統合的に評価し、各候補の「確からしさ」を決定するスコアリングの仕組みが存在しません。

## **3\. 修正・実装方針（ステップ・バイ・ステップ）**

以下の手順に従って、既存のコードを修正・拡張してください。

### **ステップ1: 複数LLMからの出力をすべて集約する (app.py の修正)**

app.pyのmain関数を修正し、すべてのLLMエージェントからの応答をリストとして収集し、それをscorerに渡すように変更します。

**修正対象:** app.py

\# app.py の修正指示

\# (既存のimport文など)  
\# ...

def main():  
    \# ... (引数パーサー部分は既存のまま)

    \# 1\. すべてのLLMエージェントを準備する  
    agents \= \[  
        LLMAgent(temperature=0.01),  
        LLMAgent(temperature=0.5),  
        LLMAgent(temperature=1.0),  
    \]

    \# 2\. すべてのLLMからの応答をリストに格納する  
    llm\_results \= \[\]  
    for agent in agents:  
        \# 各エージェントからJSON形式の応答を取得  
        result\_json \= agent.ask(name, original\_furigana)  
        if result\_json: \# 応答が空でないことを確認  
            llm\_results.append(result\_json)

    \# 3\. Scorerにすべての応答リストを渡す (後続のステップでscorerを修正)  
    \# この時点では get\_candidates はまだ修正されていないが、最終形を想定して記述  
    scorer \= Scorer()  
    \# ★修正点: 単一の結果ではなく、結果のリストを渡す  
    candidates\_with\_scores \= scorer.get\_scored\_candidates(llm\_results, original\_furigana)

    \# 4\. 結果を出力する (後続のステップで実装)  
    \# ... (判定ロジックとJSON出力)  
    print(json.dumps(candidates\_with\_scores, ensure\_ascii=False, indent=2))

if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **ステップ2: 候補生成とスコアリングロジックの実装 (core/scorer.py の修正)**

core/scorer.py を大幅に修正します。複数のLLM応答から重複なく候補を抽出し、各候補の確からしさを評価するスコアリング機能を実装します。

**修正対象:** core/scorer.py

\# core/scorer.py の修正指示  
import json  
from collections import Counter  
\# Levenshtein距離を計算するためにライブラリを導入する  
\# requirements.txt に python-Levenshtein を追加してください  
import Levenshtein

class Scorer:  
    def get\_scored\_candidates(self, llm\_results: list\[str\], original\_furigana: str) \-\> dict:  
        """  
        複数のLLM応答からフリガナ候補を抽出し、スコアを付けて返す。

        Args:  
            llm\_results: LLMからのJSON文字列のリスト。  
            original\_furigana: ユーザーが入力した元のフリガナ。

        Returns:  
            最終的な判定結果を含む辞書。  
        """  
        \# 1\. すべての候補をフラットなリストに集約  
        all\_candidates \= \[\]  
        for res\_json in llm\_results:  
            try:  
                data \= json.loads(res\_json)  
                \# "candidates" キーが存在し、リストであることを確認  
                if isinstance(data.get("candidates"), list):  
                    for candidate in data\["candidates"\]:  
                        \# 各候補が "furigana" キーを持つことを確認  
                        if isinstance(candidate, dict) and "furigana" in candidate:  
                            all\_candidates.append(candidate\["furigana"\])  
            except (json.JSONDecodeError, TypeError):  
                \# JSONパースエラーなどは無視して処理を続行  
                continue

        if not all\_candidates:  
            return self.\_build\_response("error", "有効なフリガナ候補を生成できませんでした。", original\_furigana, \[\])

        \# 2\. 候補の出現回数をカウント  
        candidate\_counts \= Counter(all\_candidates)  
          
        \# 3\. ユニークな候補リストに対してスコアを計算  
        unique\_candidates \= list(candidate\_counts.keys())  
        scored\_list \= \[\]  
        for furigana in unique\_candidates:  
            score \= self.\_calculate\_score(  
                furigana,  
                original\_furigana,  
                candidate\_counts\[furigana\],  
                len(llm\_results)  
            )  
            scored\_list.append({"furigana": furigana, "score": round(score, 4)})

        \# 4\. スコアの高い順にソート  
        scored\_list.sort(key=lambda x: x\["score"\], reverse=True)

        \# 5\. 最終的な判定  
        return self.\_judge(original\_furigana, scored\_list)

    def \_calculate\_score(self, candidate\_furigana: str, original\_furigana: str, count: int, total\_agents: int) \-\> float:  
        """  
        単一の候補に対するスコアを計算する。

        スコア計算ロジック:  
        \- LLMの支持率 (出現回数 / LLMエージェント数) : 70%  
        \- 元の入力との類似度 (レーベンシュタイン距離) : 30%  
        """  
        \# LLM支持率スコア (0.0 \~ 1.0)  
        support\_score \= count / total\_agents

        \# 類似度スコア (0.0 \~ 1.0)  
        \# 距離が0（完全一致）のときスコアが1.0になるように正規化  
        distance \= Levenshtein.distance(candidate\_furigana, original\_furigana)  
        max\_len \= max(len(candidate\_furigana), len(original\_furigana))  
        similarity\_score \= (max\_len \- distance) / max\_len if max\_len \> 0 else 1.0

        \# 重み付けして最終スコアを算出  
        final\_score \= (support\_score \* 0.7) \+ (similarity\_score \* 0.3)  
        return final\_score

    def \_judge(self, original\_furigana: str, scored\_list: list\[dict\]) \-\> dict:  
        """  
        スコアリストに基づいて最終的なステータスとメッセージを決定する。  
        """  
        if not scored\_list:  
            return self.\_build\_response("error", "評価可能な候補がありません。", original\_furigana, \[\])

        top\_candidate \= scored\_list\[0\]  
          
        \# 元の入力が候補リストに存在するかチェック  
        original\_in\_list \= any(c\["furigana"\] \== original\_furigana for c in scored\_list)  
        if not original\_in\_list:  
            return self.\_build\_response("error", "入力されたフリガナは候補にありません。入力ミスの可能性が非常に高いです。", original\_furigana, scored\_list)

        \# 元の入力が最高スコアかチェック  
        if top\_candidate\["furigana"\] \== original\_furigana:  
            return self.\_build\_response("success", "入力されたフリガナが最も可能性の高い候補です。", original\_furigana, scored\_list)  
        else:  
            return self.\_build\_response("warning", f"入力された '{original\_furigana}' よりも可能性の高い候補 '{top\_candidate\['furigana'\]}' があります。", original\_furigana, scored\_list)

    def \_build\_response(self, status: str, message: str, original\_furigana: str, candidates: list) \-\> dict:  
        """  
        最終的な出力JSONを整形する。  
        """  
        return {  
            "status": status,  
            "message": message,  
            "input\_furigana": original\_furigana,  
            "candidates": candidates  
        }

### **ステップ3: 全体の統合と出力 (app.py の最終調整)**

ステップ1と2で修正したモジュールを統合し、最終的なJSONを出力するようにapp.pyのmain関数を完成させます。

**修正対象:** app.py

\# app.py の最終的な main 関数の姿  
import json  
import argparse  
from core.llm import LLMAgent  
from core.scorer import Scorer  
\# ... 他の必要なimport

def main():  
    parser \= argparse.ArgumentParser(description="Furigana validation tool.")  
    parser.add\_argument("name", type=str, help="Kanji name")  
    parser.add\_argument("furigana", type=str, help="Furigana in Katakana")  
    args \= parser.parse\_args()  
    name \= args.name  
    original\_furigana \= args.furigana

    \# 1\. すべてのLLMエージェントを準備する  
    agents \= \[  
        LLMAgent(temperature=0.01),  
        LLMAgent(temperature=0.5),  
        LLMAgent(temperature=1.0),  
    \]

    \# 2\. すべてのLLMからの応答をリストに格納する  
    llm\_results \= \[\]  
    for agent in agents:  
        result\_json \= agent.ask(name, original\_furigana)  
        if result\_json:  
            llm\_results.append(result\_json)

    \# 3\. Scorerを使って候補を評価・判定する  
    scorer \= Scorer()  
    final\_result \= scorer.get\_scored\_candidates(llm\_results, original\_furigana)

    \# 4\. 判定結果に漢字氏名を追加して最終出力  
    final\_result\["input\_kanji"\] \= name  
      
    \# 整形してJSONを出力  
    print(json.dumps(final\_result, ensure\_ascii=False, indent=2))

if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

## **4\. 必要なライブラリの追加**

スコアリングのためにpython-Levenshteinライブラリを使用します。requirements.txtに以下を追加してください。

python-Levenshtein

## **5\. 実行と確認**

すべての修正が完了したら、以下のコマンドで動作を確認してください。

**ケース1: 警告が期待されるケース**

python app.py "河合 良人" "カワイ ヨシト"

**期待されるstatus:** warning

**ケース2: 成功が期待されるケース**

python app.py "佐藤 健" "サトウ タケル"

**期待されるstatus:** success

**ケース3: エラーが期待されるケース**

python app.py "鈴木 一郎" "スズキ ジロウ"

**期待されるstatus:** error

以上の指示に従って、コードの修正を実行してください。これにより、フリガナチェックツールはより高精度になり、入力ミス検知という最終目標を達成できるはずです。