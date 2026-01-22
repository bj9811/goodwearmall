import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="패션 이커머스 대시보드",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. Helper Functions
# -----------------------------------------------------------------------------
@st.cache_data # 데이터 로드 속도 향상을 위한 캐싱
def load_and_preprocess_data(uploaded_file):
    try:
        # 파일 확장자 확인 및 로드
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            # 엑셀 엔진을 openpyxl로 명시하여 호환성 문제 해결
            df_raw = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # 헤더 감지 로직 (1월, Jan, 또는 숫자형 월 데이터 감지)
        header_idx = -1
        for idx, row in df_raw.iterrows():
            row_str = row.astype(str).values
            if any('1월' in s for s in row_str) or any('Jan' in s for s in row_str):
                header_idx = idx
                break
        
        # 헤더를 못 찾았을 경우, 2번째 행(Index 1)을 기본값으로 시도
        if header_idx == -1:
            header_idx = 1

        # 데이터프레임 재설정
        df = df_raw.iloc[header_idx+1:].copy()
        df.columns = df_raw.iloc[header_idx]
        
        # 컬럼명 정제 (첫 컬럼이 NaN일 경우 'Mall'로 지정)
        cols = list(df.columns)
        if pd.isna(cols[0]) or str(cols[0]).strip() == '':
            cols[0] = 'Mall'
        df.columns = cols
        
        # Mall 컬럼을 인덱스로 설정
        if 'Mall' not in df.columns:
             # 만약 Mall이 없다면 첫번째 컬럼을 강제로 Mall로 지정
             df.rename(columns={df.columns[0]: 'Mall'}, inplace=True)
        
        df.set_index('Mall', inplace=True)
        
        # 숫자 데이터 변환 (콤마 제거)
        # 문자열로 변환 후 replace -> 숫자 변환
        df_clean = df.apply(lambda x: x.astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce'))
        
        # 유효하지 않은 행/열 제거
        df_clean.dropna(how='all', axis=0, inplace=True)
        df_clean.dropna(how='all', axis=1, inplace=True)
        
        # Total 컬럼 생성
        df_clean['Total_Users'] = df_clean.sum(axis=1)
        
        # Long Format 변환 (시각화용)
        df_reset = df_clean.reset_index()
        # Total_Users는 라인 차트에서 제외
        if 'Total_Users' in df_reset.columns:
            df_for_melt = df_reset.drop(columns=['Total_Users'])
        else:
            df_for_melt = df_reset

        df_long = df_for_melt.melt(
            id_vars=['Mall'], 
            var_name='Month', 
            value_name='Users'
        )
        
        return df_clean, df_long

    except Exception as e:
        st.error(f"데이터를 읽는 중 오류가 발생했습니다: {e}")
        return None, None

def get_color_map(malls):
    color_map = {}
    highlight_blue = '#2980b9'  # 굿웨어/탑텐
    competitor_color = '#95a5a6' # 경쟁사
    
    for mall in malls:
        mall_str = str(mall)
        if '굿웨어' in mall_str or '탑텐' in mall_str or 'Goodwear' in mall_str or 'Topten' in mall_str:
            color_map[mall] = highlight_blue
        else:
            color_map[mall] = competitor_color
    return color_map

# -----------------------------------------------------------------------------
# 3. Main UI
# -----------------------------------------------------------------------------
st.title("📊 2025 Fashion E-Commerce Analysis")
st.markdown("데이터 파일을 업로드하여 분석을 시작하세요.")

with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Excel 또는 CSV 파일", type=['xlsx', 'csv'])

if uploaded_file is not None:
    df_clean, df_long = load_and_preprocess_data(uploaded_file)
    
    if df_clean is not None and not df_clean.empty:
        # --- Selector ---
        all_malls = df_clean.index.unique().tolist()
        selected_malls = st.multiselect("비교할 브랜드 선택", all_malls, default=all_malls)
        
        if selected_malls:
            # Filter Data
            df_filtered_long = df_long[df_long['Mall'].isin(selected_malls)]
            df_filtered_clean = df_clean.loc[selected_malls]
            
            color_map = get_color_map(selected_malls)

            # --- Layout ---
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("월별 MAU 추이")
                fig_line = px.line(
                    df_filtered_long, 
                    x='Month', y='Users', color='Mall',
                    markers=True, color_discrete_map=color_map
                )
                fig_line.update_layout(height=400, xaxis_title=None, yaxis_title="사용자 수")
                st.plotly_chart(fig_line, use_container_width=True)
                
            with col2:
                st.subheader("연간 누적 점유율")
                df_bar = df_filtered_clean.sort_values('Total_Users')
                fig_bar = px.bar(
                    df_bar, 
                    x='Total_Users', y=df_bar.index, orientation='h',
                    color=df_bar.index, color_discrete_map=color_map,
                    text='Total_Users'
                )
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='inside')
                fig_bar.update_layout(height=400, xaxis_title=None, yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- Data Grid ---
            st.markdown("---")
            st.subheader("상세 데이터")
            # AttributeError 방지를 위해 style 제거하고 단순 표시
            st.dataframe(df_filtered_clean)
        else:
            st.warning("브랜드를 하나 이상 선택해주세요.")
    else:
        st.error("데이터를 처리할 수 없습니다. 파일 형식을 확인해주세요.")
else:
    st.info("좌측 사이드바에서 파일을 업로드해주세요.")
