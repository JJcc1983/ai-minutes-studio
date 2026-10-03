# gemini-3.5-flash-lite

import streamlit as st
from google import genai
from google.genai import types
import datetime

# ページ基本設定
st.set_page_config(
    page_title="AI 音声＆テキスト処理スタジオ",
    page_icon="🎙️",
    layout="wide"
)

st.title("🎙️ AI 音声文字起こし ＆ 要約スタジオ")
st.caption("Google Gemini API × Streamlit によるマルチモーダル処理・コスト最適化ダッシュボード")

# --- 定数設定（gemini-3.5-flash-lite 料金レート：1USD=150円換算） ---
# 入力: $0.075 / 1M tokens, 出力: $0.30 / 1M tokens
USD_JPY = 150.0
COST_PER_INPUT_TOKEN = (0.075 / 1_000_000) * USD_JPY
COST_PER_OUTPUT_TOKEN = (0.30 / 1_000_000) * USD_JPY

def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """トークン数から日本円の概算コストを計算"""
    return (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)

# --- セッション状態の初期化 ---
if "history" not in st.session_state:
    st.session_state.history = []
if "current_audio_result" not in st.session_state:
    st.session_state.current_audio_result = None
if "current_text_result" not in st.session_state:
    st.session_state.current_text_result = None
if "total_in_tokens" not in st.session_state:
    st.session_state.total_in_tokens = 0
if "total_out_tokens" not in st.session_state:
    st.session_state.total_out_tokens = 0
if "total_cost_jpy" not in st.session_state:
    st.session_state.total_cost_jpy = 0.0

# --- サイドバー設定 ---
with st.sidebar:
    st.header("⚙️ 設定 & 監視")
    api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studioで取得したAPIキーを入力")
    
    st.markdown("---")
    st.markdown("### 📊 累計利用コスト・トークン")
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("累計トークン", f"{st.session_state.total_in_tokens + st.session_state.total_out_tokens:,}")
    with col_sb2:
        st.metric("累計概算コスト", f"¥{st.session_state.total_cost_jpy:.3f}")
    
    st.caption(f"・入力: {st.session_state.total_in_tokens:,} tok\n・出力: {st.session_state.total_out_tokens:,} tok")
    st.write(f"保存中の履歴: **{len(st.session_state.history)} 件**")
    
    if len(st.session_state.history) > 0:
        if st.button("🗑️ 履歴と利用統計をリセット", type="secondary", use_container_width=True):
            st.session_state.history = []
            st.session_state.current_audio_result = None
            st.session_state.current_text_result = None
            st.session_state.total_in_tokens = 0
            st.session_state.total_out_tokens = 0
            st.session_state.total_cost_jpy = 0.0
            st.rerun()

# --- メインタブの作成 ---
tab1, tab2, tab3 = st.tabs([
    "🎵 音声の文字起こし & 要約",
    "📝 テキスト要約",
    f"📜 処理履歴 ({len(st.session_state.history)})"
])

