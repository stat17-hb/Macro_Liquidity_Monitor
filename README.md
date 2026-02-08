# 유동성 모니터링 대시보드

대차대조표 확장/수축 관점의 유동성 분석 웹앱

## 핵심 철학

### 유동성 - 대차대조표 관점
**유동성은 돈의 총량이 아닌, 금융시스템 대차대조표의 확장과 수축이다.**

고정된 화폐량(money supply)은 거시경제학의 착각이다. 실제 유동성은:
- Fed의 자산 확장(QE) → 은행 예치금 증가 → 신용 창출 활성화
- Fed의 자산 축소(QT) → 은행 예치금 감소 → 신용 수축 압박
- 담보 가치 변화 → 레버리지 제약 강화/완화

### 가격 - 한계 신념
**자산 가격은 실물 기초(fundamental value)가 아닌, 한계 투자자(marginal buyer)의 신념에서 결정된다.**

가격 결정 메커니즘:
- 달러 증가 ≠ 가격 상승 (돈의 양이 아님)
- **한계 신념** = 기대 수익 - 위험 프리미엄 → 가격 변동
- 담보 가치 하락 → 한계 투자자 신용 조달 어려움 → 가격 조정
- 레버리지 제약 → 가격 탄성(elasticity) 하락 → 가격 변동성 증가

### 목표 - 취약점 탐지
**목표는 가격을 설명하는 것이 아니라, 레버리지 축적과 시스템 리스크 탐지이다.**

취약점 탐지의 세 차원:
1. **신용 창출 메커니즘**: 대차대조표 확장 지속 가능성
2. **담보 강건성**: 담보 가치 변화와 레버리지 증폭/축소
3. **한계 신념 vs 현실 격차**: 밸류에이션(신념)과 이익 개선 간극

## Fed 대차대조표 항등식

Fed의 자산/부채 구조는 유동성 환경을 완전히 결정한다:

```
Fed 자산 = 준비금(Reserves) + RRP + 기타 부채
WALCL  = RESBALNS + RRPONTSV + ...
```

### 항등식 상세

**자산(Assets):**
- **SOMA 보유 자산** (System Open Market Account): 국채, MBS, 기타
- **대출(Lending)**: 은행 대출(사다리 지원), 통화 스왑 등

**부채 및 자본:**
- **준비금(Reserves, RESBALNS)**: 은행 예치금 → 신용 창출 원천
- **Reverse Repo (RRP, RRPONTSV)**: 단기 자금 조달처 (MMF, 정부 펀드)
- **TGA (Treasury General Account)**: 미국 정부 예치금

### 유동성 메커니즘

| 시나리오 | Fed 자산 | 준비금 | 신용 창출 | RRP 압력 |
|---------|---------|--------|----------|----------|
| QE 확대 | ↑ | ↑ | ↑ | ↓ (여유) |
| QT 진행 | ↓ | ↓ | ↓ | ↑ (압박) |
| 이자율 인상 | → | → | → | ↑ (매력) |
| 신용 추월 | → | ↓ | ↑ | ↑ (경쟁) |

**핵심**: RRP 잔액 급증 = 시스템 유동성 과잉 신호 → 경고

## 설치 및 실행

