# NL to TIO 實驗及方法評估

## 前述：
* 為什麼需要 TIO
* 這個實驗的目的：研究 retrieval 方法相對於單純使用 LLM 的優勢
* 
## 四條實驗線簡述
* 實驗線的環境，基礎配置（few shot + system prompt 等等，要記得明確寫出 strong/weak few shot, system prompt 的差異）
* 簡述四條實驗線的意義
* 測資架構介紹 （hub and spoke）

## 自創 graphrag 架構設計
* 先敘述為什麼這個實驗不適合使用 microsoft graphrag 的原因
* 根據 retrieval_arch.md 的 Graphrag 敘述
* 盡量不要敘述的太複雜，用圖大於用文字介紹
* 簡單扼要，不需要太細節，但重要的部分還是要說不要忽略

## KGE 架構設計
* 根據 retrieval_arch.md 的 KGE 架構敘述
* 盡量不要敘述的太複雜，用圖大於用文字介紹
* 簡單扼要，不需要太細節，但重要的部分還是要說不要忽略

## 評估器
* 評估面向及標準
* 簡述評估方法

## 四方比較
* 使用圖對這四項實驗線做準確率以及 token 數量比較，可以做兩張圖分別說明

## 結論
* 根據實驗結果得出 retrieval 對於省 token 又能達到跟純LLM一樣高的品質 