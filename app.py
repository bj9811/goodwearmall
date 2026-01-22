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
@st.cache_data
def load_and_preprocess_data(uploaded_file):
    try:
        # 파일 로드 (Excel 엔진 호환성 강화)
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # 헤더 자동 감지 ('1월', 'Jan' 등)
        header_idx = -1
        for idx, row in df_raw.iterrows():
            row_str = row.astype(str).values
            if any('1월' in s for s in row_str) or any('Jan' in s for s in row_str):
                header_idx = idx
                break
        
        if header_idx == -1:
            header_idx = 1 # 감지 실패 시 기본값

        # 데이터 정리
        df = df_raw.iloc[header_idx+1:].copy()
        df.columns = df_raw.iloc[header_idx]
        
        cols = list(df.columns)
        if pd.isna(cols[0]) or str(cols[0]).strip() == '':
            cols[0] = 'Mall'
        df.columns = cols
        
        if 'Mall' not in df.columns:
             df.rename(columns={df.columns[0]: 'Mall'}, inplace=True)
        
        df.set_index('Mall', inplace=True)
        
        # 숫자 변환 (콤마 제거)
        df_clean = df.apply(lambda x: x.astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce'))
        
        df_clean.dropna(how='all', axis=0, inplace=True)
        df_clean.dropna(how='all', axis=1, inplace=True)
        
        # 합계 컬럼 생성
        df_clean['Total_Users'] = df_clean.sum(axis=1)
        
        # 시각화용 데이터 변환 (Wide -> Long)
        df_reset = df_clean.reset_index()
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
        st.error(f"데이터 처리 중 오류: {e}")
        return None, None

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
        # ---------------------------------------------------------
        # [수정됨] 브랜드 선택 영역: Checkbox List UI
        # ---------------------------------------------------------
        st.sidebar.markdown("---")
        st.sidebar.subheader("비교할 브랜드 선택")
        
        all_malls = df_clean.index.unique().tolist()
        selected_malls = []

        # 각 브랜드별로 체크박스 생성 (기본값: 체크됨)
        for mall in all_malls:
            # key를 주어 위젯 충돌 방지
            is_checked = st.sidebar.checkbox(mall, value=True, key=f"chk_{mall}")
            if is_checked:
                selected_malls.append(mall)
        
        # ---------------------------------------------------------

        if selected_malls:
            # 데이터 필터링
            df_filtered_long = df_long[df_long['Mall'].isin(selected_malls)]
            df_filtered_clean = df_clean.loc[selected_malls]
            
            # 레이아웃 분할
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("월별 MAU 추이")
                # 자동 색상 할당
                fig_line = px.line(
                    df_filtered_long, 
                    x='Month', 
                    y='Users', 
                    color='Mall', 
                    markers=True
                )
                fig_line.update_layout(height=450, xaxis_title=None, yaxis_title="사용자 수")
                st.plotly_chart(fig_line, use_container_width=True)
                
            with col2:
                st.subheader("연간 누적 점유율")
                df_bar = df_filtered_clean.sort_values('Total_Users')
                fig_bar = px.bar(
                    df_bar, 
                    x='Total_Users', 
                    y=df_bar.index, 
                    orientation='h',
                    color=df_bar.index,
                    text='Total_Users'
                )
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='inside')
                fig_bar.update_layout(height=450, xaxis_title=None, yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            # 상세 데이터
            st.markdown("---")
            st.subheader("상세 데이터")
            st.dataframe(df_filtered_clean)
        else:
            st.warning("왼쪽 사이드바에서 최소 하나의 브랜드를 체크해주세요.")
    else:
        st.error("데이터 형식 오류: 파일을 확인해주세요.")
else:
    st.info("좌측 사이드바에서 파일을 업로드해주세요.")
