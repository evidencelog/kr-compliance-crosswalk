# kr-compliance-crosswalk

국내외 보안 인증 기준의 통제항목을 **공통 통제(Common Control)** 하나에 연결해, 증적 하나를 여러 인증에 재사용할 수 있게 만드는 오픈 크로스워크입니다.

> An open crosswalk that maps Korean and international security certification controls (ISMS-P, CSAP, ISO/IEC 27001 family) to a shared set of common controls, so one piece of evidence can serve many audits.

## 왜 만드나

인증마다 같은 증적을 다시 요청하고, 기준 문서를 펼쳐 "이 항목이 지난번 그 항목인가"를 다시 따지는 일을 줄이기 위해서입니다. 배경은 블로그 글에 정리했습니다.

- [인증 기준은 다른데 증적은 같다: 통합 크로스워크를 만드는 이유](https://evidencelog.tistory.com/1)

## 구조: 기준끼리가 아니라 공통 통제를 가운데에

```
ISMS-P 2.5.6 ──┐
               ├──▶ CC-AC-03 접근권한 정기 검토 ──▶ 증적: 권한 검토 결과 보고서
ISO A.5.18  ───┘
```

기준 항목끼리 직접 잇지 않고, 각 항목을 공통 통제에 연결합니다. 두 기준 사이의 대응은 공통 통제를 거쳐 **계산**합니다. 그래서 기준이 하나 늘어도 그 기준만 공통 통제에 연결하면 됩니다.

## 원칙

| 원칙 | 데이터에서 구현하는 방법 |
| --- | --- |
| 대응 강도를 구분한다 | `relation` 컬럼: `equal` / `within` / `contains` / `related` |
| 방향을 명시한다 | `relation`의 포함 관계로 "A를 충족하면 B도 충족되는가"를 단방향으로 계산 |
| 판단 근거를 남긴다 | `rationale` 필수, 부분 대응(`contains`)은 `gap_note` 필수 |
| 표준 원문을 옮기지 않는다 | 항목 번호와 짧은 제목, 직접 쓴 요약만 저장 |
| 최종 판단은 사람이 한다 | `status`(`draft` / `reviewed`)로 검토 여부를 구분. 심사 결과를 대신하지 않음 |

자세한 정의는 [docs/schema.md](docs/schema.md)를 보세요.

## 폴더 구성

```
data/
  frameworks.csv          # 인증 기준 목록 (이름, 버전, 출처)
  controls/
    isms-p.csv            # ISMS-P 항목 (번호, 제목)
    iso27001-2022.csv     # ISO/IEC 27001:2022 부속서 A 통제 (번호, 짧은 제목)
  common_controls.csv     # 공통 통제
  mappings.csv            # 기준 항목 → 공통 통제 대응
  evidence.csv            # 공통 통제별 대표 증적
scripts/
  crosswalk.py            # 데이터 검증 + 기준 간 대응 계산
docs/
  schema.md               # 컬럼 정의와 대응 규칙
```

## 사용법

Python 3.9 이상, 외부 패키지 없이 동작합니다.

```bash
# 데이터 검증 (컬럼, 허용값, 참조 무결성, 근거 누락)
python scripts/crosswalk.py validate

# ISMS-P 기준으로 ISO 27001 대응 계산
python scripts/crosswalk.py derive --from isms-p --to iso27001-2022
```

`derive` 출력 예:

```
from          to        via        result
A.5.18    ->  2.5.6     CC-AC-03   A.5.18을 충족하면 2.5.6도 충족 (단방향)  [draft]
2.9.3     <-> A.8.13    CC-BK-01   상호 충족  [draft]
```

## 로드맵

- [x] **v0.1** ISMS-P 101개 항목 ↔ ISO/IEC 27001:2022 부속서 A 93개 통제
- [ ] **v0.2** ISO 27001 본문 조항(4~10장), ISO/IEC 27701:2025, ISO/IEC 27017·27018, CSAP IaaS 확장 (진행 중: 27701)
- [ ] **v0.3** 검색 가능한 웹 페이지 공개

현재 진행 상황: ISMS-P 101개, ISO 27001:2022 93개 항목 전체를 공통 통제 88개에 대응했습니다(v0.1 데이터 완료, 일부 검토 중). 설계 결정은 [docs/decisions](docs/decisions)에 기록합니다. 진행률은 `python scripts/crosswalk.py validate`로 확인할 수 있습니다.

## 주의

- 이 자료는 인증 준비를 돕는 참고 자료이며, 인증기관이나 심사원의 판단을 대신하지 않습니다.
- ISO 표준 원문은 저작권 대상이므로 이 저장소에는 원문을 싣지 않습니다. 정확한 요구사항은 각 기준의 원문을 확인하세요.
- ISMS-P 항목은 「정보보호 및 개인정보보호 관리체계 인증 등에 관한 고시」 기준입니다. 개정 시점은 `data/frameworks.csv`에 적습니다.

## 기여

오류 제보와 대응 의견을 환영합니다. [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 라이선스

데이터(`data/`, `docs/`)는 CC BY 4.0, 코드(`scripts/`)는 MIT입니다. [LICENSE.md](LICENSE.md) 참고.