```bash
cd "유동성 분석 대시보드"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 페이지 구성

| 페이지 | 설명 |
|--------|------|
| Executive Overview | 레짐 배지, 핵심 6개 지표, 취약 지점 Top 3 |
| Balance Sheet | Fed 자산, Bank Credit, M2 성장률/가속도, 준비금/RRP 추이 |
| Collateral | VIX, 스프레드, 담보 스트레스 지수 |
| Marginal Belief | 실질금리, 밸류에이션 vs 이익, 신념 과열 |
| Leverage | 레버리지 점수, 한계 투자자 추정 |
| Alerts | 룰 기반 알림, 레짐별 행동 제안 |
| QT Monitoring | Fed QT 진행도, 준비금 감소율, RRP 변화, 신용 추월 지표 |

## 지표 정의

### 최소 세트 (기본 제공)
- **Fed Total Assets**: 중앙은행 대차대조표 (WALCL)
- **Bank Credit**: 상업은행 신용 (TOTBKCR)
- **M2**: 광의통화 (M2SL)
- **HY Spread**: 하이일드 스프레드 (BAMLH0A0HYM2)
- **VIX**: 변동성 지수 (^VIX)
- **Real Yield**: 실질금리 (DFII10)
- **S&P 500**: 주가지수 (^GSPC)

## 레짐 분류

| 레짐 | 조건 |
|------|------|
| Expansion | 신용 성장(+), 스프레드 축소, 변동성 낮음 |
| Late-cycle | 신용 성장 지속, 밸류에이션 > 이익 개선 |
| Contraction | 신용 둔화/역전, 스프레드 확대, 변동성 상승 |
| Stress | 변동성 급등 + 스프레드 급확대 + 주가 급락 |

## 알림 규칙

1. **신념 과열**: 밸류에이션 z-score 상승 > 이익 z-score 상승
2. **담보 스트레스**: VIX 90%ile + 스프레드 75%ile + 주가 1M < -5%
3. **대차대조표 수축**: Bank Credit 3M ann < 0% + 스프레드 확대

## 분석 프레임워크

이 대시보드는 다음 네 가지 분석 차원을 통합한다:

### 1. 신용 창출 메커니즘 (대차대조표 확장)

**조기 경고 신호:**
- Fed 준비금(RESBALNS) 감소 추세 → 신용 창출 여력 약화
- Bank Credit 성장률 둔화 → 신용 공급 부진
- M2 성장률 역전 → 광의통화 수축 신호

**대시보드 측정:**
- Balance Sheet 페이지: Fed Total Assets, Bank Credit, M2 추이
- QT Monitoring: 준비금 감소율, RRP 변화

### 2. 담보 가치 변화와 레버리지 증폭

**담보 메커니즘:**
```
담보 가치 ↓ → 한계 투자자 신용선 축소
         → 자산 담보 재평가(haircut) 강화
         → 레버리지 축소 압력 (forced deleveraging)
```

**측정 지표:**
- VIX (변동성 = 담보 불안정성)
- HY Spread (신용 위험 프리미엄)
- Equity risk premium (주가 담보 가치 지표)

**Collateral 페이지:** 담보 스트레스 지수 = VIX + Spread 정규화

### 3. 한계 신념 vs 현실 격차

**신념의 과열 감지:**
```
밸류에이션 상승 (높은 P/E)
  ↕ (괴리)
이익 성장 부진 (낮은 EPS 성장)
  = 신념 버블 위험 신호
```

**측정:**
- P/E Ratio z-score: 밸류에이션 과열 정도
- EPS 성장률: 실질 이익 개선 여부
- 실질금리(Real Yield): 할인율 변화 (신념 지탱력)

**Marginal Belief 페이지:** 신념 과열 지수 = (P/E z-score) - (EPS z-score)

### 4. QT와 유동성 환경 변화

**QT의 신용 수축 경로:**
```
Fed QT (자산 감소)
  → 준비금 감소
    → 은행 신용 창출 여력 약화
      → Bank Credit 성장률 둔화
        → 한계 투자자 신용선 축소
          → 자산 담보 재평가
            → 가격 조정
```

**모니터링 포인트:**
- QT 월간 속도 (Target: 월 600억 달러)
- 준비금 감소 가속도
- RRP 잔액 변화 (금리 경쟁 신호)
- Credit impulse = Bank Credit 가속도 (정부 지출과 비교)

**QT Monitoring 페이지:**
- QT 진행도 vs Target
- 준비금 감소율 추이
- RRP vs 금리 간 상관관계
- Credit impulse 신호

## 데이터 소스 교체

1. `loaders/` 폴더의 로더 클래스 사용
2. CSV 업로드: 사이드바에서 파일 업로드
3. 실시간 데이터: 샘플 데이터 체크박스 해제

```python
from loaders import CSVLoader
loader = CSVLoader()
df = loader.load_from_path("my_data.csv", indicator_name="Custom")
```

## 라이선스

MIT License
