# **フリガナ判定ロジックの修正指示書 (for AI Agent)**

## **1\. タスクの最終目標 (Goal)**

このタスクの目標は、フリガナチェックツールにおいて、**キーパンチャー特有の入力ルール（拗音を大文字で入力するなど）と、標準的な日本語の読み方との間の表記の揺れを吸収し、正しくフリガナの一致判定を行えるようにする**ことです。

具体的には、core/utils.py 内の比較ロジックで使われている正規化関数を、このプロジェクト専用に用意されている normalize\_for\_keypuncher\_check に変更します。

## **2\. 問題の背景と原因 (Context & Root Cause)**

背景:  
現在のシステムは、利用者が入力したフリガナと、形態素解析（Sudachi）やLLM（GPT）が生成した読み仮名を比較して、フリガナの正しさを判定します。しかし、利用者は「ジュ」を「ジユ」、「キャ」を「キヤ」のように、拗音を2つの大文字で入力する特殊なルール（キーパンチャールール）で入力することがあります。  
原因:  
問題の根本原因は、フリガナを比較する際に使用している正規化関数が不適切なことです。

* **ファイル:** core/utils.py  
* **関数:** process\_dataframe, async\_process\_dataframe  
* **問題のコード:**  
  \# Sudachiの解析結果やGPTの候補と比較する際に、単純な正規化関数が使われている  
  if normalize\_kana(sudachi\_kana) \== normalize\_kana(reading):  
      ...  
  if normalize\_kana(candidate) \== normalize\_kana(reading):  
      ...

* 詳細:  
  normalize\_kana 関数は、半角カタカナを全角に変換するだけで、キーパンチャールール（例: ジユ）と標準的な拗音（例: ジュ）を同一視する処理を行いません。その結果、人間が見れば正しいフリガナでも、プログラム上は「不一致」と判定され、信頼度が不当に低く評価されてしまいます。（例：「サトウ ジュウスケ」という名前に対し「ｻﾄｳ ｼﾞﾕｳｽｹ」というフリガナが入力されると、信頼度30になってしまう）

幸い、この問題を解決するために設計された normalize\_for\_keypuncher\_check という関数が core/normalize.py にすでに存在します。今回はこの関数を適切な場所で使うように修正します。

## **3\. 修正手順 (Step-by-Step Instructions)**

以下の手順に従って、core/utils.py ファイルを修正してください。

### **ステップ1: import文の変更**

まず、core/utils.py ファイルの先頭にある import 文を変更し、今回使用する正しい正規化関数 normalize\_for\_keypuncher\_check をインポートします。

**変更前:**

from .normalize import normalize\_kana

**変更後:**

from .normalize import normalize\_kana, normalize\_for\_keypuncher\_check

*(注: normalize\_kana は他の箇所で使われている可能性も考慮し、削除せずに追加する形で対応してください)*

### **ステップ2: process\_dataframe 関数の修正**

同期処理を行う process\_dataframe 関数内の比較処理を修正します。2箇所あります。

**変更箇所 1/2 (Sudachi候補との比較):**

\# core/utils.py の process\_dataframe 関数内

\# 変更前  
if sudachi\_kana and normalize\_kana(sudachi\_kana) \== normalize\_kana(reading):  
    confs\[idx\] \= 95  
    reasons\[idx\] \= "辞書候補1位一致"  
    continue

\# 変更後  
if sudachi\_kana and normalize\_for\_keypuncher\_check(sudachi\_kana) \== normalize\_for\_keypuncher\_check(reading):  
    confs\[idx\] \= 95  
    reasons\[idx\] \= "辞書候補1位一致"  
    continue

**変更箇所 2/2 (GPT候補との比較):**

\# core/utils.py の process\_dataframe 関数内

\# 変更前  
if normalize\_kana(candidate) \== normalize\_kana(reading):  
    conf \= 80  
    reason \= "GPT候補一致"  
    break

\# 変更後  
if normalize\_for\_keypuncher\_check(candidate) \== normalize\_for\_keypuncher\_check(reading):  
    conf \= 80  
    reason \= "GPT候補一致"  
    break

### **ステップ3: async\_process\_dataframe 関数の修正**

非同期処理を行う async\_process\_dataframe 関数内も同様に修正します。こちらも2箇所あります。

**変更箇所 1/2 (Sudachi候補との比較):**

\# core/utils.py の async\_process\_dataframe 関数内

\# 変更前  
if sudachi\_kana and normalize\_kana(sudachi\_kana) \== normalize\_kana(reading):  
    return 95, "辞書候補1位一致"

\# 変更後  
if sudachi\_kana and normalize\_for\_keypuncher\_check(sudachi\_kana) \== normalize\_for\_keypuncher\_check(reading):  
    return 95, "辞書候補1位一致"

**変更箇所 2/2 (GPT候補との比較):**

\# core/utils.py の async\_process\_dataframe 関数内

\# 変更前  
if normalize\_kana(candidate) \== normalize\_kana(reading):  
    return 80, "GPT候補一致"

\# 変更後  
if normalize\_for\_keypuncher\_check(candidate) \== normalize\_for\_keypuncher\_check(reading):  
    return 80, "GPT候補一致"

## **4\. 期待される結果 (Expected Outcome)**

この修正を適用すると、システムは以下のように動作するようになります。

* **入力例:**  
  * name: サトウ　ジュウスケ  
  * reading (入力フリガナ): ｻﾄｳ ｼﾞﾕｳｽｹ  
* **修正後の動作:**  
  1. Sudachiが name から サトウジュウスケ という読みを生成します。  
  2. normalize\_for\_keypuncher\_check("サトウジュウスケ") は "サトウジユウスケ" を返します。  
  3. normalize\_for\_keypuncher\_check("ｻﾄｳ ｼﾞﾕｳｽｹ") も "サトウジユウスケ" を返します。  
  4. 両者が一致するため、\*\*信頼度は95、理由は「辞書候補1位一致」\*\*と正しく判定されます。

## **5\. 結論**

以上の手順で core/utils.py を修正してください。これにより、キーパンチャールールに起因するフリガナの表記揺れ問題が解決され、ツールの判定精度が大幅に向上します。