# ==========================================
# タブ1：音声処理
# ==========================================
with tab1:
    st.subheader("音声ファイル（MP3 / WAV / M4A）の解析")
    
    uploaded_file = st.file_uploader(
        "音声ファイルをアップロードしてください",
        type=["mp3", "wav", "m4a", "aac", "ogg"]
    )
    
    output_format = st.radio(
        "出力フォーマット",
        ["議事録形式（文字起こし ＋ 決定事項・Todo）", "文字起こし全文のみ", "要点のみを箇条書き要約"],
        horizontal=True
    )

    if uploaded_file is not None:
        st.audio(uploaded_file)
        
        if st.button("音声から文字起こし＆要約を実行", type="primary"):
            if not api_key:
                st.error("左のサイドバーにGemini API Keyを入力してください。")
            else:
                try:
                    with st.spinner("音声を解析中...（数十秒かかる場合があります）"):
                        client = genai.Client(api_key=api_key)
                        
                        audio_bytes = uploaded_file.read()
                        audio_part = types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=uploaded_file.type
                        )
                        
                        prompt = f"""
提供された音声ファイルを注意深く聴き取り、以下の形式・指示に従って日本語で出力してください。

【出力フォーマットの指示】:
{output_format}

【要件】:
- 文字起こしはケバ取りを行い、読みやすく整えてください。
- 会話者やトピックが分かる場合は、見出しを付けて構造化してください。
"""
                        
                        response = client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=[prompt, audio_part]
                        )
                        
                        # トークン情報の取得
                        usage = response.usage_metadata
                        in_tok = usage.prompt_token_count if usage else 0
                        out_tok = usage.candidates_token_count if usage else 0
                        cost = calculate_cost(in_tok, out_tok)
                        
                        # 累計更新
                        st.session_state.total_in_tokens += in_tok
                        st.session_state.total_out_tokens += out_tok
                        st.session_state.total_cost_jpy += cost
                        
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        result_data = {
                            "text": response.text,
                            "in_tok": in_tok,
                            "out_tok": out_tok,
                            "cost": cost
                        }
                        st.session_state.current_audio_result = result_data
                        
                        # 履歴に追加
                        st.session_state.history.insert(0, {
                            "id": f"audio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "timestamp": now_str,
                            "type": "音声解析",
                            "source_title": uploaded_file.name,
                            "format": output_format,
                            "result": response.text,
                            "in_tok": in_tok,
                            "out_tok": out_tok,
                            "cost": cost
                        })
                        
                        st.success("音声解析が完了しました！")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

    # 直近の音声結果表示
    if st.session_state.current_audio_result:
        res = st.session_state.current_audio_result
        st.markdown("---")
        
        # コスト・トークンメトリクス表示
        m1, m2, m3 = st.columns(3)
        m1.metric("入力トークン", f"{res['in_tok']:,} tok")
        m2.metric("出力トークン", f"{res['out_tok']:,} tok")
        m3.metric("今回の概算コスト", f"¥{res['cost']:.4f}")
        
        st.markdown("### 📄 解析結果")
        st.markdown(res["text"])
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        c1, c2, _ = st.columns([2, 2, 4])
        with c1:
            st.download_button(
                "📥 テキスト保存 (.txt)",
                data=res["text"],
                file_name=f"audio_result_{timestamp}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c2:
            st.download_button(
                "📥 Markdown保存 (.md)",
                data=res["text"],
                file_name=f"audio_result_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==========================================
# タブ2：テキスト要約
# ==========================================
with tab2:
    st.subheader("テキストの要約・整形")
    user_text = st.text_area("文章を入力してください", height=180, placeholder="ここに要約したいテキストを入力...")
    text_style = st.selectbox(
        "要約スタイル",
        ["3行で要約", "箇条書きで重要ポイント抽出", "ビジネスメール風に整形"]
    )
    
    if st.button("テキストを要約する", type="primary"):
        if not api_key:
            st.error("左のサイドバーにGemini API Keyを入力してください。")
        elif not user_text.strip():
            st.warning("文章を入力してください。")
        else:
            try:
                with st.spinner("要約中..."):
                    client = genai.Client(api_key=api_key)
                    prompt = f"【指示】: {text_style}\n\n【テキスト】:\n{user_text}"
                    response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=prompt
                    )
                    
                    usage = response.usage_metadata
                    in_tok = usage.prompt_token_count if usage else 0
                    out_tok = usage.candidates_token_count if usage else 0
                    cost = calculate_cost(in_tok, out_tok)
                    
                    st.session_state.total_in_tokens += in_tok
                    st.session_state.total_out_tokens += out_tok
                    st.session_state.total_cost_jpy += cost
                    
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    result_data = {
                        "text": response.text,
                        "in_tok": in_tok,
                        "out_tok": out_tok,
                        "cost": cost
                    }
                    st.session_state.current_text_result = result_data
                    
                    preview = user_text[:30].replace("\n", " ") + ("..." if len(user_text) > 30 else "")
                    st.session_state.history.insert(0, {
                        "id": f"text_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "timestamp": now_str,
                        "type": "テキスト要約",
                        "source_title": preview,
                        "format": text_style,
                        "result": response.text,
                        "in_tok": in_tok,
                        "out_tok": out_tok,
                        "cost": cost
                    })
                    
                    st.success("テキスト要約が完了しました！")
                    st.rerun()
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    # 直近のテキスト結果表示
    if st.session_state.current_text_result:
        res = st.session_state.current_text_result
        st.markdown("---")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("入力トークン", f"{res['in_tok']:,} tok")
        m2.metric("出力トークン", f"{res['out_tok']:,} tok")
        m3.metric("今回の概算コスト", f"¥{res['cost']:.4f}")
        
        st.markdown("### 📋 要約結果")
        st.markdown(res["text"])
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 要約結果を保存 (.txt)",
            data=res["text"],
            file_name=f"text_summary_{timestamp}.txt",
            mime="text/plain"
        )

# ==========================================
# タブ3：処理履歴一覧
# ==========================================
with tab3:
    st.subheader("📜 過去の処理履歴")
    
    if not st.session_state.history:
        st.info("まだ処理履歴がありません。")
    else:
        st.caption(f"全 {len(st.session_state.history)} 件の履歴を表示しています。")
        
        for idx, item in enumerate(st.session_state.history):
            title_icon = "🎵" if item["type"] == "音声解析" else "📝"
            header_label = (
                f"{title_icon} [{item['timestamp']}] {item['type']} - {item['source_title']} "
                f"| 消耗: {item['in_tok'] + item['out_tok']:,} tok (¥{item['cost']:.4f})"
            )
            
            with st.expander(header_label, expanded=(idx == 0)):
                # 内訳メトリクス
                st.caption(f"🔹 入力: {item['in_tok']:,} tok / 出力: {item['out_tok']:,} tok / 概算コスト: ¥{item['cost']:.4f}")
                st.markdown(item["result"])
                
                st.download_button(
                    label=f"📥 この結果をダウンロード ({item['id']}.txt)",
                    data=item["result"],
                    file_name=f"{item['id']}.txt",
                    mime="text/plain",
                    key=f"dl_history_{item['id']}_{idx}"
                )