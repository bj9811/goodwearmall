import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="패션 이커머스 통합 대시보드",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. Helper Functions (Data Processing)
# -----------------------------------------------------------------------------
def clean_numeric(val):
    """문자열에서 콤마 제거 후 숫자로 변환"""
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        return pd.to_numeric(val.replace(',', ''), errors='coerce')
    return val

@st.cache_data
def load_and_parse_multiple_tables(uploaded_file):
    """
    하나의 시트에 여러 테이블이 있는 파일을 키워드 기반으로 분리하여 로드합니다.
    """
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # 데이터 프레임 딕셔너리
        extracted_data = {
            'mau': None,
            'install': None,
            'male_demo': None,
            'female_demo': None
        }

        # 키워드로 각 섹션의 시작 행 찾기
        section_map = {
            '월별 사용자수': 'mau',
            '월별 신규설치수': 'install',
            '남성 사용자 비율': 'male_demo',
            '여성 사용자 비율': 'female_demo'
        }

        # 섹션별 시작 인덱스 탐색
        section_starts = {}
        for idx, row in df_raw.iterrows():
            row_str = " ".join(row.astype(str).values)
            for keyword, key in section_map.items():
                if keyword in row_str:
                    section_starts[key] = idx
        
        # 각 섹션 추출 및 정제
        sorted_starts = sorted(section_starts.items(), key=lambda x: x[1])
        
        for i, (key, start_idx) in enumerate(sorted_starts):
            # 끝 인덱스 결정 (다음 섹션 시작 전 or 파일 끝)
            end_idx = sorted_starts[i+1][1] if i < len(sorted_starts)-1 else len(df_raw)
            
            # 테이블 슬라이싱 (Title 행 다음이 Header라고 가정)
            sub_df = df_raw.iloc[start_idx+1 : end_idx].copy()
            
            # 빈 행 제거 (앞쪽)
            sub_df.dropna(how='all', inplace=True)
            
            if sub_df.empty:
                continue

            # 첫 번째 줄을 헤더로 설정
            sub_df.columns = sub_df.iloc[0]
            sub_df = sub_df.iloc[1:]
            
            # 첫 컬럼명 통일 ('Mall')
            cols = list(sub_df.columns)
            if pd.isna(cols[0]) or str(cols[0]).strip() == '':
                cols[0] = 'Mall'
            sub_df.columns = cols
            
            # 'Mall' 컬럼 기준 NaN 제거
            sub_df = sub_df[sub_df['Mall'].notna()]
            sub_df.set_index('Mall', inplace=True)
            
            # 숫자 데이터 정제 (콤마 제거 등)
            sub_df = sub_df.applymap(clean_numeric)
            
            # 불필요한 NaN 컬럼/행 제거
            sub_df.dropna(how='all', axis=1, inplace=True)
            
            extracted_data[key] = sub_df

        return extracted_data

    except Exception as e:
        st.error(f"데이터 파싱 중 오류 발생: {e}")
        return None

def process_timeseries_data(df):
    """시계열 데이터(MAU, 설치수)를 Long Format으로 변환"""
    if df is None: return None, None
    
    # 합계 컬럼 생성 (있으면 덮어쓰기)
    df_processed = df.copy()
    df_processed['Total'] = df_processed.sum(axis=1, numeric_only=True)
    
    # Long Format 변환
    df_reset = df_processed.reset_index()
    # Total 컬럼 제외하고 Melt
    cols_to_melt = [c for c in df_processed.columns if c != 'Total']
    df_long = df_reset.melt(id_vars=['Mall'], value_vars=cols_to_melt, var_name='Month', value_name='Value')
    
    # Month 정렬을 위해 간단히 처리 (실제 데이터에 따라 날짜 변환 필요할 수 있음)
    # 여기서는 원본 순서를 유지하거나 문자열 그대로 사용
    
    return df_processed, df_long

