# 데이터 스키마와 대응 규칙

모든 데이터는 UTF-8 CSV이며, 첫 줄은 아래 표의 컬럼명과 정확히 같아야 합니다. `python scripts/crosswalk.py validate`가 이 규칙을 검사합니다.

## 1. frameworks.csv — 인증 기준 목록

| 컬럼 | 필수 | 설명 | 예 |
| --- | --- | --- | --- |
| framework_id | ○ | 기준 식별자. `data/controls/<framework_id>.csv` 파일명과 같아야 함 | `isms-p` |
| name | ○ | 기준 이름 | `ISMS-P` |
| version | ○ | 기준 버전 또는 고시 개정일 | `2023-10-31` |
| issuer | ○ | 발행·운영 기관 | `KISA` |
| source_url |  | 원문 확인 위치 | |
| note |  | 저작권 등 참고 사항 | `원문 미전재` |

## 2. controls/<framework_id>.csv — 기준별 항목

| 컬럼 | 필수 | 설명 | 예 |
| --- | --- | --- | --- |
| control_id | ○ | 기준 내 항목 번호. 파일 안에서 중복 불가 | `2.5.6` |
| domain |  | 상위 영역 | `2.5 인증 및 권한관리` |
| title_ko |  | 한국어 제목 | `접근권한 검토` |
| title_en |  | 영문 제목 | `Access rights` |

`title_ko`와 `title_en` 중 하나는 반드시 있어야 합니다. **요구사항 원문은 넣지 않습니다.**

## 3. common_controls.csv — 공통 통제

| 컬럼 | 필수 | 설명 | 예 |
| --- | --- | --- | --- |
| cc_id | ○ | `CC-<영역>-<번호>` 형식 | `CC-AC-03` |
| name_ko | ○ | 공통 통제 이름 | `접근권한 정기 검토` |
| name_en |  | 영문 이름 | `Periodic access review` |
| description | ○ | 이 공통 통제가 확인하는 것 (직접 작성) | |
| category | ○ | 영역 코드 | `AC` |

영역 코드 예: `GV`(거버넌스), `AM`(자산), `HR`(인적), `PH`(물리), `AC`(접근통제), `CR`(암호), `OP`(운영), `BK`(백업·연속성), `IR`(사고대응), `PV`(개인정보), `SC`(공급망)

## 4. mappings.csv — 기준 항목 → 공통 통제

| 컬럼 | 필수 | 설명 |
| --- | --- | --- |
| framework_id | ○ | `frameworks.csv`에 있는 값 |
| control_id | ○ | 해당 기준 파일에 있는 항목 번호 |
| cc_id | ○ | `common_controls.csv`에 있는 값 |
| relation | ○ | 아래 4가지 중 하나 |
| gap_note | 조건부 | `relation`이 `contains`이면 필수. 공통 통제만으로 빠지는 요구사항 |
| rationale | ○ | 이렇게 대응한 근거 한 줄 |
| status | ○ | `draft`(초안) 또는 `reviewed`(검토 완료) |
| reviewed_at |  | 검토일 `YYYY-MM-DD`. `status`가 `reviewed`이면 필수 |

### relation: 대응 강도와 방향

기준 항목(X)과 공통 통제(C)의 **포함 관계**로 표현합니다.

| relation | 의미 | 블로그 표현 | X를 충족하면 C도? | C를 충족하면 X도? |
| --- | --- | --- | --- | --- |
| `equal` | X와 C의 요구 범위가 같음 | 완전 대응 | 예 | 예 |
| `within` | X가 C의 일부 (C가 더 넓음) | 완전 대응 | 아니오 | 예 |
| `contains` | C가 X의 일부 (X가 더 넓음) | 부분 대응 | 예 | **아니오** → `gap_note` 필수 |
| `related` | 겹치지만 포함 관계 없음 | 관련만 있음 | 아니오 | 아니오 |

### 기준 간 대응 계산 규칙

같은 공통 통제 C에 연결된 두 항목 X(기준 A), Y(기준 B)에 대해:

- **X ⇒ C** 는 X의 relation이 `equal` 또는 `contains`일 때 성립
- **C ⇒ Y** 는 Y의 relation이 `equal` 또는 `within`일 때 성립
- 둘 다 성립하면 **X를 충족하면 Y도 충족** (X ⇒ Y)
- 양쪽 방향이 모두 성립하면 **상호 충족** (X ⇔ Y)
- 어느 쪽도 성립하지 않으면 **참고 관계**로만 표시

예: ISMS-P 2.5.6은 공통 통제와 `equal`, ISO A.5.18은 `contains`(권한 부여·회수까지 포함)라면 → A.5.18을 충족하면 2.5.6도 충족되지만, 2.5.6만으로 A.5.18이 충족되지는 않습니다.

## 5. evidence.csv — 대표 증적

| 컬럼 | 필수 | 설명 | 예 |
| --- | --- | --- | --- |
| evidence_id | ○ | `EV-<번호>` | `EV-001` |
| cc_id | ○ | 연결된 공통 통제 | `CC-AC-03` |
| name | ○ | 증적 이름 | `권한 검토 결과 보고서` |
| description |  | 무엇을 보여주는 자료인지 | |
| frequency |  | 생성 주기 | `분기` |

조직의 실제 증적 파일이 아니라 **증적의 종류**를 적습니다.