# -----------------------------------------------------------------------------
# 3. Main UI
# -----------------------------------------------------------------------------
st.title("📊 2025 Fashion App Performance Dashboard")
st.markdown("""
<style>
    .metric-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)
st.markdown("MAU, 신규 설치, 인구 통계 데이터를 통합 분석하여 인사이트를 제공합니다.")

with st.sidebar:
    st.header("📂 Data Import")
    uploaded_file = st.file_uploader("통합 데이터 파일 업로드 (xlsx/csv)", type=['xlsx', 'csv'])
    st.info("지원 형식: MAU, 신규설치, 데모 데이터가 포함된 통합 시트")
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("- **더블 클릭**: 범례 항목을 더블 클릭하면 해당 브랜드만 봅니다.")
    st.markdown("- **드래그**: 차트 영역을 드래그하여 확대할 수 있습니다.")

if uploaded_file is not None:
    data_dict = load_and_parse_multiple_tables(uploaded_file)
    
    if data_dict:
        # ---------------------------------------------------------
        # 공통 필터링 (브랜드 선택)
        # ---------------------------------------------------------
        all_malls = set()
        for key, df in data_dict.items():
            if df is not None:
                all_malls.update(df.index.tolist())
        
        # 사이드바 브랜드 선택
        st.sidebar.subheader("비교할 브랜드 선택")
        sorted_malls = sorted(list(all_malls))
        
        # "전체 선택" 옵션
        all_selected = st.sidebar.checkbox("모두 선택/해제", value=True)
        
        if all_selected:
            selected_malls = st.sidebar.multiselect("브랜드 선택", sorted_malls, default=sorted_malls)
        else:
            selected_malls = st.sidebar.multiselect("브랜드 선택", sorted_malls, default=[])
            
        if not selected_malls:
            st.warning("분석할 브랜드를 하나 이상 선택해주세요.")
            st.stop()
            
        # 색상 맵 생성 (브랜드별 고정 색상)
        color_palette = px.colors.qualitative.Bold  # 선명한 색상 팔레트 사용
        color_map = {mall: color_palette[i % len(color_palette)] for i, mall in enumerate(sorted_malls)}

        # ---------------------------------------------------------
        # 탭 구성
        # ---------------------------------------------------------
        tab1, tab2, tab3 = st.tabs(["📉 월별 MAU 분석", "📲 신규 설치수 분석", "👥 인구 통계 (성별/연령)"])

        # === TAB 1: MAU Analysis ===
        with tab1:
            st.subheader("월별 활성 사용자(MAU) 추이")
            df_mau = data_dict.get('mau')
            
            if df_mau is not None:
                df_mau_filtered = df_mau.loc[df_mau.index.isin(selected_malls)]
                df_mau_clean, df_mau_long = process_timeseries_data(df_mau_filtered)
                
                # Metrics (Top 3 Average MAU)
                if not df_mau_clean.empty:
                    top_brands = df_mau_clean['Total'].nlargest(3)
                    cols = st.columns(len(top_brands) + 1 if len(top_brands) > 0 else 1)
                    
                    with cols[0]:
                        st.markdown("**🏆 Top Brands (Total)**")
                    
                    for idx, (brand, total) in enumerate(top_brands.items()):
                        with cols[idx+1]:
                            st.metric(label=brand, value=f"{total:,.0f}")
                
                st.divider()

                # Line Chart
                fig_mau = px.line(df_mau_long, x='Month', y='Value', color='Mall', markers=True,
                                  color_discrete_map=color_map,
                                  labels={'Value': 'MAU (명)', 'Month': '기간', 'Mall': '브랜드'})
                
                fig_mau.update_traces(hovertemplate='%{y:,.0f} 명')
                fig_mau.update_layout(
                    height=500, 
                    template="plotly_white",
                    hovermode="x unified",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='#eee'),
                    legend_title_text=''
                )
                st.plotly_chart(fig_mau, use_container_width=True)
                
                # Data Grid with Download
                with st.expander("MAU 상세 데이터 및 다운로드"):
                    st.dataframe(df_mau_filtered.style.format("{:,.0f}"))
                    csv = df_mau_filtered.to_csv().encode('utf-8-sig')
                    st.download_button("CSV 다운로드", csv, "mau_data.csv", "text/csv")
            else:
                st.warning("MAU 데이터를 찾을 수 없습니다.")

        # === TAB 2: New Installs Analysis ===
        with tab2:
            st.subheader("월별 앱 신규 설치수 추이")
            df_inst = data_dict.get('install')
            
            if df_inst is not None:
                valid_malls = [m for m in selected_malls if m in df_inst.index]
                if valid_malls:
                    df_inst_filtered = df_inst.loc[valid_malls]
                    df_inst_clean, df_inst_long = process_timeseries_data(df_inst_filtered)
                    
                    # Highlight Metric: Max Monthly Install
                    max_val = df_inst_long['Value'].max()
                    max_row = df_inst_long[df_inst_long['Value'] == max_val].iloc[0]
                    
                    st.info(f"💡 기간 내 단일 월 최대 설치: **{max_row['Mall']}** ({max_row['Month']}, {max_val:,.0f}건)")

                    col2_1, col2_2 = st.columns([2, 1])
                    
                    with col2_1:
                        st.markdown("##### 📅 월별 설치 추이")
                        fig_inst = px.line(df_inst_long, x='Month', y='Value', color='Mall', markers=True,
                                          color_discrete_map=color_map,
                                          labels={'Value': '설치수', 'Month': '기간'})
                        fig_inst.update_traces(hovertemplate='%{y:,.0f} 건')
                        fig_inst.update_layout(
                            height=450, 
                            template="plotly_white", 
                            hovermode="x unified",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_inst, use_container_width=True)
                    
                    with col2_2:
                        st.markdown("##### 🏆 브랜드별 누적 설치")
                        df_inst_sorted = df_inst_clean.sort_values('Total', ascending=True) # Bar chart order
                        fig_bar = px.bar(df_inst_sorted, x='Total', y=df_inst_sorted.index, orientation='h',
                                        color=df_inst_sorted.index, text='Total',
                                        color_discrete_map=color_map)
                        fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='inside')
                        fig_bar.update_layout(
                            height=450, 
                            template="plotly_white",
                            showlegend=False, xaxis_title=None, yaxis_title=None
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("선택한 브랜드의 신규 설치 데이터가 없습니다.")
            else:
                st.warning("신규 설치 데이터를 찾을 수 없습니다.")

        # === TAB 3: Demographics ===
        with tab3:
            st.subheader("성별 및 연령별 사용자 비중")
            
            df_male = data_dict.get('male_demo')
            df_female = data_dict.get('female_demo')

            if df_male is not None and df_female is not None:
                valid_malls_demo = [m for m in selected_malls if m in df_male.index]
                
                if valid_malls_demo:
                    df_male_filter = df_male.loc[valid_malls_demo]
                    df_female_filter = df_female.loc[valid_malls_demo]
                    
                    # 1. 성별 비중 Data Construction
                    gender_data = []
                    for mall in valid_malls_demo:
                        m_ratio = df_male_filter.loc[mall, '전체'] if '전체' in df_male_filter.columns else 0
                        f_ratio = df_female_filter.loc[mall, '전체'] if '전체' in df_female_filter.columns else 0
                        gender_data.append({'Mall': mall, 'Gender': '남성', 'Ratio': m_ratio})
                        gender_data.append({'Mall': mall, 'Gender': '여성', 'Ratio': f_ratio})
                    
                    df_gender = pd.DataFrame(gender_data)
                    
                    # Top Section: Gender Bar
                    st.markdown("#### 1️⃣ 성별 구성비 (Male vs Female)")
                    fig_gender = px.bar(df_gender, x='Ratio', y='Mall', color='Gender', orientation='h',
                                        color_discrete_map={'남성': '#3498db', '여성': '#e74c3c'},
                                        text='Ratio', barmode='relative')
                    fig_gender.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
                    fig_gender.update_layout(
                        height=max(200, len(valid_malls_demo)*40), 
                        template="plotly_white",
                        xaxis_title="비중 (%)", yaxis_title=None,
                        legend_title_text=''
                    )
                    st.plotly_chart(fig_gender, use_container_width=True)

                    st.markdown("---")
                    st.markdown("#### 2️⃣ 상세 연령 분포")
                    
                    # Age Columns Parsing (전체 제외)
                    age_cols = [c for c in df_male_filter.columns if c != '전체']
                    
                    tab_age_m, tab_age_f = st.tabs(["🚹 남성 연령별 상세", "🚺 여성 연령별 상세"])
                    
                    with tab_age_m:
                        df_m_melt = df_male_filter[age_cols].reset_index().melt(id_vars='Mall', var_name='Age', value_name='Ratio')
                        fig_m_age = px.bar(df_m_melt, x='Ratio', y='Mall', color='Age', orientation='h',
                                           color_discrete_sequence=px.colors.sequential.Blues,
                                           title="남성 연령 분포")
                        fig_m_age.update_layout(height=450, template="plotly_white", xaxis_title="비중(%)")
                        st.plotly_chart(fig_m_age, use_container_width=True)
                        
                    with tab_age_f:
                        df_f_melt = df_female_filter[age_cols].reset_index().melt(id_vars='Mall', var_name='Age', value_name='Ratio')
                        fig_f_age = px.bar(df_f_melt, x='Ratio', y='Mall', color='Age', orientation='h',
                                           color_discrete_sequence=px.colors.sequential.Reds,
                                           title="여성 연령 분포")
                        fig_f_age.update_layout(height=450, template="plotly_white", xaxis_title="비중(%)")
                        st.plotly_chart(fig_f_age, use_container_width=True)
                        
                else:
                    st.info("선택한 브랜드의 인구 통계 데이터가 없습니다.")
            else:
                st.warning("인구 통계 데이터를 찾을 수 없습니다.")

    else:
        st.error("데이터 파일 형식을 인식하지 못했습니다. 파일 내에 '월별 사용자수', '월별 신규설치수' 등의 키워드가 포함되어 있는지 확인해주세요.")
else:
    # 빈 화면일 때 안내 메시지
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h3>👋 환영합니다!</h3>
        <p>왼쪽 사이드바에서 <b>데이터 파일</b>을 업로드하여 분석을 시작하세요.</p>
    </div>
    """, unsafe_allow_html=True)
